"""Prioritization tab (slice 1: guidance and experiments; slider ranking arrives in slice 5)."""

import gradio as gr

from .callbacks import (
    autosave_experiment_from_ui,
    load_experiment_choices,
    load_experiment_edit_from_ui,
    save_experiment_action,
    save_experiment_plan,
)

METHOD_CHOICES = [
    ("Prototype walkthrough", "prototype_walkthrough"),
    ("User interview", "user_interview"),
    ("Comparative usability test", "comparative_usability_test"),
    ("Model/output evaluation", "model_output_evaluation"),
    ("Technical feasibility test", "technical_feasibility_test"),
    ("Cost estimate/simulation", "cost_estimate_simulation"),
    ("Pilot", "pilot"),
    ("Other", "other"),
]


def build_priority_tab(token, project_id, status):
    with gr.Tab("Prioritization") as tab:
        gr.Markdown("Rank hypotheses by risk and evidence, then plan the experiment for the top uncertainty. Interactive ranking sliders arrive in the next slice.")
        priority_display = gr.Textbox(label="Priority guidance", interactive=False, lines=8)

        gr.Markdown("## Experiments")
        experiment_selector = gr.Dropdown(label="Reopen experiment", choices=[])
        experiment_primary = gr.Dropdown(label="Primary hypothesis", choices=[])
        experiment_title = gr.Textbox(label="Experiment title")
        experiment_method = gr.Dropdown(label="Method", choices=METHOD_CHOICES, value="prototype_walkthrough")
        create_experiment_button = gr.Button("Create experiment plan")
        experiment_id = gr.State(None)
        experiment_revision = gr.State(None)
        experiment_procedure = gr.Textbox(label="Procedure", lines=3)
        experiment_participants = gr.Textbox(label="Participants or representative dataset", lines=2)
        experiment_baseline = gr.Textbox(label="Comparison / baseline", lines=2)
        experiment_metric = gr.Textbox(label="Metric", lines=2)
        experiment_success = gr.Textbox(label="Success criterion", lines=2)
        experiment_guardrail = gr.Textbox(label="Guardrail", lines=2)
        experiment_resources = gr.Textbox(label="Required resources", lines=2)
        experiment_owner = gr.Textbox(label="Owner")
        experiment_date = gr.Textbox(label="Planned date")
        experiment_status = gr.Dropdown(label="Status", choices=["planned", "in_progress", "completed", "cancelled"], value="planned")
        experiment_results = gr.Textbox(label="Observations / results", lines=3)
        experiment_links = gr.Textbox(label="Evidence links", lines=2)
        experiment_limitations = gr.Textbox(label="Limitations", lines=2)
        experiment_conclusion = gr.Textbox(label="Conclusion", lines=2)
        experiment_decision = gr.Dropdown(label="Resulting decision", choices=["continue", "revise", "retest", "stop", "undecided"], value="undecided")
        save_experiment_button = gr.Button("Save experiment")
        experiment_dirty = gr.State(False)
        experiment_timer = gr.Timer(2.0)
        experiment_fields = [experiment_title, experiment_method, experiment_procedure, experiment_participants, experiment_baseline, experiment_metric, experiment_success, experiment_guardrail, experiment_resources, experiment_owner, experiment_date, experiment_status, experiment_results, experiment_links, experiment_limitations, experiment_conclusion, experiment_decision]
        for experiment_field in experiment_fields:
            experiment_field.input(lambda: True, outputs=experiment_dirty)

        create_experiment_button.click(save_experiment_plan, [token, project_id, experiment_primary, experiment_title, experiment_method], [status, experiment_id, experiment_revision]).then(load_experiment_choices, [token, project_id], experiment_selector).then(lambda: False, outputs=experiment_dirty)
        save_experiment_button.click(
            save_experiment_action,
            [token, project_id, experiment_id, experiment_revision, experiment_procedure, experiment_participants, experiment_baseline, experiment_metric, experiment_success, experiment_guardrail, experiment_resources, experiment_owner, experiment_date, experiment_status, experiment_results, experiment_links, experiment_limitations, experiment_conclusion, experiment_decision],
            [status, experiment_revision, experiment_dirty],
        )
        experiment_timer.tick(
            autosave_experiment_from_ui,
            [token, project_id, experiment_id, experiment_revision, experiment_dirty, experiment_procedure, experiment_participants, experiment_baseline, experiment_metric, experiment_success, experiment_guardrail, experiment_resources, experiment_owner, experiment_date, experiment_status, experiment_results, experiment_links, experiment_limitations, experiment_conclusion, experiment_decision],
            [status, experiment_revision, experiment_dirty],
        )
        experiment_selector.change(
            load_experiment_edit_from_ui,
            [token, experiment_selector],
            [experiment_title, experiment_method, experiment_procedure, experiment_participants, experiment_baseline, experiment_metric, experiment_success, experiment_guardrail, experiment_resources, experiment_owner, experiment_date, experiment_status, experiment_results, experiment_links, experiment_limitations, experiment_conclusion, experiment_decision, experiment_revision],
        ).then(lambda selected: selected, experiment_selector, experiment_id).then(lambda: False, outputs=experiment_dirty)

    return {
        "tab": tab,
        "priority_display": priority_display,
        "experiment_selector": experiment_selector,
        "experiment_primary": experiment_primary,
    }
