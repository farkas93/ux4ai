"""Assessment tab: dimensions, comparator, and reflections (slice 1 layout)."""

import gradio as gr

from ..dimensions import DEFAULT_DIMENSIONS
from .callbacks import (
    autosave_assessments_from_ui,
    load_comparison_from_ui,
    save_assessments_action,
    save_comparator_from_ui,
    save_feedback_reflection_from_ui,
    save_risk_reflection_from_ui,
)


def build_assessment_tab(token, project_id, status):
    with gr.Tab("Assessment") as tab:
        gr.Markdown("Higher scores are not inherently better. Mark a dimension Unknown when the team cannot make a reasoned estimate yet.")
        assessment_components = []
        for definition in DEFAULT_DIMENSIONS:
            with gr.Accordion(definition["title"], open=False):
                gr.Markdown(f"**0:** {definition['low_anchor']}  |  **5:** {definition['high_anchor']}\n\n{definition['explanation']}")
                assessment_components.extend([
                    gr.Radio(label="Assessment status", choices=[("Unassessed", "unassessed"), ("Estimated", "estimated"), ("Unknown", "unknown")], value="unassessed"),
                    gr.Slider(label="Score", minimum=0, maximum=5, step=0.1, value=None),
                    gr.Textbox(label="Rationale", lines=2),
                    gr.Radio(label="Basis", choices=[("Intended design", "intended_design"), ("Prototype-observed behavior", "prototype_observed"), ("Mixed", "mixed")]),
                    gr.Textbox(label="Evidence / observation", lines=2),
                    gr.Textbox(label="Uncertainty", lines=2),
                ])
        assessment_revisions = gr.State([])
        assessment_dirty = gr.State(False)
        assessment_timer = gr.Timer(2.0)
        for assessment_field in assessment_components:
            assessment_field.input(lambda: True, outputs=assessment_dirty)
        save_assessments_button = gr.Button("Save dimension assessments", variant="primary")

        gr.Markdown("## Comparator")
        gr.Markdown("Historical profiles are classroom assessments, not current product ratings or rankings.")
        comparator = gr.Dropdown(label="Historical comparator", choices=[])
        comparator_purpose = gr.Radio(label="Comparison purpose", choices=[("Task comparator", "task_comparator"), ("Design contrast", "design_contrast")], value="task_comparator")
        comparator_scope = gr.Textbox(label="Comparison scope or explanation", lines=2)
        save_comparator_button = gr.Button("Save comparator selection")
        comparator_snapshot_id = gr.State(None)
        comparison_chart = gr.Plot(label="Comparison radar")
        comparison_table = gr.Textbox(label="Comparison table", interactive=False, lines=8)

        gr.Markdown("## Adversarial-Risk Reflection")
        gr.Markdown("Distinguish malicious manipulation from ordinary incorrect outputs. Any score here is a discussion input, not a calibrated security assessment.")
        risk_score = gr.Slider(label="Optional subjective risk estimate", minimum=0, maximum=5, step=0.1, value=None)
        risk_entry = gr.Textbox(label="Plausible attack entry point", lines=2)
        risk_behavior = gr.Textbox(label="Unwanted behavior", lines=2)
        risk_affected = gr.Textbox(label="Affected data or action", lines=2)
        risk_consequence = gr.Textbox(label="Consequence", lines=2)
        risk_safeguard = gr.Textbox(label="Proposed safeguard", lines=2)
        risk_uncertainty = gr.Textbox(label="Remaining uncertainty", lines=2)
        save_risk_button = gr.Button("Save risk reflection")

        gr.Markdown("## Feedback-Loop Reflection")
        feedback_signal = gr.Textbox(label="Signal to collect", lines=2)
        feedback_meaning = gr.Textbox(label="What the signal might reveal", lines=2)
        feedback_change = gr.Textbox(label="Possible product change", lines=2)
        feedback_human = gr.Textbox(label="Human interpretation or approval needed", lines=2)
        feedback_evaluation = gr.Textbox(label="Evaluation after the change", lines=2)
        save_feedback_button = gr.Button("Save feedback-loop reflection")

        save_assessments_button.click(
            save_assessments_action,
            [token, project_id, assessment_revisions, *assessment_components],
            [status, assessment_revisions, assessment_dirty],
        )
        assessment_timer.tick(
            autosave_assessments_from_ui,
            [token, project_id, assessment_revisions, assessment_dirty, *assessment_components],
            [status, assessment_revisions, assessment_dirty],
        )
        save_comparator_button.click(
            save_comparator_from_ui,
            [token, project_id, comparator, comparator_purpose, comparator_scope],
            [status, comparator_snapshot_id],
        ).then(load_comparison_from_ui, [token, project_id, comparator_snapshot_id], [comparison_chart, comparison_table])
        save_risk_button.click(save_risk_reflection_from_ui, [token, project_id, risk_score, risk_entry, risk_behavior, risk_affected, risk_consequence, risk_safeguard, risk_uncertainty], status)
        save_feedback_button.click(save_feedback_reflection_from_ui, [token, project_id, feedback_signal, feedback_meaning, feedback_change, feedback_human, feedback_evaluation], status)

    return {
        "tab": tab,
        "assessment_components": assessment_components,
        "assessment_revisions": assessment_revisions,
        "assessment_dirty": assessment_dirty,
        "comparator": comparator,
        "comparison_chart": comparison_chart,
        "comparison_table": comparison_table,
        "risk_score": risk_score,
        "feedback_signal": feedback_signal,
    }
