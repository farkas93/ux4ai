"""Prioritization tab: per-hypothesis risk/evidence sliders with real-time ranking and matrix plot."""

import gradio as gr

from .callbacks import (
    PLACEMENT_SLOTS,
    ranked_backlog_from_ui,
    save_placement_from_ui,
)


def build_priority_tab(token, product_dropdown, status):
    with gr.Column(visible=False, elem_id="page-prioritization") as tab:
        gr.Markdown("## Prioritization\nWhich hypothesis is most important to test next?", elem_classes=["toolkit-page-heading"])
        gr.Markdown(
            "Open a hypothesis and discuss risk if it is wrong and the evidence you have. "
            "The suggested test order updates as you change the sliders."
        )
        with gr.Row(elem_classes=["toolkit-two-column"]):
            with gr.Column():
                gr.Markdown("### Hypotheses")
                slot_components = []
                for index in range(PLACEMENT_SLOTS):
                    with gr.Accordion(f"H{index + 1}", open=False, visible=False) as accordion:
                        statement_display = gr.Markdown("")
                        source_display = gr.Textbox(label="Source question / assumption", interactive=False, lines=2)
                        risk_slider = gr.Slider(label="Risk if wrong", minimum=0, maximum=10, step=0.5, value=0)
                        evidence_slider = gr.Slider(label="Evidence available", minimum=0, maximum=10, step=0.5, value=0)
                    slot_components.append({
                        "accordion": accordion,
                        "statement": statement_display,
                        "risk": risk_slider,
                        "evidence": evidence_slider,
                        "id": gr.State(None),
                        "revision": gr.State(None),
                        "source": source_display,
                    })
            with gr.Column():
                gr.Markdown("**Test first** · High risk with limited evidence", elem_id="test-first-key")
                matrix_fig = gr.Plot(label="Risk versus evidence matrix")
                gr.Markdown("### Suggested test order")
                ranking_display = gr.HTML()

        ranking_inputs = []
        for slot in slot_components:
            ranking_inputs.append(slot["id"])
        for slot in slot_components:
            ranking_inputs.append(slot["statement"])
        for slot in slot_components:
            ranking_inputs.append(slot["risk"])
        for slot in slot_components:
            ranking_inputs.append(slot["evidence"])

        source_inputs = [slot["source"] for slot in slot_components]

        def refresh_ranking(*args):
            return ranked_backlog_from_ui(*args[:PLACEMENT_SLOTS * 4], sources=args[PLACEMENT_SLOTS * 4:])

        for slot in slot_components:
            for slider in (slot["risk"], slot["evidence"]):
                slider.change(
                    save_placement_from_ui,
                    [token, slot["id"], slot["revision"], slot["risk"], slot["evidence"]],
                    [status, slot["revision"]],
                ).then(refresh_ranking, ranking_inputs + source_inputs, [ranking_display, matrix_fig])

    placement_outputs = []
    for slot in slot_components:
        placement_outputs.extend([slot["accordion"], slot["statement"], slot["risk"], slot["evidence"], slot["id"], slot["revision"], slot["source"]])

    return {
        "tab": tab,
        "placement_outputs": placement_outputs,
        "ranking_display": ranking_display,
        "matrix_fig": matrix_fig,
    }
