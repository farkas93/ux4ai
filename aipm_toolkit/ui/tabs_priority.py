"""Prioritization tab: per-hypothesis risk/evidence sliders with real-time ranking, plus experiments."""

import gradio as gr

from .callbacks import (
    PLACEMENT_SLOTS,
    autosave_experiment_from_ui,
    load_experiment_choices,
    load_experiment_edit_from_ui,
    ranked_backlog_from_ui,
    save_experiment_action,
    save_experiment_plan,
    save_placement_from_ui,
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
        gr.Markdown("Left: open a hypothesis and set risk and evidence (0-10; every hypothesis starts at 0/0). Right: the ranked backlog updates in real time - risk 10 with evidence 0 ranks first, evidence 10 with risk 0 ranks last.")
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

    placement_outputs = []
    for slot in slot_components:
        placement_outputs.extend([slot["accordion"], slot["statement"], slot["risk"], slot["evidence"], slot["id"], slot["revision"]])

    return {
        "tab": tab,
        "placement_outputs": placement_outputs,
        "ranking_display": ranking_display,
        "matrix_fig": matrix_fig,
        "experiment_selector": experiment_selector,
        "experiment_primary": experiment_primary,
        "create_experiment_button": create_experiment_button,
        "save_experiment_button": save_experiment_button,
    }
