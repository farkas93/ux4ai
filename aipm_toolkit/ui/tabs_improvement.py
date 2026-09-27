"""Explore one AI-assisted improvement loop as a learning exercise."""

import gradio as gr

from ..improvement_services import QUESTIONS, SCOPES
from .safety_callbacks import add_learning_note_ui, live_loop_card, save_primary_loop_ui


def build_improvement_tab(token, product_dropdown, status):
    with gr.Tab("Self-Improvement") as tab:
        gr.Markdown("## Recursive Self-Improvement\nImagine one way your product might learn from its use. Write questions and assumptions first, then develop hypotheses in **Backlog Creator**.")
        loop_id = gr.State(None)
        name = gr.Textbox(label="Your improvement loop", placeholder="Analyze failed support conversations and propose better clarification prompts")
        notes_list = gr.Textbox(label="Current questions and assumptions", interactive=False, lines=3)
        with gr.Row():
            note_type = gr.Radio(choices=["Question", "Assumption"], value="Question", label="Add")
            note_text = gr.Textbox(label="What needs exploring?", scale=3)
            add_button = gr.Button("Add", scale=1)
        section, origin_key = gr.State("self_improvement"), gr.State(None)
        note_event = add_button.click(add_learning_note_ui, [token, product_dropdown, section, origin_key, note_type, note_text], [status, notes_list, note_text])
        gr.Markdown("### Explore what AI contributes to the loop")
        answers = []
        def add_capability(question):
            with gr.Accordion(question, open=False):
                answer = gr.Radio(choices=[("Yes", "yes"), ("Partly", "partly"), ("No", "no"), ("Unknown", "unknown")], label="Capability", value=None)
                explanation = gr.Textbox(label="Explanation", lines=2)
                answers.extend([answer, explanation])

        for question in list(QUESTIONS.values())[:5]:
            add_capability(question)
        with gr.Accordion("Optional: explore more automated loops", open=False):
            for question in list(QUESTIONS.values())[5:]:
                add_capability(question)
        with gr.Accordion("Optional: describe the implementation", open=False):
            status_field = gr.Radio(choices=[("Intended", "intended"), ("Implemented", "implemented"), ("Demonstrated", "demonstrated")], label="Status", value="intended")
            scopes = gr.CheckboxGroup(choices=[(key.replace("_", " ").title(), key) for key in sorted(SCOPES)], label="Change scope")
            recursion = gr.Radio(choices=[("Product behavior", "product_behavior"), ("Improvement process itself", "improvement_process")], label="Recursion scope", value="product_behavior")
            release = gr.Radio(choices=[("Human", "human"), ("Bounded automatic", "bounded_automatic"), ("Unspecified", "unspecified")], label="Release approval", value="unspecified")
            boundary = gr.Textbox(label="Approval boundary and automatic-application limits", lines=2)
            checks = gr.Textbox(label="Success criteria and regression checks", lines=2)
            rollback = gr.Textbox(label="Rollback or recovery mechanism", lines=2)
        revision = gr.State(None)
        fields = [name, *answers, status_field, scopes, recursion, release, boundary, checks, rollback, revision]
        with gr.Accordion("Optional: course-specific level feedback", open=False):
            card = gr.Markdown("Name a specific improvement loop to see a provisional course-specific level.")
        save = gr.Button("Save learning loop", variant="primary")
        for component in fields[:-1]:
            component.change(live_loop_card, fields[:-1], card)
        save.click(save_primary_loop_ui, [token, product_dropdown, loop_id, revision, *fields[:-1]], [status, loop_id, revision, card])
    return {"tab": tab, "loop_id": loop_id, "fields": fields, "card": card, "notes_list": notes_list, "note_event": note_event, "note_section": section}
