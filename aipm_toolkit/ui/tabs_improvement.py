"""AI-assisted and automated improvement loops, classified individually."""

import gradio as gr

from ..improvement_services import QUESTIONS, SCOPES
from .safety_callbacks import blank_loop_ui, live_loop_card, load_loop_ui, save_loop_ui


def build_improvement_tab(token, product_dropdown, status):
    with gr.Tab("Self-Improvement") as tab:
        gr.Markdown("## Recursive Self-Improvement Assessment\n**AI-assisted and automated improvement loops**\n\nName one concrete loop at a time. Each loop receives its own course-specific classification; loops are never averaged.")
        with gr.Row():
            selector = gr.Dropdown(label="Saved improvement loops", choices=[])
            new_button = gr.Button("+ New loop")
        name = gr.Textbox(label="Specific improvement loop", placeholder="Analyze failed support conversations and propose clarification-prompt changes")
        answers = []
        for key, question in QUESTIONS.items():
            with gr.Accordion(question, open=(key == "observe")):
                answer = gr.Radio(choices=[("Yes", "yes"), ("Partly", "partly"), ("No", "no"), ("Unknown", "unknown")], label="Capability", value=None)
                explanation = gr.Textbox(label="Explanation", lines=2)
                answers.extend([answer, explanation])
        gr.Markdown("The last two questions establish whether levels 4 and 5 are supported. 'Partly' does not satisfy a prerequisite.")
        status_field = gr.Radio(choices=[("Intended", "intended"), ("Implemented", "implemented"), ("Demonstrated", "demonstrated")], label="Status", value="intended")
        scopes = gr.CheckboxGroup(choices=[(key.replace("_", " ").title(), key) for key in sorted(SCOPES)], label="Change scope")
        recursion = gr.Radio(choices=[("Product behavior", "product_behavior"), ("Improvement process itself", "improvement_process")], label="Recursion scope", value="product_behavior")
        release = gr.Radio(choices=[("Human", "human"), ("Bounded automatic", "bounded_automatic"), ("Unspecified", "unspecified")], label="Release approval", value="unspecified")
        boundary = gr.Textbox(label="Approval boundary and automatic-application limits", lines=2)
        checks = gr.Textbox(label="Success criteria and regression checks", lines=2)
        rollback = gr.Textbox(label="Rollback or recovery mechanism", lines=2)
        revision = gr.State(None)
        fields = [name, *answers, status_field, scopes, recursion, release, boundary, checks, rollback, revision]
        card = gr.Markdown("Name a specific improvement loop to classify it. Course-specific classification—not a standardized benchmark.")
        save = gr.Button("Save loop", variant="primary")
        for component in fields[:-1]:
            component.change(live_loop_card, fields[:-1], card)
        selector.change(load_loop_ui, [token, product_dropdown, selector], [*fields, card])
        new_button.click(blank_loop_ui, outputs=[selector, *fields, card])
        save.click(save_loop_ui, [token, product_dropdown, selector, revision, *fields[:-1]], [status, selector, revision, card])
    return {"tab": tab, "selector": selector, "fields": fields, "card": card}
