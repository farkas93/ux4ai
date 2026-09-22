"""Backlog creator tab: 4-column table for Dimension, Assumption, Question, Hypothesis."""

import gradio as gr

from ..dimensions import DEFAULT_DIMENSIONS
from .callbacks import (
    MAX_BACKLOG_ROWS,
    save_backlog_row_from_ui,
    show_next_row_from_ui,
)


def build_backlog_tab(token, product_dropdown, status):
    with gr.Tab("Backlog creator") as tab:
        gr.Markdown(
            "### Backlog Table\n"
            "Rows are auto-populated from your Assessment questions and assumptions. "
            "Expand each row with the missing counterpart and formulate a testable hypothesis. "
            "All assumptions and questions can be edited directly."
        )

        # Header row
        with gr.Row(elem_classes=["backlog-table-header"]):
            with gr.Column(scale=2, min_width=120):
                gr.Markdown("**Dimension**")
            with gr.Column(scale=3):
                gr.Markdown("**Assumption**")
            with gr.Column(scale=3):
                gr.Markdown("**Question**")
            with gr.Column(scale=4):
                gr.Markdown("**Hypothesis**")
            with gr.Column(scale=1, min_width=80):
                gr.Markdown("**Action**")

        # Scrollable container for rows (scrollview active if > 10 rows)
        row_components = []
        with gr.Column(elem_classes=["backlog-table-container"]):
            for i in range(MAX_BACKLOG_ROWS):
                with gr.Row(visible=(i == 0), variant="panel") as row_box:
                    dim_dropdown = gr.Dropdown(
                        choices=[(d["title"], d["key"]) for d in DEFAULT_DIMENSIONS],
                        value="conversational",
                        show_label=False,
                        scale=2,
                    )
                    assumption_box = gr.Textbox(
                        show_label=False,
                        placeholder="Assumption (from Assessment or enter new)...",
                        lines=2,
                        scale=3,
                    )
                    question_box = gr.Textbox(
                        show_label=False,
                        placeholder="Question (from Assessment or enter new)...",
                        lines=2,
                        scale=3,
                    )
                    hypothesis_box = gr.Textbox(
                        show_label=False,
                        placeholder="Testable hypothesis extending this...",
                        lines=2,
                        scale=4,
                    )
                    save_btn = gr.Button("Save", variant="primary", scale=1)
                    note_id_state = gr.State(None)
                    hyp_id_state = gr.State(None)
                    hyp_rev_state = gr.State(None)

                row_components.append({
                    "box": row_box,
                    "dim": dim_dropdown,
                    "assumption": assumption_box,
                    "question": question_box,
                    "hypothesis": hypothesis_box,
                    "save_btn": save_btn,
                    "note_id": note_id_state,
                    "hyp_id": hyp_id_state,
                    "hyp_rev": hyp_rev_state,
                })

        with gr.Row():
            add_row_btn = gr.Button("+ Add Row", variant="secondary")
            visible_rows_count = gr.State(1)

        # Event: add row reveals next hidden slot
        add_row_btn.click(
            show_next_row_from_ui,
            [visible_rows_count],
            [visible_rows_count, *[r["box"] for r in row_components]],
        )

        # Event: save row saves notes + hypothesis
        for r in row_components:
            r["save_btn"].click(
                save_backlog_row_from_ui,
                [token, product_dropdown, r["dim"], r["assumption"], r["question"], r["hypothesis"], r["note_id"], r["hyp_id"], r["hyp_rev"]],
                [status, r["note_id"], r["hyp_id"], r["hyp_rev"]],
            )

    table_flat_outputs = []
    for r in row_components:
        table_flat_outputs.extend([r["box"], r["dim"], r["assumption"], r["question"], r["hypothesis"], r["note_id"], r["hyp_id"], r["hyp_rev"]])

    return {
        "tab": tab,
        "row_components": row_components,
        "table_flat_outputs": table_flat_outputs,
        "visible_rows_count": visible_rows_count,
    }
