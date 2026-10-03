"""Backlog creator: transform sourced questions and assumptions into hypotheses."""

import gradio as gr

from ..dimensions import DEFAULT_DIMENSIONS
from .callbacks import (
    MAX_BACKLOG_ROWS,
    show_next_row_from_ui,
)


def build_backlog_tab(token, product_dropdown, status):
    with gr.Tab("Backlog creator", id="Backlog creator") as tab:
        gr.Markdown(
            "## Backlog Creator\n"
            "Rows are auto-populated from Assessment, AI Safety, and Self-Improvement. "
            "Their source is preserved. A product dimension is optional for safety and improvement questions. "
            "Turn a question or assumption into a testable hypothesis. Save each entry when you finish.",
            elem_classes=["toolkit-page-heading"],
        )

        # Cards keep fields labeled and stack naturally on narrow screens.
        row_components = []
        with gr.Column(elem_classes=["backlog-table-container"]):
            for i in range(MAX_BACKLOG_ROWS):
                with gr.Column(visible=False, elem_classes=["backlog-entry"]) as row_box:
                    source = gr.Textbox(value="Backlog Creator", label="From", interactive=False, container=False)
                    with gr.Row(elem_classes=["backlog-fields"]):
                        assumption_box = gr.Textbox(
                            label="Assumption",
                            placeholder="What do you believe to be true?",
                            lines=2,
                            scale=3,
                        )
                        question_box = gr.Textbox(
                            label="Question",
                            placeholder="What needs exploring?",
                            lines=2,
                            scale=3,
                        )
                        hypothesis_box = gr.Textbox(
                            label="Hypothesis",
                            placeholder="If we change …, we expect … because …",
                            lines=2,
                            scale=4,
                        )
                    with gr.Row(elem_classes=["backlog-actions"]):
                        dim_dropdown = gr.Dropdown(choices=[(d["title"], d["key"]) for d in DEFAULT_DIMENSIONS], value=None, label="Product dimension (optional for Safety / Self-Improvement)", scale=4)
                        remove_btn = gr.Button("Remove", variant="secondary", scale=1, visible=False)
                        cancel_btn = gr.Button("Cancel", scale=1, visible=False)
                        save_btn = gr.Button("Save entry", variant="primary", scale=1)
                    note_id_state = gr.State(None)
                    hyp_id_state = gr.State(None)
                    hyp_rev_state = gr.State(None)

                row_components.append({
                    "box": row_box,
                    "source": source,
                    "dim": dim_dropdown,
                    "assumption": assumption_box,
                    "question": question_box,
                    "hypothesis": hypothesis_box,
                    "save_btn": save_btn,
                    "remove_btn": remove_btn,
                    "cancel_btn": cancel_btn,
                    "note_id": note_id_state,
                    "hyp_id": hyp_id_state,
                    "hyp_rev": hyp_rev_state,
                })

        with gr.Row():
            add_row_btn = gr.Button("+ Add entry", variant="secondary")
            visible_rows_count = gr.State(0)

        # Event: add row reveals next hidden slot
        added = add_row_btn.click(
            show_next_row_from_ui,
            [visible_rows_count],
            [visible_rows_count, *[r["box"] for r in row_components]],
        )

        def show_cancellations(count, *ids):
            return [gr.update(visible=i < count and not ids[i * 2] and not ids[i * 2 + 1]) for i in range(MAX_BACKLOG_ROWS)]

        added.then(show_cancellations,
                   [visible_rows_count, *[part for r in row_components for part in (r["note_id"], r["hyp_id"])]],
                   [r["cancel_btn"] for r in row_components])

    table_flat_outputs = []
    for r in row_components:
        table_flat_outputs.extend([r["box"], r["source"], r["dim"], r["assumption"], r["question"], r["hypothesis"], r["remove_btn"], r["cancel_btn"], r["note_id"], r["hyp_id"], r["hyp_rev"]])

    return {
        "tab": tab,
        "row_components": row_components,
        "table_flat_outputs": table_flat_outputs,
        "visible_rows_count": visible_rows_count,
    }
