"""Question-first AI Safety learning prompts."""

import gradio as gr

from ..safety_services import CHECKPOINTS
from .safety_callbacks import add_learning_note_ui


def build_safety_tab(token, product_dropdown, status):
    with gr.Column(visible=False, elem_id="page-ai-safety") as tab:
        gr.Markdown("## AI Safety", elem_classes=["toolkit-page-heading"])
        gr.Markdown(
            "Discuss where the idea might cause harm or need safeguards. Add questions and assumptions here, "
            "then turn them into hypotheses in **Backlog Creator**."
        )
        note_events = []
        note_lists = []
        checkpoint_states = []
        section = gr.State("safety")
        for key, (title, prompt) in CHECKPOINTS.items():
            with gr.Accordion(title, open=(key == "scope")):
                gr.Markdown(prompt)
                notes_list = gr.Textbox(label="Current questions and assumptions", interactive=False, lines=2)
                note_lists.append(notes_list)
                with gr.Row(elem_classes=["toolkit-note-composer"]):
                    note_type = gr.Dropdown(choices=["Question", "Assumption"], value="Question", label="Type", scale=0, min_width=140)
                    text = gr.Textbox(label="What needs exploring?", scale=3)
                    add_button = gr.Button("Add", scale=0, min_width=80, size="sm")
                checkpoint = gr.State(key)
                checkpoint_states.append(checkpoint)
                note_events.append(add_button.click(
                    add_learning_note_ui,
                    [token, product_dropdown, section, checkpoint, note_type, text],
                    [status, notes_list, text],
                ))

        # Deferred for next academic year pending pedagogical review: coverage
        # scoring, maturity/evidence rating, and the critical-risk summary card.
    return {
        "tab": tab,
        "note_events": note_events,
        "note_lists": note_lists,
        "note_section": section,
        "checkpoint_states": checkpoint_states,
    }
