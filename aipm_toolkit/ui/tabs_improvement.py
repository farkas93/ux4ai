"""Explore one AI-assisted improvement loop as a learning exercise."""

import gradio as gr

from ..improvement_services import QUESTIONS
from .safety_callbacks import add_learning_note_ui, save_primary_loop_ui


def build_improvement_tab(token, project_id, status):
    with gr.Column(visible=False, elem_id="page-self-improvement") as tab:
        gr.Markdown(
            "## Recursive Self-Improvement\n"
            "Imagine one way your product might learn from its use. Write questions and assumptions first, "
            "then develop hypotheses in **Backlog Creator**."
        )
        loop_id = gr.State(None)
        revision = gr.State(None)
        dirty = gr.State(False)
        name = gr.Textbox(
            label="Your improvement loop",
            placeholder="Analyze failed support conversations and propose better clarification prompts",
        )

        notes_list = gr.Textbox(label="Current questions and assumptions", interactive=False, lines=3)
        with gr.Row(elem_classes=["toolkit-note-composer"]):
            note_type = gr.Dropdown(choices=["Question", "Assumption"], value="Question", label="Type", scale=0, min_width=140)
            note_text = gr.Textbox(label="What needs exploring?", scale=3)
            add_button = gr.Button("Add", scale=0, min_width=80, size="sm")
        note_draft_dirty = gr.State(False)
        note_type.input(lambda: True, outputs=note_draft_dirty, concurrency_id="project-data-write", concurrency_limit=1)
        note_text.input(lambda: True, outputs=note_draft_dirty, concurrency_id="project-data-write", concurrency_limit=1)
        section, origin_key = gr.State("self_improvement"), gr.State(None)
        note_event = add_button.click(
            add_learning_note_ui,
            [token, project_id, section, origin_key, note_type, note_text],
            [status, notes_list, note_text],
            concurrency_id="project-data-write",
            concurrency_limit=1,
        )
        note_event.then(lambda message: not message.startswith("Added."), status, note_draft_dirty)

        gr.Markdown("### Explore what AI contributes to the loop")
        answers = []
        for question in list(QUESTIONS.values())[:5]:
            with gr.Accordion(question, open=False):
                answer = gr.Radio(
                    choices=[("Yes", "yes"), ("Partly", "partly"), ("No", "no"), ("Unknown", "unknown")],
                    label="Capability",
                    value=None,
                )
                explanation = gr.Textbox(label="Explanation", lines=2)
                answers.extend([answer, explanation])

        # Deferred for next academic year pending pedagogical review: levels 4-5,
        # advanced automation prerequisites, implementation metadata, and numeric
        # level feedback. The persistence layer retains these fields for review.
        save = gr.Button("Save learning loop", variant="primary")
        save_event = save.click(
            save_primary_loop_ui,
            [token, project_id, loop_id, revision, name, *answers],
            [status, loop_id, revision],
            concurrency_id="project-data-write",
            concurrency_limit=1,
        )
        for field in (name, *answers):
            field.input(lambda: True, outputs=dirty, concurrency_id="project-data-write", concurrency_limit=1)

        save_event.then(lambda message: not message.startswith("Learning loop saved."), status, dirty)
    return {
        "tab": tab,
        "loop_id": loop_id,
        "revision": revision,
        "dirty": dirty,
        "name": name,
        "answers": answers,
        "fields": [name, *answers, revision],
        "notes_list": notes_list,
        "note_event": note_event,
        "note_draft": {"dirty": note_draft_dirty, "type": note_type, "text": note_text, "list": notes_list},
        "note_section": section,
    }
