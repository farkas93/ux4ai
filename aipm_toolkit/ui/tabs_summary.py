"""Summary & Export tab."""

import gradio as gr

from .callbacks import export_project_from_ui


def build_summary_tab(token, project_id, status):
    with gr.Tab("Summary & Export") as tab:
        gr.Markdown("Review checklist progress and download the product record.")
        checklist_display = gr.Textbox(label="Workshop checklist", interactive=False, lines=8)
        export_button = gr.Button("Generate JSON and Markdown exports")
        json_download = gr.File(label="JSON export")
        markdown_download = gr.File(label="Markdown export")

        export_button.click(export_project_from_ui, [token, project_id], [status, json_download, markdown_download])

    return {
        "tab": tab,
        "checklist_display": checklist_display,
        "json_download": json_download,
        "markdown_download": markdown_download,
    }
