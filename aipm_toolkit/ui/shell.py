"""App shell: header bar with product switcher, language, and real tabs."""

import gradio as gr

from ..i18n import load_catalog
from . import (
    tabs_assessment,
    tabs_backlog,
    tabs_history,
    tabs_improvement,
    tabs_priority,
    tabs_safety,
    tabs_setup,
    tabs_summary,
)
from .callbacks import (
    archive_backlog_row_from_ui,
    auto_login,
    checklist_text,
    create_project_from_ui,
    delete_product_from_ui,
    dimension_notes_from_ui,
    instructor_overview_from_ui,
    live_profile_from_ui,
    load_backlog_table_from_ui,
    load_comparator_choices,
    load_estimates_from_ui,
    load_placements_from_ui,
    load_project_from_ui,
    login,
    preview_upload_from_ui,
    project_history_from_ui,
    provision_team_from_ui,
    publish_upload_from_ui,
    save_backlog_row_from_ui,
    summary_preview_from_ui,
    workspace,
)
from .safety_callbacks import learning_notes_ui, load_primary_loop_ui
from .tunnel_callbacks import (
    close_public_access_from_ui,
    open_public_access_from_ui,
    public_access_status_from_ui,
)
from .workspace_style import WORKSPACE_CSS

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

BLOCKS_CSS = """
footer {
    display: none !important;
}
.gradio-container { max-width: 1440px !important; margin: auto !important; }
#toolkit-brand { padding: 24px 8px 12px; }
#toolkit-brand h1 { font-size: 28px; letter-spacing: -.03em; margin-bottom: 6px; }
#toolkit-brand p { color: var(--body-text-color-subdued); }
#toolkit-login { max-width: 460px; margin: 32px auto; padding: 28px;
    border: 1px solid var(--border-color-primary); border-radius: 16px; }
#aipm-app-bar { padding: 16px; border-radius: 14px; margin: 8px 0 16px; }
#aipm-status-banner { border-left: 3px solid var(--color-accent); padding: 8px 14px; }
#aipm-status-banner:empty { display: none; }
.tab-nav { gap: 4px; flex-wrap: wrap; padding-bottom: 8px; }
.tab-nav button { border-radius: 8px; padding: 10px 14px; }
.tabitem { padding-top: 20px !important; }
.toolkit-form-card { border: 1px solid var(--border-color-primary); border-radius: 12px; padding: 20px; }
@media (max-width: 760px) {
    #toolkit-brand { padding: 16px 4px 8px; }
    .tab-nav { flex-wrap: nowrap; overflow-x: auto; }
    .tab-nav button { white-space: nowrap; flex-shrink: 0; }
}
.backlog-table-container {
    max-height: 560px;
    overflow-y: auto;
    border: 1px solid #e5e7eb;
    border-radius: 8px;
    padding: 12px;
    margin-bottom: 12px;
}
.backlog-table-header {
    font-weight: 600;
    margin-bottom: 4px;
    padding-bottom: 4px;
    border-bottom: 2px solid #e5e7eb;
}
"""


def _build_instructor_panel(token, status, product_dropdown):
    with gr.Column(visible=False) as instructor_panel:
        gr.Markdown("## Instructor\nManage the workshop and team access.", elem_classes=["toolkit-page-heading"])
        refresh_overview_button = gr.Button("Refresh course overview")
        overview_display = gr.Textbox(label="Course progress", interactive=False, lines=8)
        refresh_overview_button.click(instructor_overview_from_ui, token, overview_display)
        gr.Markdown("### Public access (Gradio share link)")
        gr.Markdown("LAN NodePort access is always available. Opening a public link does not bypass team or instructor sign-in. The link closes when the app pod restarts.")
        access_status = gr.Textbox(label="Access status", value="Public Gradio link is closed. LAN access remains available.", interactive=False)
        public_url = gr.Textbox(label="Temporary public URL", interactive=False)
        with gr.Row():
            refresh_access = gr.Button("Refresh access status")
            open_access = gr.Button("Open public link", variant="primary")
            close_access = gr.Button("Close public link", variant="stop")
        refresh_access.click(public_access_status_from_ui, token, [access_status, public_url])
        open_access.click(open_public_access_from_ui, token, [access_status, public_url])
        close_access.click(close_public_access_from_ui, token, [access_status, public_url])
        with gr.Accordion("Historical reference import", open=False):
            import_files = gr.File(label="Legacy JSON files", file_count="multiple", file_types=[".json"], type="filepath")
            import_manifest = gr.File(label="Import manifest JSON", file_count="single", file_types=[".json"], type="filepath")
            with gr.Row():
                preview_button = gr.Button("Preview import")
                publish_button = gr.Button("Publish preview", variant="primary")
            import_batch_id = gr.State(None)
            import_report = gr.Textbox(label="Import report", interactive=False, lines=8)
        preview_button.click(preview_upload_from_ui, [token, import_files, import_manifest], [status, import_report, import_batch_id])
        publish_button.click(publish_upload_from_ui, [token, import_batch_id], [status, import_report])
        gr.Markdown("### Create team account")
        team_course = gr.Textbox(label="Course name", value="AIPM Workshop")
        team_alias = gr.Textbox(label="Team alias")
        team_password = gr.Textbox(label="Initial team password", type="password")
        create_team_button = gr.Button("Create team account")
        create_team_button.click(provision_team_from_ui, [token, team_course, team_alias, team_password], status)
        with gr.Accordion("Product administration", open=False):
            gr.Markdown("Deletion is manual and permanent.")
            delete_product_id = gr.Textbox(label="Product UUID to delete")
            confirm_delete = gr.Checkbox(label="I understand this permanently deletes the product", value=False)
            delete_product_button = gr.Button("Delete product", variant="stop")
        delete_product_button.click(delete_product_from_ui, [token, delete_product_id, confirm_delete], [status, product_dropdown])
    return instructor_panel


def build_app():
    theme = gr.themes.Soft(primary_hue="teal", secondary_hue="slate", neutral_hue="slate",
                           font=[gr.themes.Font("ui-sans-serif"), gr.themes.Font("system-ui"), gr.themes.Font("sans-serif")]).set(
        block_label_background_fill="transparent", block_label_background_fill_dark="transparent",
        block_label_border_width="0px", block_label_shadow="none", block_label_padding="0px",
        block_label_text_color="*body_text_color", block_label_text_color_dark="*body_text_color",
        block_label_text_size="13px", block_label_margin="0px",
        body_text_size="14px", input_text_size="14px", prose_text_size="14px",
        button_large_text_size="14px", button_large_padding="10px 16px",
        block_title_text_size="14px", block_padding="12px", layout_gap="16px",
    )
    with gr.Blocks(title="AI Product Toolkit", theme=theme, js=BLOCKS_JS, css=WORKSPACE_CSS) as app:
        token = gr.State(None)
        project_revision = gr.State(None)
        delete_confirm_state = gr.State(True)

        status = gr.Markdown(elem_id="aipm-status-banner")
        session_notice = gr.Markdown(elem_id="toolkit-session-note")
        with gr.Column(visible=True, elem_id="toolkit-login") as login_panel:
            gr.Markdown("### Welcome to your workspace\nExplore value, question assumptions, and build a hypothesis backlog. Use the account provided for your course.")
            username = gr.Textbox(label="Team alias or instructor username")
            password = gr.Textbox(label="Password", type="password")
            submit = gr.Button("Sign in", variant="primary")
            gr.Markdown("Need help signing in? Ask your instructor.")
        with gr.Column(visible=False) as workspace_panel:
            workspace_text = gr.Markdown(elem_id="toolkit-workspace-note")
        with gr.Column(visible=False) as team_panel:
            with gr.Row(elem_id="aipm-app-bar"):
                gr.HTML('<strong class="toolkit-wordmark">AI Product Toolkit</strong>', elem_id="toolkit-brand")
                product_dropdown = gr.Dropdown(label="Product", show_label=False, choices=[], interactive=True, container=False, elem_id="toolkit-product")
                new_product_btn = gr.Button("+ Product", variant="secondary", elem_id="toolkit-new-product")
                language_selector = gr.Dropdown(label="Language / Sprache", show_label=False, choices=LANGUAGE_CHOICES, value="en", container=False, elem_id="toolkit-language")
                gr.HTML('<details><summary>Account &amp; actions</summary><a href="/auth/logout">Sign out</a></details>', elem_classes=["toolkit-account"])
            with gr.Accordion("Product administration", open=False, elem_id="toolkit-product-admin"):
                delete_product_btn = gr.Button("Delete product", variant="stop", size="sm")

            with gr.Row(visible=False, variant="panel") as new_product_panel:
                new_product_input = gr.Textbox(label="New product name", placeholder="e.g. HealthAI Assistant", scale=3)
                create_product_btn = gr.Button("Create", variant="primary", scale=1)
                cancel_product_btn = gr.Button("Cancel", variant="secondary", scale=1)

            with gr.Row(visible=False, variant="panel") as delete_confirm_panel:
                gr.Markdown("⚠️ **Are you sure you want to permanently delete the selected product and all its data?**")
                confirm_delete_btn = gr.Button("Yes, delete permanently", variant="stop", scale=1)
                cancel_delete_btn = gr.Button("Cancel", variant="secondary", scale=1)

            section_names = ["Project Setup", "Assessment", "AI Safety", "Self-Improvement", "Backlog creator", "Prioritization", "Summary & Export", "Project History"]
            mobile_section = gr.Dropdown(label="Section", choices=section_names, value="Project Setup", elem_id="toolkit-mobile-section", container=False)
            with gr.Row(elem_id="toolkit-workspace"):
                with gr.Column(scale=0, min_width=180, elem_id="toolkit-sidebar"):
                    desktop_section = gr.Radio(label="Workspace", choices=section_names, value="Project Setup", container=False, elem_id="toolkit-desktop-section")
                with gr.Column(scale=1, min_width=0, elem_id="toolkit-main"), gr.Tabs(elem_id="toolkit-sections", selected="Project Setup") as sections:
                    setup = tabs_setup.build_setup_tab(token, product_dropdown, project_revision, status)
                    assessment = tabs_assessment.build_assessment_tab(token, product_dropdown, status)
                    safety = tabs_safety.build_safety_tab(token, product_dropdown, status)
                    improvement = tabs_improvement.build_improvement_tab(token, product_dropdown, status)
                    backlog = tabs_backlog.build_backlog_tab(token, product_dropdown, status)
                    priority = tabs_priority.build_priority_tab(token, product_dropdown, status)
                    summary = tabs_summary.build_summary_tab(token, product_dropdown, status)
                    history = tabs_history.build_history_tab(token, product_dropdown)
            mobile_section.input(lambda name: gr.update(selected=name), mobile_section, sections)
            desktop_section.input(lambda name: gr.update(selected=name), desktop_section, sections)
            for page, name in zip([setup, assessment, safety, improvement, backlog, priority, summary, history], section_names):
                page["tab"].select(lambda name=name: (name, name), outputs=[mobile_section, desktop_section])

        instructor_panel = _build_instructor_panel(token, status, product_dropdown)
        dimension_note_outputs = assessment["dimension_note_lists"]
        status.change(project_history_from_ui, [token, product_dropdown], history["history"])

        label_bindings = [
            (language_selector, "language", "Language / Sprache"),
            (product_dropdown, "projects", "Product"),
            (setup["product_type"], "product_type", "AI product type"),
            (setup["description"], "description", "Short description"),
            (setup["target_user"], "target_user", "Target user"),
            (setup["job"], "job", "Job to be done"),
            (setup["problem"], "problem", "Current problem or workflow"),
            (setup["hypothesis"], "main_hypothesis", "Main value hypothesis"),
            (setup["figma_url"], "figma_url", "Figma prototype URL (optional)"),
            (assessment["comparator"], "comparator", "Historical comparator"),
            (summary["checklist_display"], "checklist", "Workshop checklist"),
            (summary["pdf_download"], "pdf_export", "PDF export"),
            (summary["json_download"], "json_export", "JSON export"),
            (summary["markdown_download"], "markdown_export", "Markdown export"),
        ]

        def update_ui_labels(language):
            labels = load_catalog(language)["labels"]
            return [gr.update(label=labels.get(key, default)) for _, key, default in label_bindings]

        language_selector.change(update_ui_labels, language_selector, [component for component, _, _ in label_bindings])

        # New product panel toggle
        new_product_btn.click(lambda: gr.update(visible=True), outputs=new_product_panel)
        cancel_product_btn.click(lambda: (gr.update(visible=False), ""), outputs=[new_product_panel, new_product_input])

        # Delete confirmation panel toggle
        delete_product_btn.click(lambda: gr.update(visible=True), outputs=delete_confirm_panel)
        cancel_delete_btn.click(lambda: gr.update(visible=False), outputs=delete_confirm_panel)

        def _wire_product_load(trigger):
            return (
                trigger.then(
                    load_project_from_ui,
                    [token, product_dropdown],
                    [
                        setup["description"],
                        setup["target_user"],
                        setup["job"],
                        setup["problem"],
                        setup["hypothesis"],
                        setup["product_type"],
                        setup["figma_url"],
                        project_revision,
                    ],
                )
                .then(lambda: False, outputs=setup["brief_dirty"])
                .then(
                    load_estimates_from_ui,
                    [token, product_dropdown],
                    assessment["assessment_components"] + [assessment["assessment_revisions"]],
                )
                .then(lambda: False, outputs=assessment["assessment_dirty"])
                .then(load_primary_loop_ui, [token, product_dropdown], [improvement["loop_id"], *improvement["fields"]])
                .then(learning_notes_ui, [token, product_dropdown, improvement["note_section"]], improvement["notes_list"])
                .then(
                    load_comparator_choices,
                    outputs=assessment["comparator"],
                )
                .then(
                    live_profile_from_ui,
                    [assessment["frozen_state"], *assessment["sliders"]],
                    assessment["live_chart"],
                )
                .then(
                    dimension_notes_from_ui,
                    [token, product_dropdown, assessment["dimension_note_states"][0]],
                    dimension_note_outputs[0],
                )
                .then(
                    dimension_notes_from_ui,
                    [token, product_dropdown, assessment["dimension_note_states"][1]],
                    dimension_note_outputs[1],
                )
                .then(
                    dimension_notes_from_ui,
                    [token, product_dropdown, assessment["dimension_note_states"][2]],
                    dimension_note_outputs[2],
                )
                .then(
                    dimension_notes_from_ui,
                    [token, product_dropdown, assessment["dimension_note_states"][3]],
                    dimension_note_outputs[3],
                )
                .then(
                    dimension_notes_from_ui,
                    [token, product_dropdown, assessment["dimension_note_states"][4]],
                    dimension_note_outputs[4],
                )
                .then(learning_notes_ui, [token, product_dropdown, safety["note_section"], safety["checkpoint_states"][0]], safety["note_lists"][0])
                .then(learning_notes_ui, [token, product_dropdown, safety["note_section"], safety["checkpoint_states"][1]], safety["note_lists"][1])
                .then(learning_notes_ui, [token, product_dropdown, safety["note_section"], safety["checkpoint_states"][2]], safety["note_lists"][2])
                .then(learning_notes_ui, [token, product_dropdown, safety["note_section"], safety["checkpoint_states"][3]], safety["note_lists"][3])
                .then(learning_notes_ui, [token, product_dropdown, safety["note_section"], safety["checkpoint_states"][4]], safety["note_lists"][4])
                .then(learning_notes_ui, [token, product_dropdown, safety["note_section"], safety["checkpoint_states"][5]], safety["note_lists"][5])
                .then(
                    load_backlog_table_from_ui,
                    [token, product_dropdown],
                    backlog["table_flat_outputs"] + [backlog["visible_rows_count"]],
                )
                .then(
                    checklist_text,
                    [token, product_dropdown],
                    summary["checklist_display"],
                )
                .then(
                    load_placements_from_ui,
                    [token, product_dropdown],
                    priority["placement_outputs"] + [priority["ranking_display"], priority["matrix_fig"]],
                )
                .then(
                    summary_preview_from_ui,
                    [token, product_dropdown],
                    summary["summary_preview"],
                )
                .then(
                    project_history_from_ui,
                    [token, product_dropdown],
                    history["history"],
                )
            )

        # Wire product loading on dropdown change
        _wire_product_load(product_dropdown.change(lambda: None))

        # Create product: updates dropdown, then triggers full load
        created_event = create_product_btn.click(
            create_project_from_ui,
            [token, new_product_input],
            [status, product_dropdown, new_product_input, new_product_panel],
        )
        _wire_product_load(created_event)

        # Delete product: deletes product, updates dropdown, hides panel, then triggers full load
        deleted_event = confirm_delete_btn.click(
            delete_product_from_ui,
            [token, product_dropdown, delete_confirm_state],
            [status, product_dropdown],
        ).then(lambda: gr.update(visible=False), outputs=delete_confirm_panel)
        _wire_product_load(deleted_event)

        # Login and auto-login: authenticate, reveal panels, update dropdown, then trigger full load
        login_event = submit.click(login, [username, password], [status, token, login_panel, workspace_panel]).then(
            workspace, token, [workspace_text, login_panel, instructor_panel, team_panel, product_dropdown]
        )
        _wire_product_load(login_event)

        load_event = app.load(auto_login, outputs=[session_notice, token, login_panel, workspace_panel]).then(
            workspace, token, [workspace_text, login_panel, instructor_panel, team_panel, product_dropdown]
        )
        _wire_product_load(load_event)

        def _refresh_backlog_workspace(event):
            event = event.then(
                load_backlog_table_from_ui,
                [token, product_dropdown],
                backlog["table_flat_outputs"] + [backlog["visible_rows_count"]],
            )
            for note_state, note_output in zip(assessment["dimension_note_states"], dimension_note_outputs):
                event = event.then(dimension_notes_from_ui, [token, product_dropdown, note_state], note_output)
            for state, output in zip(safety["checkpoint_states"], safety["note_lists"]):
                event = event.then(learning_notes_ui, [token, product_dropdown, safety["note_section"], state], output)
            event = event.then(learning_notes_ui, [token, product_dropdown, improvement["note_section"]], improvement["notes_list"])
            return (
                event.then(
                    load_placements_from_ui,
                    [token, product_dropdown],
                    priority["placement_outputs"] + [priority["ranking_display"], priority["matrix_fig"]],
                )
                .then(checklist_text, [token, product_dropdown], summary["checklist_display"])
                .then(project_history_from_ui, [token, product_dropdown], history["history"])
            )

        for r in backlog["row_components"]:
            saved_event = r["save_btn"].click(
                save_backlog_row_from_ui,
                [token, product_dropdown, r["dim"], r["assumption"], r["question"], r["hypothesis"], r["note_id"], r["hyp_id"], r["hyp_rev"]],
                [status, r["note_id"], r["hyp_id"], r["hyp_rev"]],
            )
            _refresh_backlog_workspace(saved_event)
            removed_event = r["remove_btn"].click(
                archive_backlog_row_from_ui,
                [token, product_dropdown, r["note_id"], r["hyp_id"]],
                status,
            )
            _refresh_backlog_workspace(removed_event)
            r["cancel_btn"].click(
                load_backlog_table_from_ui, [token, product_dropdown], backlog["table_flat_outputs"] + [backlog["visible_rows_count"]],
            )

        for event in [*assessment["note_events"], *safety["note_events"], improvement["note_event"]]:
            event.then(load_backlog_table_from_ui, [token, product_dropdown], backlog["table_flat_outputs"] + [backlog["visible_rows_count"]])

    return app
