"""Summary & Export tab."""

import gradio as gr

from .callbacks import delete_product_from_ui, export_project_from_ui, summary_preview_from_ui


def build_summary_tab(token, product_dropdown, status):
    with gr.Column(visible=False, elem_id="page-summary-export") as tab:
        gr.Markdown("## Summary & Export\nBring your idea and learning together.", elem_classes=["toolkit-page-heading"])
        with gr.Row(elem_classes=["toolkit-two-column"]):
            with gr.Column(scale=3, elem_classes=["toolkit-card"]):
                summary_preview = gr.Markdown("Select a product to view its summary.")
                refresh_summary_button = gr.Button("Refresh summary", variant="secondary")
            with gr.Column(scale=2, elem_classes=["toolkit-card"]):
                checklist_display = gr.Textbox(label="Workshop progress", interactive=False, lines=9)
        with gr.Column(elem_classes=["toolkit-card"]):
            gr.Markdown("### Take your work with you\nExport for discussion, presentation, or further work.")
            export_button = gr.Button("Prepare downloads", variant="primary")
            with gr.Row(elem_classes=["toolkit-two-column"]):
                pdf_download = gr.File(label="PDF export (includes both graphs)")
                markdown_download = gr.File(label="Markdown export")
                json_download = gr.File(label="JSON export")

        with gr.Accordion("Product administration", open=False):
            gr.Markdown("Deleting is manual and permanent. Only your team or an instructor can delete this product.")
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
