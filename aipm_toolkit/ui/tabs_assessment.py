"""Assessment tab: dimension sliders with reasoning and inline notes (left), comparator and live radar (right), reflections below."""

import gradio as gr

from ..dimensions import DEFAULT_DIMENSIONS
from .callbacks import (
    add_dimension_note_from_ui,
    live_profile_from_ui,
    on_comparator_selected,
    save_assessments_action,
    save_feedback_reflection_from_ui,
    save_risk_reflection_from_ui,
)

DIMENSION_NOTE_CHOICES = ["Question", "Assumption"]


def build_assessment_tab(token, project_id, status):
    with gr.Tab("Assessment") as tab:
        frozen_state = gr.State({})
        unsaved_note = gr.Markdown()

        with gr.Row():
            # LEFT COLUMN: 5 Dimensions with Sliders, Notes, and Inline Questions/Assumptions
            with gr.Column(scale=3):
                gr.Markdown("### Product Dimensions")
                gr.Markdown("Set your product's intended characteristic (0.0 to 5.0) and record key reasoning.")

                sliders = []
                reasoning_fields = []
                assessment_components = []
                dimension_note_states = []
                dimension_note_lists = []

                for index, definition in enumerate(DEFAULT_DIMENSIONS):
                    with gr.Accordion(f"{definition['title']}", open=(index == 0)):
                        gr.Markdown(
                            f"**0.0:** {definition['low_anchor']}  |  **5.0:** {definition['high_anchor']}\n\n"
                            f"*{definition['explanation']}*"
                        )
                        slider = gr.Slider(
                            label=f"{definition['title']} score",
                            minimum=0.0,
                            maximum=5.0,
                            step=0.1,
                            value=2.5,
                        )
                        reasoning = gr.Textbox(
                            label="Reasoning / Notes",
                            placeholder="Why this score? What are key observations or decisions?",
                            lines=2,
                        )
                        sliders.append(slider)
                        reasoning_fields.append(reasoning)
                        assessment_components.extend([slider, reasoning])

                        dim_key_state = gr.State(definition["key"])
                        dimension_note_states.append(dim_key_state)

                        gr.Markdown("#### Questions & Assumptions")
                        with gr.Row():
                            note_type = gr.Dropdown(
                                choices=DIMENSION_NOTE_CHOICES,
                                value="Question",
                                label="Type",
                                scale=1,
                            )
                            note_input = gr.Textbox(
                                placeholder="Add a question or assumption to test...",
                                show_label=False,
                                scale=4,
                            )
                            add_btn = gr.Button("Add", variant="secondary", scale=1)

                        notes_list = gr.Textbox(
                            show_label=False,
                            interactive=False,
                            lines=3,
                            placeholder="No questions or assumptions added for this dimension yet.",
                        )
                        dimension_note_lists.append(notes_list)

                        add_btn.click(
                            add_dimension_note_from_ui,
                            [token, project_id, dim_key_state, note_type, note_input],
                            [status, notes_list, note_input],
                        )

                assessment_revisions = gr.State([])
                assessment_dirty = gr.State(False)
                save_assessments_button = gr.Button("Save dimension assessments", variant="primary")

            # RIGHT COLUMN: Comparator Selector, Live Spider Chart, and Comparison Table
            with gr.Column(scale=2):
                gr.Markdown("### Benchmark & Comparison")
                comparator_dropdown = gr.Dropdown(
                    label="Compare with another product (optional)",
                    choices=[],
                    value=None,
                )

                live_chart = gr.Plot(label="Dimension Radar")

                with gr.Accordion("Comparison Details & Differences", open=False):
                    comparison_table = gr.Textbox(
                        show_label=False,
                        interactive=False,
                        lines=7,
                    )

        # Purely event-driven live spider chart updates:
        for slider in sliders:
            slider.change(live_profile_from_ui, [frozen_state, *sliders], live_chart)
            slider.input(live_profile_from_ui, [frozen_state, *sliders], live_chart)

        # Comparator dropdown event: immediately updates frozen_state, table, and chart
        comparator_dropdown.change(
            on_comparator_selected,
            [token, project_id, comparator_dropdown],
            [frozen_state, comparison_table],
        ).then(
            live_profile_from_ui,
            [frozen_state, *sliders],
            live_chart,
        )

        # Mark dirty when sliders or reasoning change
        def mark_dirty():
            return True

        for comp in assessment_components:
            comp.input(mark_dirty, outputs=assessment_dirty)

        assessment_dirty.change(
            lambda dirty: "⚠ Unsaved changes — save dimension assessments to keep them." if dirty else "",
            assessment_dirty,
            unsaved_note,
        )

        # Save assessments button
        save_assessments_button.click(
            save_assessments_action,
            [token, project_id, assessment_revisions, *assessment_components],
            [status, assessment_revisions, assessment_dirty],
        )

        # BELOW: Adversarial-Risk and Feedback-Loop Reflections
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

        save_risk_button.click(
            save_risk_reflection_from_ui,
            [token, project_id, risk_score, risk_entry, risk_behavior, risk_affected, risk_consequence, risk_safeguard, risk_uncertainty],
            status,
        )
        save_feedback_button.click(
            save_feedback_reflection_from_ui,
            [token, project_id, feedback_signal, feedback_meaning, feedback_change, feedback_human, feedback_evaluation],
            status,
        )

    return {
        "tab": tab,
        "sliders": sliders,
        "reasoning_fields": reasoning_fields,
        "assessment_components": assessment_components,
        "assessment_revisions": assessment_revisions,
        "assessment_dirty": assessment_dirty,
        "dimension_note_states": dimension_note_states,
        "dimension_note_lists": dimension_note_lists,
        "comparator": comparator_dropdown,
        "comparison_table": comparison_table,
        "live_chart": live_chart,
        "frozen_state": frozen_state,
        "risk_score": risk_score,
        "feedback_signal": feedback_signal,
    }
