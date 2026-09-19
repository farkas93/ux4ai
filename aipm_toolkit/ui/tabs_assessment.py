"""Assessment tab: dimension accordions with inline notes (left), live chart and comparator (right), reflections below."""

import gradio as gr

from ..dimensions import DEFAULT_DIMENSIONS
from .callbacks import (
    add_dimension_note_from_ui,
    autosave_assessments_from_ui,
    comparison_table_from_ui,
    live_profile_from_ui,
    load_frozen_profile_from_ui,
    save_assessments_action,
    save_comparator_from_ui,
    save_feedback_reflection_from_ui,
    save_risk_reflection_from_ui,
)

DIMENSION_NOTE_CHOICES = [("Question", "question"), ("Assumption", "assumption")]


def build_assessment_tab(token, project_id, status):
    with gr.Tab("Assessment") as tab:
        frozen_state = gr.State({})
        unsaved_note = gr.Markdown()
        with gr.Row():
            with gr.Column():
                gr.Markdown("### Dimensions")
                gr.Markdown("Higher scores are not inherently better. Mark a dimension Unknown when the team cannot make a reasoned estimate yet.")
                assessment_components = []
                dimension_note_states = []
                dimension_note_lists = []
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
                        dimension_key_state = gr.State(definition["key"])
                        dimension_note_states.append(dimension_key_state)
                        with gr.Accordion("Questions and assumptions for this dimension", open=False):
                            dimension_note_list = gr.Textbox(label=f"{definition['title']}: notes", interactive=False, lines=3)
                            dimension_note_lists.append(dimension_note_list)
                            with gr.Row():
                                inline_note_type = gr.Dropdown(label="Type", choices=DIMENSION_NOTE_CHOICES, value="question", scale=0)
                                inline_note_text = gr.Textbox(label="New question or assumption", lines=2)
                            add_note_button = gr.Button("Add to this dimension")
                            add_note_button.click(
                                add_dimension_note_from_ui,
                                [token, project_id, dimension_key_state, inline_note_type, inline_note_text],
                                [status, dimension_note_list],
                            )
                assessment_revisions = gr.State([])
                assessment_dirty = gr.State(False)
                assessment_timer = gr.Timer(2.0)
                save_assessments_button = gr.Button("Save dimension assessments", variant="primary")

            with gr.Column():
                gr.Markdown("### Live profile")
                gr.Markdown("The chart shows your currently entered values. Unsaved changes must still be saved.")
                live_chart = gr.Plot(label="Live spider chart")
                gr.Markdown("### Comparator (optional)")
                gr.Markdown("Historical profiles are classroom assessments, not current product ratings or rankings.")
                comparator = gr.Dropdown(label="Historical comparator", choices=[])
                comparator_purpose = gr.Radio(label="Comparison purpose", choices=[("Task comparator", "task_comparator"), ("Design contrast", "design_contrast")], value="task_comparator")
                comparator_scope = gr.Textbox(label="Comparison scope or explanation", lines=2)
                save_comparator_button = gr.Button("Save comparator selection")
                comparator_snapshot_id = gr.State(None)
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

        def mark_dirty():
            return True

        for assessment_field in assessment_components:
            assessment_field.input(mark_dirty, outputs=assessment_dirty)
        assessment_dirty.change(lambda dirty: "⚠ Unsaved changes — save dimension assessments to keep them." if dirty else "", assessment_dirty, unsaved_note)

        save_assessments_button.click(
            save_assessments_action,
            [token, project_id, assessment_revisions, *assessment_components],
            [status, assessment_revisions, assessment_dirty],
        ).then(live_profile_from_ui, [frozen_state, *assessment_components], live_chart)
        assessment_timer.tick(
            autosave_assessments_from_ui,
            [token, project_id, assessment_revisions, assessment_dirty, *assessment_components],
            [status, assessment_revisions, assessment_dirty],
        ).then(live_profile_from_ui, [frozen_state, *assessment_components], live_chart)
        for assessment_field in assessment_components:
            assessment_field.input(live_profile_from_ui, [frozen_state, *assessment_components], live_chart)

        save_comparator_button.click(
            save_comparator_from_ui,
            [token, project_id, comparator, comparator_purpose, comparator_scope],
            [status, comparator_snapshot_id],
        ).then(load_frozen_profile_from_ui, [token, project_id, comparator_snapshot_id], frozen_state).then(live_profile_from_ui, [frozen_state, *assessment_components], live_chart).then(comparison_table_from_ui, [token, project_id, comparator_snapshot_id], comparison_table)

        save_risk_button.click(save_risk_reflection_from_ui, [token, project_id, risk_score, risk_entry, risk_behavior, risk_affected, risk_consequence, risk_safeguard, risk_uncertainty], status)
        save_feedback_button.click(save_feedback_reflection_from_ui, [token, project_id, feedback_signal, feedback_meaning, feedback_change, feedback_human, feedback_evaluation], status)

    return {
        "tab": tab,
        "assessment_components": assessment_components,
        "assessment_revisions": assessment_revisions,
        "assessment_dirty": assessment_dirty,
        "dimension_note_states": dimension_note_states,
        "dimension_note_lists": dimension_note_lists,
        "comparator": comparator,
        "comparison_table": comparison_table,
        "live_chart": live_chart,
        "frozen_state": frozen_state,
        "risk_score": risk_score,
        "feedback_signal": feedback_signal,
    }
