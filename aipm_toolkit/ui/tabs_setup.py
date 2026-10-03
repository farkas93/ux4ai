"""Project Setup tab."""

import gradio as gr

from .callbacks import (
    autosave_project_from_ui,
    save_project_action,
)


def build_setup_tab(token, product_dropdown, project_revision, status):
    with gr.Tab("Project Setup", id="Project Setup") as tab:
        gr.Markdown("### Start with the value\nWho are you helping, and what should improve for them? Define the idea before exploring its assumptions.")
        with gr.Row():
            with gr.Column(elem_classes=["toolkit-form-card"]):
                gr.Markdown("#### 1 · Your product idea")
                product_type = gr.Dropdown(label="AI product type", choices=["Feature", "Plugin", "Native", "Mixed/Undecided"], value=None)
                description = gr.Textbox(label="Short description", lines=3, placeholder="What does your product help someone do?")
                figma_url = gr.Textbox(label="Figma prototype URL (optional)")
            with gr.Column(elem_classes=["toolkit-form-card"]):
                gr.Markdown("#### 2 · The user and their problem")
                target_user = gr.Textbox(label="Target user", placeholder="Who would benefit from this idea?")
                job = gr.Textbox(label="Job to be done", lines=2)
                problem = gr.Textbox(label="Current problem or workflow", lines=2)
        with gr.Column(elem_classes=["toolkit-form-card"]):
            gr.Markdown("#### 3 · Your main value hypothesis\nDescribe the improvement you expect. You’ll explore supporting hypotheses in Backlog Creator.")
            hypothesis = gr.Textbox(label="Main value hypothesis", lines=3, placeholder="If we help [user] accomplish [job] through [capability], we expect [outcome] to improve while maintaining [constraint].")
        save_button = gr.Button("Save product setup", variant="primary")
        brief_dirty = gr.State(False)
        brief_timer = gr.Timer(2.0)
        for brief_field in (product_type, description, target_user, job, problem, hypothesis, figma_url):
            brief_field.input(lambda: True, outputs=brief_dirty)

        save_button.click(
            save_project_action,
            [token, product_dropdown, project_revision, product_type, description, target_user, job, problem, hypothesis, figma_url],
            [status, project_revision, brief_dirty],
        )
        brief_timer.tick(
            autosave_project_from_ui,
            [token, product_dropdown, project_revision, brief_dirty, product_type, description, target_user, job, problem, hypothesis, figma_url],
            [status, project_revision, brief_dirty],
        )

    return {
        "tab": tab,
        "product_type": product_type,
        "description": description,
        "target_user": target_user,
        "job": job,
        "problem": problem,
        "hypothesis": hypothesis,
        "figma_url": figma_url,
        "brief_dirty": brief_dirty,
    }
