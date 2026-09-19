"""Project Setup tab."""

import gradio as gr

from .callbacks import (
    autosave_project_from_ui,
    create_project_from_ui,
    load_project_from_ui,
    save_project_action,
)


def build_setup_tab(token, project_id, project_revision, status):
    with gr.Tab("Project Setup") as tab:
        gr.Markdown("Context: define the product concept, target user, job, problem, prototype, and main value hypothesis.")
        with gr.Row():
            project_dropdown = gr.Dropdown(label="Your products", choices=[], interactive=True)
            new_product_name = gr.Textbox(label="New product name", placeholder="Only the product name is required")
            create_button = gr.Button("Create draft")
        project_title = gr.Markdown()
        with gr.Row():
            product_name = gr.Textbox(label="Product name")
            product_type = gr.Dropdown(label="AI product type", choices=["Feature", "Plugin", "Native", "Mixed/Undecided"], value=None)
        description = gr.Textbox(label="Short description", lines=3)
        target_user = gr.Textbox(label="Target user")
        job = gr.Textbox(label="Job to be done", lines=3)
        problem = gr.Textbox(label="Current problem or workflow", lines=3)
        hypothesis = gr.Textbox(label="Main value hypothesis", lines=4, placeholder="If we help [user] accomplish [job] through [capability], we expect [outcome] to improve while maintaining [constraint].")
        figma_url = gr.Textbox(label="Figma prototype URL (optional)")
        save_button = gr.Button("Save product setup", variant="primary")
        brief_dirty = gr.State(False)
        brief_timer = gr.Timer(2.0)
        for brief_field in (product_name, product_type, description, target_user, job, problem, hypothesis, figma_url):
            brief_field.input(lambda: True, outputs=brief_dirty)

        project_dropdown.change(
            load_project_from_ui,
            [token, project_dropdown],
            [project_title, product_name, description, target_user, job, problem, hypothesis, product_type, figma_url, project_id, project_revision],
        ).then(lambda: False, outputs=brief_dirty)
        create_button.click(create_project_from_ui, [token, new_product_name], [status, project_dropdown, product_name, project_revision])
        save_button.click(
            save_project_action,
            [token, project_id, project_revision, product_name, product_type, description, target_user, job, problem, hypothesis, figma_url],
            [status, project_revision, brief_dirty],
        )
        brief_timer.tick(
            autosave_project_from_ui,
            [token, project_id, project_revision, brief_dirty, product_name, product_type, description, target_user, job, problem, hypothesis, figma_url],
            [status, project_revision, brief_dirty],
        )

    return {
        "tab": tab,
        "project_dropdown": project_dropdown,
        "project_title": project_title,
        "product_name": product_name,
        "product_type": product_type,
        "description": description,
        "target_user": target_user,
        "job": job,
        "problem": problem,
        "hypothesis": hypothesis,
        "figma_url": figma_url,
    }
