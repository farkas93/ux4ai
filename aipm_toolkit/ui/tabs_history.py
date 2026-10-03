"""Project activity history tab."""

import gradio as gr

from .callbacks import project_history_from_ui


def build_history_tab(token, product_dropdown):
    with gr.Tab("Project History", id="Project History") as tab:
        gr.Markdown("## Project History\nSee how your thinking has changed.", elem_classes=["toolkit-page-heading"])
        gr.Markdown(
            "Changes to assessments and backlog entries are recorded here. "
            "This is a history of changes made in the workspace, not a record of edits made before history was introduced."
        )
        refresh_button = gr.Button("Refresh history")
        history = gr.HTML("Select a product to view its history.")
        refresh_button.click(project_history_from_ui, [token, product_dropdown], history)
    return {"tab": tab, "history": history}
