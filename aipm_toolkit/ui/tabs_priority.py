"""Prioritization tab: per-hypothesis risk/evidence sliders with real-time ranking and matrix plot."""

import gradio as gr

from .callbacks import (
    PLACEMENT_SLOTS,
    ranked_backlog_from_ui,
    save_placement_from_ui,
)


def build_priority_tab(token, product_dropdown, status):
    with gr.Tab("Prioritization") as tab:
        gr.Markdown(
            "Left: open a hypothesis and set risk and evidence (0-10; every hypothesis starts at 0/0). "
            "Right: the ranked backlog updates in real time - risk 10 with evidence 0 ranks first, "
            "evidence 10 with risk 0 ranks last."
        )
        with gr.Row():
            with gr.Column():
                gr.Markdown("### Hypotheses")
                slot_components = []
                for index in range(PLACEMENT_SLOTS):
                    with gr.Accordion(f"H{index + 1}", open=False, visible=False) as accordion:
                        statement_display = gr.Markdown("")
                        risk_slider = gr.Slider(label="Risk to project", minimum=0, maximum=10, step=0.5, value=0)
                        evidence_slider = gr.Slider(label="Evidence provided", minimum=0, maximum=10, step=0.5, value=0)
                    slot_components.append({
                        "accordion": accordion,
                        "statement": statement_display,
                        "risk": risk_slider,
                        "evidence": evidence_slider,
                        "id": gr.State(None),
                        "revision": gr.State(None),
                    })
            with gr.Column():
                gr.Markdown("### Backlog ranking")
                ranking_display = gr.Textbox(label="Backlog ranking", interactive=False, lines=10)
                matrix_fig = gr.Plot(label="Risk versus evidence matrix")

        ranking_inputs = []
        for slot in slot_components:
            ranking_inputs.append(slot["id"])
        for slot in slot_components:
            ranking_inputs.append(slot["statement"])
        for slot in slot_components:
            ranking_inputs.append(slot["risk"])
        for slot in slot_components:
            ranking_inputs.append(slot["evidence"])

        def refresh_ranking(*args):
            return ranked_backlog_from_ui(*args)

        for slot in slot_components:
            for slider in (slot["risk"], slot["evidence"]):
                slider.change(
                    save_placement_from_ui,
                    [token, slot["id"], slot["revision"], slot["risk"], slot["evidence"]],
                    [status, slot["revision"]],
                ).then(refresh_ranking, ranking_inputs, [ranking_display, matrix_fig])

    placement_outputs = []
    for slot in slot_components:
        placement_outputs.extend([slot["accordion"], slot["statement"], slot["risk"], slot["evidence"], slot["id"], slot["revision"]])

    return {
        "tab": tab,
        "placement_outputs": placement_outputs,
        "ranking_display": ranking_display,
        "matrix_fig": matrix_fig,
    }
