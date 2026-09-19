"""App shell: header bar with language and feedback, real tabs, cross-tab wiring."""

import gradio as gr

from ..i18n import load_catalog
from . import tabs_assessment, tabs_backlog, tabs_priority, tabs_setup, tabs_summary
from .callbacks import (
    auto_login,
    backlog_columns_from_ui,
    checklist_text,
    delete_product_from_ui,
    dimension_notes_from_ui,
    import_baselines_from_ui,
    instructor_overview_from_ui,
    live_profile_from_ui,
    load_backlog_from_ui,
    load_comparator_choices,
    load_estimates_from_ui,
    load_experiment_choices,
    login,
    priority_text,
    provision_team_from_ui,
    workspace,
)

LANGUAGE_CHOICES = [("English", "en"), ("Deutsch", "de")]

BLOCKS_JS = """() => {
    window.aipmDirty = false;
    document.addEventListener('input', () => { window.aipmDirty = true; }, true);
    window.addEventListener('beforeunload', (event) => {
        if (window.aipmDirty) {
            event.preventDefault();
            event.returnValue = '';
        }
    });
    const observer = new MutationObserver(() => {
        const text = document.body.innerText || '';
        if (text.includes('Saved.') || text.includes('saved automatically')) window.aipmDirty = false;
    });
    observer.observe(document.body, {subtree: true, childList: true, characterData: true});
    document.addEventListener('click', (event) => {
        const button = event.target.closest('[role="tab"]');
        if (!button) return;
        const header = document.getElementById('aipm-section-header');
        if (header) header.innerText = button.innerText.trim();
    }, true);
}"""


def _build_instructor_panel(token, status, project_dropdown):
    with gr.Column(visible=False) as instructor_panel:
        gr.Markdown("## Instructor area")
        refresh_overview_button = gr.Button("Refresh course overview")
        overview_display = gr.Textbox(label="Course progress", interactive=False, lines=8)
        refresh_overview_button.click(instructor_overview_from_ui, token, overview_display)
        gr.Markdown("### Baseline import")
        import_directory = gr.Textbox(label="JSON directory", value="solutions")
        import_cohort = gr.Textbox(label="Cohort label", value="Legacy instructor reference")
        publish_import = gr.Checkbox(label="Publish after import", value=False)
        import_button = gr.Button("Import baseline JSON files")
        import_report = gr.Textbox(label="Import report", interactive=False, lines=5)
        import_button.click(import_baselines_from_ui, [token, import_directory, import_cohort, publish_import], [status, import_report])
        gr.Markdown("### Create team account")
        team_course = gr.Textbox(label="Course name", value="AIPM Workshop")
        team_alias = gr.Textbox(label="Team alias")
        team_password = gr.Textbox(label="Initial team password", type="password")
        create_team_button = gr.Button("Create team account")
        create_team_button.click(provision_team_from_ui, [token, team_course, team_alias, team_password], status)
        gr.Markdown("### Delete product")
        gr.Markdown("Deletion is manual and permanent. There is no automatic retention or deletion in this application.")
        delete_product_id = gr.Textbox(label="Product UUID to delete")
        confirm_delete = gr.Checkbox(label="I understand this permanently deletes the product", value=False)
        delete_product_button = gr.Button("Delete product", variant="stop")
        delete_product_button.click(delete_product_from_ui, [token, delete_product_id, confirm_delete], [status, project_dropdown])
    return instructor_panel


def build_app():
    with gr.Blocks(title="AIPM Toolkit", js=BLOCKS_JS) as app:
        token = gr.State(None)
        project_id = gr.State(None)
        project_revision = gr.State(None)
        status = gr.Markdown()
        with gr.Column(visible=True) as login_panel:
            username = gr.Textbox(label="Team alias or instructor username")
            password = gr.Textbox(label="Password", type="password")
            submit = gr.Button("Sign in", variant="primary")
        with gr.Column(visible=False) as workspace_panel:
            workspace_text = gr.Markdown()
        with gr.Column(visible=False) as team_panel:
            with gr.Row(elem_id="aipm-app-bar"):
                language_selector = gr.Dropdown(label="Language / Sprache", choices=LANGUAGE_CHOICES, value="en", scale=0)
                gr.Markdown("Project Setup", elem_id="aipm-section-header")
            with gr.Tabs():
                setup = tabs_setup.build_setup_tab(token, project_id, project_revision, status)
                assessment = tabs_assessment.build_assessment_tab(token, project_id, status)
                backlog = tabs_backlog.build_backlog_tab(token, project_id, status)
                priority = tabs_priority.build_priority_tab(token, project_id, status)
                summary = tabs_summary.build_summary_tab(token, project_id, status, setup["project_dropdown"])
            instructor_panel = _build_instructor_panel(token, status, setup["project_dropdown"])
        dimension_note_outputs = assessment["dimension_note_lists"]

        label_bindings = [
            (language_selector, "language", "Language / Sprache"),
            (setup["project_dropdown"], "projects", "Your products"),
            (setup["product_name"], "product_name", "Product name"),
            (setup["product_type"], "product_type", "AI product type"),
            (setup["description"], "description", "Short description"),
            (setup["target_user"], "target_user", "Target user"),
            (setup["job"], "job", "Job to be done"),
            (setup["problem"], "problem", "Current problem or workflow"),
            (setup["hypothesis"], "main_hypothesis", "Main value hypothesis"),
            (setup["figma_url"], "figma_url", "Figma prototype URL (optional)"),
            (assessment["comparator"], "comparator", "Historical comparator"),
            (backlog["notes_display"], "notes", "Saved notes"),
            (backlog["hypotheses_display"], "hypotheses", "Hypothesis backlog"),
            (priority["experiment_selector"], "experiments", "Reopen experiment"),
            (summary["checklist_display"], "checklist", "Workshop checklist"),
            (priority["priority_display"], "priority", "Priority matrix"),
            (summary["json_download"], "json_export", "JSON export"),
            (summary["markdown_download"], "markdown_export", "Markdown export"),
            (assessment["risk_score"], "risk_score", "Optional subjective risk estimate"),
            (assessment["feedback_signal"], "feedback_signal", "Signal to collect"),
        ]

        def update_ui_labels(language):
            labels = load_catalog(language)["labels"]
            return [gr.update(label=labels.get(key, default)) for _, key, default in label_bindings]

        language_selector.change(update_ui_labels, language_selector, [component for component, _, _ in label_bindings])

        project_dropdown = setup["project_dropdown"]
        submit.click(login, [username, password], [status, token, login_panel, workspace_panel]).then(workspace, token, [workspace_text, login_panel, instructor_panel, team_panel, project_dropdown])
        app.load(auto_login, outputs=[status, token, login_panel, workspace_panel]).then(workspace, token, [workspace_text, login_panel, instructor_panel, team_panel, project_dropdown])

        project_dropdown.change(
            load_estimates_from_ui,
            [token, project_id],
            assessment["assessment_components"] + [assessment["assessment_revisions"]],
        ).then(lambda: False, outputs=assessment["assessment_dirty"]).then(load_comparator_choices, outputs=assessment["comparator"]).then(live_profile_from_ui, [assessment["frozen_state"], *assessment["assessment_components"]], assessment["live_chart"]).then(
            dimension_notes_from_ui,
            [token, project_id, assessment["dimension_note_states"][0]],
            dimension_note_outputs[0],
        ).then(
            dimension_notes_from_ui,
            [token, project_id, assessment["dimension_note_states"][1]],
            dimension_note_outputs[1],
        ).then(
            dimension_notes_from_ui,
            [token, project_id, assessment["dimension_note_states"][2]],
            dimension_note_outputs[2],
        ).then(
            dimension_notes_from_ui,
            [token, project_id, assessment["dimension_note_states"][3]],
            dimension_note_outputs[3],
        ).then(
            dimension_notes_from_ui,
            [token, project_id, assessment["dimension_note_states"][4]],
            dimension_note_outputs[4],
        ).then(
            load_backlog_from_ui,
            [token, project_id],
            [backlog["notes_display"], backlog["hypotheses_display"], backlog["hypothesis_note"], backlog["relation_source"], backlog["relation_target"], backlog["note_edit_selector"], backlog["hypothesis_edit_selector"]],
        ).then(lambda choices: choices, backlog["relation_source"], priority["experiment_primary"]).then(load_experiment_choices, [token, project_id], priority["experiment_selector"]).then(checklist_text, [token, project_id], summary["checklist_display"]).then(priority_text, [token, project_id], priority["priority_display"]).then(
            backlog_columns_from_ui,
            [token, project_id],
            [backlog["assumption_selector"], backlog["question_selector"], backlog["assumptions_display"], backlog["questions_display"]],
        )
    return app
