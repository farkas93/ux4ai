"""Assessment tab: dimensions, current notes, historical comparator and radar."""

import gradio as gr

from ..dimensions import DEFAULT_DIMENSIONS
from .callbacks import (
    add_dimension_note_from_ui,
    live_profile_from_ui,
    on_comparator_selected,
    save_assessments_action,
)


def build_assessment_tab(token, product_dropdown, status):
    with gr.Tab("Assessment") as tab:
        frozen_state = gr.State({})
        unsaved_note = gr.Markdown()

        with gr.Row():
            # LEFT COLUMN: 5 Dimensions with Sliders, Notes, and Inline Questions/Assumptions
            with gr.Column(scale=3):
                gr.Markdown("### Product Dimensions")
                gr.Markdown("Set your product's intended characteristic (0.0 to 5.0) and record key reasoning.")
                gr.Markdown("Add questions and assumptions here; edit, move or remove them in **Backlog Creator**.")

                sliders = []
                reasoning_fields = []
                assessment_components = []
                dimension_note_states = []
                dimension_note_lists = []
                note_events = []

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

                        gr.Markdown("#### Current Questions & Assumptions")
                        notes_list = gr.Textbox(
                            show_label=False,
                            interactive=False,
                            lines=3,
                            placeholder="No questions or assumptions for this dimension yet.",
                        )
                        dimension_note_lists.append(notes_list)
                        with gr.Row():
                            note_type = gr.Radio(choices=["Question", "Assumption"], value="Question", label="Add")
                            note_text = gr.Textbox(label="Question or assumption", placeholder="What should the team test?", scale=3)
                            add_button = gr.Button("Add", scale=1)
                        note_events.append(add_button.click(add_dimension_note_from_ui, [token, product_dropdown, dim_key_state, note_type, note_text], [status, notes_list, note_text]))

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
            [token, product_dropdown, comparator_dropdown],
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
            [token, product_dropdown, assessment_revisions, *assessment_components],
            [status, assessment_revisions, assessment_dirty],
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
        "note_events": note_events,
        "comparator": comparator_dropdown,
        "comparison_table": comparison_table,
        "live_chart": live_chart,
        "frozen_state": frozen_state,
    }
