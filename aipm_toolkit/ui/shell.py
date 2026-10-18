"""App shell: header bar with product switcher, language, and real tabs."""

import gradio as gr
from sqlalchemy.exc import SQLAlchemyError

from ..auth import AuthenticationError, AuthorizationError
from ..dimensions import DEFAULT_DIMENSIONS
from ..i18n import load_catalog
from . import (
    tabs_assessment,
    tabs_backlog,
    tabs_improvement,
    tabs_priority,
    tabs_setup,
    tabs_summary,
)
from .callbacks import (
    archive_backlog_row_from_ui,
    auto_login,
    checklist_text,
    create_project_from_ui,
    decide_project_switch,
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
    project_switch_prompt_text,
    provision_team_from_ui,
    publish_upload_from_ui,
    save_backlog_row_from_ui,
    save_pending_project_edits,
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
    // Use the native drawer's button so its state and accessibility stay in sync.
    const viewport = window.matchMedia('(max-width: 1023px)');
    const syncDrawer = () => {
        const drawer = document.querySelector('.gradio-container .sidebar');
        const handle = drawer?.querySelector('button.toggle-button');
        if (!drawer || !handle) return false;
        const shouldOpen = !viewport.matches;
        if (drawer.classList.contains('open') !== shouldOpen) handle.click();
        return true;
    };
    // Sidebar applies its initial open state after mounting.
    setTimeout(() => {
        if (syncDrawer()) return;
        const drawerObserver = new MutationObserver(() => {
            if (syncDrawer()) drawerObserver.disconnect();
        });
        drawerObserver.observe(document.body, {childList: true, subtree: true});
    }, 500);
    viewport.addEventListener('change', syncDrawer);
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
        active_project_id = gr.State(None)
        pending_project_id = gr.State(None)
        project_switch_action = gr.State("none")
        project_switch_busy = gr.State(False)
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
                new_product_btn = gr.Button("+ New", size="sm", variant="secondary", elem_id="toolkit-new-product")

            with gr.Row(visible=False, variant="panel") as new_product_panel:
                new_product_input = gr.Textbox(label="New product name", placeholder="e.g. HealthAI Assistant", scale=3)
                create_product_btn = gr.Button("Create", variant="primary", scale=1)
                cancel_product_btn = gr.Button("Cancel", variant="secondary", scale=1)

            with gr.Row(visible=False, variant="panel") as delete_confirm_panel:
                gr.Markdown("⚠️ **Are you sure you want to permanently delete the selected product and all its data?**")
                confirm_delete_btn = gr.Button("Yes, delete permanently", variant="stop", scale=1)
                cancel_delete_btn = gr.Button("Cancel", variant="secondary", scale=1)

            with gr.Column(visible=False, elem_id="toolkit-project-switch-backdrop") as project_switch_dialog:  # noqa: SIM117
                with gr.Column(elem_id="toolkit-project-switch-card"):
                    gr.Markdown("### Switch product?")
                    project_switch_message = gr.Markdown(elem_id="toolkit-project-switch-message")
                    with gr.Row(elem_id="toolkit-project-switch-actions"):
                        save_switch_button = gr.Button("Save & Switch", variant="primary")
                        discard_switch_button = gr.Button("Discard & Switch", variant="stop")
                        cancel_switch_button = gr.Button("Cancel")

            section_names = ["Value Hypothesis", "Explore Dimensions", "Explore Backlog", "Explore Priority", "Build Self-Improvement", "Summary & Export"]
            with gr.Row(elem_id="toolkit-workspace"):
                with gr.Sidebar(label="Workspace navigation", open=True, width=240, elem_id="toolkit-sidebar") as sidebar:
                    desktop_section = gr.Radio(label="Workspace", choices=section_names, value="Value Hypothesis", container=False, elem_id="toolkit-desktop-section")
                    language_selector = gr.Dropdown(label="Language / Sprache", choices=LANGUAGE_CHOICES, value="en", container=False, elem_id="toolkit-language")
                    gr.HTML('<a href="/auth/logout">Sign out</a>', elem_classes=["toolkit-account"])
                    with gr.Accordion("Product administration", open=False, elem_id="toolkit-product-admin"):
                        delete_product_btn = gr.Button("Delete product", variant="stop", size="sm")
                with gr.Column(scale=1, min_width=0, elem_id="toolkit-main"):
                    current_section = gr.Markdown("Value Hypothesis", elem_id="toolkit-current-section")
                    setup = tabs_setup.build_setup_tab(token, active_project_id, project_revision, status, project_switch_busy)
                    assessment = tabs_assessment.build_assessment_tab(token, active_project_id, status)
                    backlog = tabs_backlog.build_backlog_tab(token, active_project_id, status)
                    priority = tabs_priority.build_priority_tab(token, active_project_id, status)
                    improvement = tabs_improvement.build_improvement_tab(token, active_project_id, status)
                    summary = tabs_summary.build_summary_tab(token, active_project_id, status, product_dropdown)
            pages = [setup, assessment, backlog, priority, improvement, summary]

            def select_section(name):
                return [gr.update(visible=label == name) for label in section_names]

            desktop_section.change(lambda name: name, desktop_section, current_section)
            small_screen = gr.State(False)
            desktop_section.input(select_section, desktop_section, [page["tab"] for page in pages]).then(
                lambda small: gr.update(open=False) if small else gr.update(),
                small_screen,
                sidebar,
                js="() => [window.matchMedia('(max-width: 1023px)').matches]",
            )

        instructor_panel = _build_instructor_panel(token, status, product_dropdown)
        dimension_note_outputs = assessment["dimension_note_lists"]
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

        row_dirty_states = [row["dirty"] for row in backlog["row_components"]]
        dirty_states = [
            setup["brief_dirty"],
            assessment["assessment_dirty"],
            *[draft["dirty"] for draft in assessment["note_drafts"]],
            improvement["dirty"],
            improvement["note_draft"]["dirty"],
            *priority["dirty_states"],
            *row_dirty_states,
        ]

        def route_project_selection(auth_token, requested_id, active_id, switching, request: gr.Request, *dirty_values):
            if switching or requested_id == active_id:
                return (gr.update(),) * 7
            action = decide_project_switch(active_id, requested_id, dirty_values)
            if action == "none":
                return active_id, None, "none", gr.update(visible=False), "", gr.update(value=active_id, interactive=True), False
            if action == "confirm":
                prompt = project_switch_prompt_text(auth_token, active_id, requested_id, request=request)
                return active_id, requested_id, "none", gr.update(visible=True), prompt, gr.update(value=active_id, interactive=False), True
            # Keep editors associated with the old project until every target
            # value has loaded. The picker is a requested target, not identity.
            return active_id, requested_id, "load", gr.update(visible=False), "", gr.update(value=active_id, interactive=False), True

        setup_load_outputs = [
            setup["description"], setup["target_user"], setup["job"], setup["problem"],
            setup["hypothesis"], setup["product_type"], setup["figma_url"], project_revision,
        ]
        estimate_load_outputs = assessment["assessment_components"] + [assessment["assessment_revisions"]]
        backlog_load_outputs = backlog["table_flat_outputs"] + [backlog["visible_rows_count"]]
        priority_load_outputs = priority["placement_outputs"] + [priority["ranking_display"], priority["matrix_fig"]]
        improvement_load_outputs = [improvement["loop_id"], *improvement["fields"]]
        snapshot_outputs = [
            *setup_load_outputs, *estimate_load_outputs, *dimension_note_outputs,
            *backlog_load_outputs, *priority_load_outputs, *improvement_load_outputs,
            improvement["notes_list"], assessment["comparator"], assessment["frozen_state"],
            assessment["comparison_table"], assessment["live_chart"], assessment["unsaved_note"],
            summary["checklist_display"], summary["summary_preview"],
            summary["pdf_download"], summary["json_download"], summary["markdown_download"],
            *dirty_states, *[draft["text"] for draft in assessment["note_drafts"]],
            improvement["note_draft"]["text"],
            active_project_id, pending_project_id, project_switch_action, project_switch_busy,
            product_dropdown, status,
        ]

        def load_project_snapshot(action, auth_token, active_id, target_id, request: gr.Request):
            if action != "load":
                return gr.skip()
            target_id = target_id if target_id is not None else active_id
            try:
                # Fetch all project-owned editor values before returning any UI
                # update, so identity and content change in the same response.
                values = {}

                def put(outputs, data):
                    values.update(zip(outputs, data, strict=True))

                setup_values = load_project_from_ui(auth_token, target_id, request=request)
                if target_id and setup_values[-1] is None:
                    raise ValueError("The selected product could not be loaded. Please sign in again and retry.")
                put(setup_load_outputs, setup_values)
                estimates = load_estimates_from_ui(auth_token, target_id, request=request)
                put(estimate_load_outputs, estimates)
                for definition, output in zip(DEFAULT_DIMENSIONS, dimension_note_outputs, strict=True):
                    values[output] = dimension_notes_from_ui(auth_token, target_id, definition["key"], request=request)
                put(backlog_load_outputs, load_backlog_table_from_ui(auth_token, target_id, request=request))
                put(priority_load_outputs, load_placements_from_ui(auth_token, target_id, request=request))
                put(improvement_load_outputs, load_primary_loop_ui(auth_token, target_id, request=request))
                values[improvement["notes_list"]] = learning_notes_ui(auth_token, target_id, "self_improvement", request=request)
                auxiliary_errors = []
                try:
                    comparator = load_comparator_choices()
                    comparator["value"] = None
                except (SQLAlchemyError, ValueError) as exc:
                    comparator = gr.update(choices=[], value=None)
                    auxiliary_errors.append(f"Historical comparison could not be loaded: {exc}")
                values[assessment["comparator"]] = comparator
                values[assessment["frozen_state"]] = {}
                values[assessment["comparison_table"]] = "Select a comparator to see the comparison table."
                values[assessment["live_chart"]] = live_profile_from_ui({}, *estimates[:-1:2])
                values[assessment["unsaved_note"]] = ""
                for name, output, load in (
                    ("Workshop checklist", summary["checklist_display"], checklist_text),
                    ("Summary", summary["summary_preview"], summary_preview_from_ui),
                ):
                    try:
                        values[output] = load(auth_token, target_id, request=request)
                    except (AuthenticationError, AuthorizationError, SQLAlchemyError, ValueError, LookupError) as exc:
                        message = f"{name} could not be loaded: {exc}"
                        values[output] = message
                        auxiliary_errors.append(message)
                for output in (summary["pdf_download"], summary["json_download"], summary["markdown_download"]):
                    values[output] = None
                values.update(dict.fromkeys(dirty_states, False))
                for draft in assessment["note_drafts"]:
                    values[draft["text"]] = ""
                values[improvement["note_draft"]["text"]] = ""
                values.update({
                    active_project_id: target_id,
                    pending_project_id: None,
                    project_switch_action: "none",
                    project_switch_busy: False,
                    product_dropdown: gr.update(value=target_id, interactive=True),
                    status: " ".join(auxiliary_errors) if auxiliary_errors else gr.skip(),
                })
                return values
            except (AuthenticationError, AuthorizationError, SQLAlchemyError, ValueError, LookupError) as exc:
                # Retain the previous snapshot and make failures visible rather
                # than leaving some pages empty and the selector locked.
                return {
                    status: f"Product load failed: {exc}",
                    pending_project_id: None,
                    project_switch_action: "none",
                    project_switch_busy: False,
                    product_dropdown: gr.update(value=active_id, interactive=True),
                }

        def _wire_project_load(trigger):
            return trigger.then(
                load_project_snapshot,
                [project_switch_action, token, active_project_id, pending_project_id],
                snapshot_outputs,
                concurrency_id="project-data-write",
                concurrency_limit=1,
            )

        switch_event = product_dropdown.input(
            route_project_selection,
            [token, product_dropdown, active_project_id, project_switch_busy, *dirty_states],
            [active_project_id, pending_project_id, project_switch_action, project_switch_dialog, project_switch_message, product_dropdown, project_switch_busy],
            concurrency_id="project-data-write",
            concurrency_limit=1,
        )
        _wire_project_load(switch_event)

        save_switch_ok = gr.State(False)
        save_switch_inputs = [
            token,
            active_project_id,
            setup["brief_dirty"],
            project_revision,
            setup["product_type"],
            setup["description"],
            setup["target_user"],
            setup["job"],
            setup["problem"],
            setup["hypothesis"],
            setup["figma_url"],
            assessment["assessment_dirty"],
            assessment["assessment_revisions"],
            *assessment["assessment_components"],
            improvement["dirty"],
            improvement["loop_id"],
            *improvement["fields"],
        ]
        for slot in priority["slot_components"]:
            save_switch_inputs.extend([slot["dirty"], slot["id"], slot["revision"], slot["risk"], slot["evidence"]])
        for row in backlog["row_components"]:
            save_switch_inputs.extend([
                row["dirty"],
                row["dim"],
                row["assumption"],
                row["question"],
                row["hypothesis"],
                row["note_id"],
                row["hyp_id"],
                row["hyp_rev"],
            ])
        for draft in assessment["note_drafts"]:
            save_switch_inputs.extend([draft["dirty"], draft["key"], draft["type"], draft["text"], draft["list"]])
        save_switch_inputs.extend([
            improvement["note_draft"]["dirty"],
            improvement["note_draft"]["type"],
            improvement["note_draft"]["text"],
            improvement["note_draft"]["list"],
        ])

        save_switch_outputs = [
            project_switch_message,
            project_revision,
            setup["brief_dirty"],
            assessment["assessment_revisions"],
            assessment["assessment_dirty"],
            improvement["loop_id"],
            improvement["revision"],
            improvement["dirty"],
        ]
        for slot in priority["slot_components"]:
            save_switch_outputs.extend([slot["dirty"], slot["revision"]])
        for row in backlog["row_components"]:
            save_switch_outputs.extend([row["dirty"], row["note_id"], row["hyp_id"], row["hyp_rev"]])
        for draft in assessment["note_drafts"]:
            save_switch_outputs.extend([draft["dirty"], draft["text"], draft["list"]])
        save_switch_outputs.extend([
            improvement["note_draft"]["dirty"],
            improvement["note_draft"]["text"],
            improvement["note_draft"]["list"],
        ])
        save_switch_outputs.append(save_switch_ok)

        def _finish_confirmed_switch(saved, active_id, target_id):
            if saved and target_id:
                return active_id, target_id, "load", gr.update(visible=False), "", gr.update(value=active_id, interactive=False), True
            return active_id, target_id, "none", gr.update(visible=True), gr.update(), gr.update(interactive=False), True

        save_switch_event = save_switch_button.click(
            save_pending_project_edits,
            save_switch_inputs,
            save_switch_outputs,
            concurrency_id="project-data-write",
            concurrency_limit=1,
        )
        saved_switch_event = save_switch_event.then(
            _finish_confirmed_switch,
            [save_switch_ok, active_project_id, pending_project_id],
            [active_project_id, pending_project_id, project_switch_action, project_switch_dialog, project_switch_message, product_dropdown, project_switch_busy],
        )
        _wire_project_load(saved_switch_event)

        def _discard_and_switch(active_id, target_id):
            if target_id:
                return active_id, target_id, "load", gr.update(visible=False), "", gr.update(value=active_id, interactive=False), True
            return active_id, None, "none", gr.update(visible=False), "", gr.update(value=active_id, interactive=True), False

        discard_switch_event = discard_switch_button.click(
            _discard_and_switch,
            [active_project_id, pending_project_id],
            [active_project_id, pending_project_id, project_switch_action, project_switch_dialog, project_switch_message, product_dropdown, project_switch_busy],
            concurrency_id="project-data-write",
            concurrency_limit=1,
        )
        _wire_project_load(discard_switch_event)

        def _cancel_project_switch(active_id):
            return None, "none", False, gr.update(visible=False), "", gr.update(value=active_id, interactive=True)

        cancel_switch_button.click(
            _cancel_project_switch,
            active_project_id,
            [pending_project_id, project_switch_action, project_switch_busy, project_switch_dialog, project_switch_message, product_dropdown],
            concurrency_id="project-data-write",
            concurrency_limit=1,
        )

        # Create product: updates dropdown, then triggers full load
        created_event = create_product_btn.click(
            create_project_from_ui,
            [token, new_product_input],
            [status, product_dropdown, new_product_input, new_product_panel],
            concurrency_id="project-data-write",
            concurrency_limit=1,
        )
        created_switch_event = created_event.then(
            route_project_selection,
            [token, product_dropdown, active_project_id, project_switch_busy, *dirty_states],
            [active_project_id, pending_project_id, project_switch_action, project_switch_dialog, project_switch_message, product_dropdown, project_switch_busy],
        )
        _wire_project_load(created_switch_event)
        # Delete product: deletes product, updates dropdown, hides panel, then triggers full load
        deleted_event = confirm_delete_btn.click(
            delete_product_from_ui,
            [token, active_project_id, delete_confirm_state],
            [status, product_dropdown],
            concurrency_id="project-data-write",
            concurrency_limit=1,
        ).then(lambda: gr.update(visible=False), outputs=delete_confirm_panel)
        def _route_after_delete(_auth_token, selected_id):
            return selected_id, None, "load", gr.update(visible=False), "", gr.update(value=selected_id, interactive=False), True

        deleted_switch_event = deleted_event.then(
            _route_after_delete,
            [token, product_dropdown],
            [active_project_id, pending_project_id, project_switch_action, project_switch_dialog, project_switch_message, product_dropdown, project_switch_busy],
        )
        _wire_project_load(deleted_switch_event)
        summary_deleted_switch = summary["delete_event"].then(
            _route_after_delete,
            [token, product_dropdown],
            [active_project_id, pending_project_id, project_switch_action, project_switch_dialog, project_switch_message, product_dropdown, project_switch_busy],
        )
        _wire_project_load(summary_deleted_switch)
        # Login and auto-login: authenticate, reveal panels, update dropdown, then trigger full load
        login_event = submit.click(login, [username, password], [status, token, login_panel, workspace_panel]).then(
            workspace, token, [workspace_text, login_panel, instructor_panel, team_panel, product_dropdown, active_project_id, project_switch_action, project_switch_busy]
        )
        _wire_project_load(login_event)

        load_event = app.load(auto_login, outputs=[session_notice, token, login_panel, workspace_panel]).then(
            workspace, token, [workspace_text, login_panel, instructor_panel, team_panel, product_dropdown, active_project_id, project_switch_action, project_switch_busy]
        )
        _wire_project_load(load_event)

        def _refresh_backlog_workspace(event):
            event = event.then(
                load_backlog_table_from_ui,
                [token, active_project_id],
                backlog["table_flat_outputs"] + [backlog["visible_rows_count"]],
            )
            for note_state, note_output in zip(assessment["dimension_note_states"], dimension_note_outputs):
                event = event.then(dimension_notes_from_ui, [token, active_project_id, note_state], note_output)
            event = event.then(learning_notes_ui, [token, active_project_id, improvement["note_section"]], improvement["notes_list"])
            return (
                event.then(
                    load_placements_from_ui,
                    [token, active_project_id],
                    priority["placement_outputs"] + [priority["ranking_display"], priority["matrix_fig"]],
                )
                .then(checklist_text, [token, active_project_id], summary["checklist_display"])
            )

        for r in backlog["row_components"]:
            saved_event = r["save_btn"].click(
                save_backlog_row_from_ui,
                [token, active_project_id, r["dim"], r["assumption"], r["question"], r["hypothesis"], r["note_id"], r["hyp_id"], r["hyp_rev"]],
                [status, r["note_id"], r["hyp_id"], r["hyp_rev"]],
                concurrency_id="project-data-write",
                concurrency_limit=1,
            )
            _refresh_backlog_workspace(saved_event)
            saved_event.then(lambda message: not message.startswith("Row saved:"), status, r["dirty"])
            removed_event = r["remove_btn"].click(
                archive_backlog_row_from_ui,
                [token, active_project_id, r["note_id"], r["hyp_id"]],
                status,
                concurrency_id="project-data-write",
                concurrency_limit=1,
            )
            _refresh_backlog_workspace(removed_event)
            removed_event.then(lambda: False, outputs=r["dirty"])
            r["cancel_btn"].click(
                load_backlog_table_from_ui, [token, active_project_id], backlog["table_flat_outputs"] + [backlog["visible_rows_count"]],
            )
            r["cancel_btn"].click(lambda: False, outputs=r["dirty"])

        for event in [*assessment["note_events"], improvement["note_event"]]:
            event.then(load_backlog_table_from_ui, [token, active_project_id], backlog["table_flat_outputs"] + [backlog["visible_rows_count"]])

    return app
