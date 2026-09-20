"""Summary & Export tab."""

import gradio as gr

from .callbacks import delete_product_from_ui, export_project_from_ui, summary_preview_from_ui


def build_summary_tab(token, product_dropdown, status):
    with gr.Tab("Summary & Export") as tab:
        gr.Markdown("Review checklist progress and download the product record.")
        checklist_display = gr.Textbox(label="Workshop checklist", interactive=False, lines=8)
        refresh_summary_button = gr.Button("Refresh summary")
        summary_preview = gr.Markdown("Select a product to view its summary.")
        export_button = gr.Button("Generate PDF, JSON, and Markdown exports")
        pdf_download = gr.File(label="PDF export (includes both graphs)")
        json_download = gr.File(label="JSON export")
        markdown_download = gr.File(label="Markdown export")

        gr.Markdown("## Danger zone")
        gr.Markdown("Deleting is manual and permanent. Only your team or an instructor can delete this product; nothing is deleted automatically.")
        confirm_delete = gr.Checkbox(label="I understand this permanently deletes my product and its content", value=False)
        delete_button = gr.Button("Delete this product", variant="stop")

        refresh_summary_button.click(summary_preview_from_ui, [token, product_dropdown], summary_preview)
        export_button.click(export_project_from_ui, [token, product_dropdown], [status, json_download, markdown_download, pdf_download])
        delete_button.click(delete_product_from_ui, [token, product_dropdown, confirm_delete], [status, product_dropdown])

    return {
        "tab": tab,
        "checklist_display": checklist_display,
        "summary_preview": summary_preview,
        "pdf_download": pdf_download,
        "json_download": json_download,
        "markdown_download": markdown_download,
    }
