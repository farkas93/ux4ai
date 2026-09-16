"""Minimal authenticated Gradio shell for the Phase 1 foundation."""

from uuid import UUID

import gradio as gr

from .assessment_services import (
    ensure_scale_definitions,
    get_project_estimates,
    save_project_estimates,
)
from .auth import AuthenticationError, RevisionConflict, authenticate, get_authenticated_user
from .baseline_services import published_datasets, select_comparator
from .db import SessionLocal
from .dimensions import DEFAULT_DIMENSIONS
from .hypothesis_services import add_relation, create_hypothesis, create_note, list_notes
from .models import Hypothesis, Role
from .services import (
    create_project,
    get_project,
    list_projects,
    update_main_hypothesis,
    update_project,
    validate_figma_url,
)


def login(username: str, password: str):
    with SessionLocal() as db:
        try:
            token, user = authenticate(db, username, password)
        except AuthenticationError as exc:
            return gr.update(value=str(exc)), None, gr.update(visible=True), gr.update(visible=False)
    # The production FastAPI adapter will set this token as an HttpOnly cookie.
    # Keeping it in State here makes the shell usable while the adapter is wired.
    return gr.update(value=f"Signed in as {user.username}"), token, gr.update(visible=False), gr.update(visible=True)


def workspace(token: str):
    with SessionLocal() as db:
        try:
            user = get_authenticated_user(db, token)
        except AuthenticationError:
            return "Session expired. Please sign in again.", gr.update(visible=True), gr.update(visible=False)
    if user.role == Role.INSTRUCTOR.value:
        return "Instructor area: course progress, teams, and baselines.", gr.update(visible=False), gr.update(visible=True), gr.update(visible=False), gr.update()
    with SessionLocal() as db:
        projects = list_projects(db, user)
    choices = [(project.product_name, str(project.id)) for project in projects]
    return "Select an existing project or create a new draft.", gr.update(visible=False), gr.update(visible=False), gr.update(visible=True), gr.update(choices=choices, value=choices[0][1] if choices else None)


def create_project_from_ui(token: str, product_name: str):
    with SessionLocal() as db:
        try:
            user = get_authenticated_user(db, token)
            project = create_project(db, user, product_name)
            choices = [(item.product_name, str(item.id)) for item in list_projects(db, user)]
        except (AuthenticationError, ValueError) as exc:
            return str(exc), gr.update(), gr.update(), gr.update()
    return "Draft created. Your project brief is ready.", gr.update(choices=choices, value=str(project.id)), gr.update(value=project.product_name), gr.update(value=project.revision)


def load_project_from_ui(token: str, project_id: str | None):
    if not project_id:
        return "", "", "", "", "", "", "", "", "", None, None
    with SessionLocal() as db:
        try:
            user = get_authenticated_user(db, token)
            project = get_project(db, user, UUID(project_id))
            hypothesis = next(iter(project.hypotheses), None)
        except (AuthenticationError, ValueError, LookupError):
            return "Unable to load that project.", "", "", "", "", "", "", "", "", None, None
    return (
        "Project Brief",
        project.product_name,
        project.short_description,
        project.target_user,
        project.job_to_be_done,
        project.current_problem,
        hypothesis.statement if hypothesis else "",
        project.product_type,
        project.figma_url,
        str(project.id),
        project.revision,
    )


def save_project_from_ui(token: str, project_id: str | None, revision: int | None, product_name: str, product_type: str | None, description: str, target_user: str, job: str, problem: str, hypothesis: str, figma_url: str):
    if not project_id or revision is None:
        return "Select a project first.", revision
    with SessionLocal() as db:
        try:
            user = get_authenticated_user(db, token)
            updated_url = validate_figma_url(figma_url)
            project = update_project(db, user, UUID(project_id), revision, product_name=product_name.strip(), product_type=product_type, short_description=description, target_user=target_user, job_to_be_done=job, current_problem=problem, figma_url=updated_url)
            main = next(iter(project.hypotheses), None)
            if main:
                update_main_hypothesis(db, user, project.id, main.revision, hypothesis)
        except (AuthenticationError, RevisionConflict, ValueError) as exc:
            return str(exc), revision
    return "Saved.", project.revision


def load_estimates_from_ui(token: str, project_id: str | None):
    blank = []
    if not project_id:
        return [value for _ in DEFAULT_DIMENSIONS for value in ("unassessed", None, "", None, "", "")]
    with SessionLocal() as db:
        try:
            user = get_authenticated_user(db, token)
            ensure_scale_definitions(db)
            estimates = get_project_estimates(db, user, UUID(project_id))
        except (AuthenticationError, ValueError):
            return [value for _ in DEFAULT_DIMENSIONS for value in ("unassessed", None, "", None, "", "")]
    for estimate in estimates:
        blank.extend([estimate.status, estimate.score, estimate.rationale, estimate.basis, estimate.evidence, estimate.uncertainty])
    return blank


def save_estimates_from_ui(token: str, project_id: str | None, *values):
    if not project_id:
        return "Select a project before saving dimension assessments."
    records = []
    for index, definition in enumerate(DEFAULT_DIMENSIONS):
        offset = index * 6
        records.append({
            "dimension_key": definition["key"],
            "status": values[offset],
            "score": values[offset + 1],
            "rationale": values[offset + 2],
            "basis": values[offset + 3],
            "evidence": values[offset + 4],
            "uncertainty": values[offset + 5],
        })
    with SessionLocal() as db:
        try:
            user = get_authenticated_user(db, token)
            ensure_scale_definitions(db)
            save_project_estimates(db, user, UUID(project_id), records)
        except (AuthenticationError, RevisionConflict, ValueError) as exc:
            return str(exc)
    return "Dimension assessments saved."


def load_comparator_choices():
    with SessionLocal() as db:
        return gr.update(choices=[(name, str(dataset_id)) for name, dataset_id in published_datasets(db)])


def save_comparator_from_ui(token: str, project_id: str | None, dataset_id: str | None, purpose: str, scope: str):
    if not project_id or not dataset_id:
        return "Select a project and comparator first."
    with SessionLocal() as db:
        try:
            user = get_authenticated_user(db, token)
            select_comparator(db, user, UUID(project_id), UUID(dataset_id), purpose, scope)
        except (AuthenticationError, ValueError) as exc:
            return str(exc)
    return "Comparator selection saved as a snapshot. Previous snapshots remain unchanged."


def _hypotheses(db, project_id: str) -> list[Hypothesis]:
    return list(db.query(Hypothesis).filter(Hypothesis.project_id == UUID(project_id)).order_by(Hypothesis.kind, Hypothesis.created_at))


def _hypothesis_text(items: list[Hypothesis]) -> str:
    return "\n".join(f"[{item.kind}] {item.statement} | impact: {item.impact_if_wrong} | evidence: {item.evidence_strength} | status: {item.workflow_status}" for item in items) or "No hypotheses yet."


def _notes_text(items) -> str:
    return "\n".join(f"[{item.note_type}] {item.text}" for item in items) or "No notes yet."


def load_backlog_from_ui(token: str, project_id: str | None):
    if not project_id:
        return "No notes yet.", "No hypotheses yet.", gr.update(choices=[]), gr.update(choices=[]), gr.update(choices=[])
    with SessionLocal() as db:
        try:
            user = get_authenticated_user(db, token)
            notes = list_notes(db, user, UUID(project_id))
            hypotheses = _hypotheses(db, project_id)
        except AuthenticationError:
            return "Session expired.", "Session expired.", gr.update(choices=[]), gr.update(choices=[]), gr.update(choices=[])
    choices = [(item.statement[:80], str(item.id)) for item in hypotheses]
    note_choices = [(item.text[:80], str(item.id)) for item in notes]
    return _notes_text(notes), _hypothesis_text(hypotheses), gr.update(choices=note_choices), gr.update(choices=choices), gr.update(choices=choices)


def save_note_from_ui(token: str, project_id: str | None, note_type: str, text: str, dimensions: list[str]):
    if not project_id:
        return "Select a project first.", "No notes yet."
    dimension_keys = [definition["key"] for definition in DEFAULT_DIMENSIONS if definition["title"] in (dimensions or [])]
    with SessionLocal() as db:
        try:
            user = get_authenticated_user(db, token)
            create_note(db, user, UUID(project_id), note_type, text, dimension_keys)
            notes = list_notes(db, user, UUID(project_id))
        except (AuthenticationError, ValueError) as exc:
            return str(exc), ""
    return "Note saved.", _notes_text(notes)


def save_hypothesis_from_ui(token: str, project_id: str | None, statement: str, value_link: str, impact: str, evidence: str, evidence_rationale: str, note_id: str | None):
    if not project_id:
        return "Select a project first.", "", gr.update(choices=[])
    with SessionLocal() as db:
        try:
            user = get_authenticated_user(db, token)
            hypothesis = create_hypothesis(db, user, UUID(project_id), statement, value_link=value_link, note_id=UUID(note_id) if note_id else None)
            hypothesis.impact_if_wrong = impact
            hypothesis.evidence_strength = evidence
            hypothesis.evidence_rationale = evidence_rationale
            db.commit()
            hypotheses = _hypotheses(db, project_id)
        except (AuthenticationError, ValueError) as exc:
            return str(exc), "", gr.update(choices=[])
    choices = [(item.statement[:80], str(item.id)) for item in hypotheses]
    return "Supporting hypothesis saved.", _hypothesis_text(hypotheses), gr.update(choices=choices)


def save_relation_from_ui(token: str, project_id: str | None, relation_type: str, source_id: str | None, target_id: str | None):
    if not project_id or not source_id or not target_id:
        return "Select a project and two hypotheses."
    with SessionLocal() as db:
        try:
            user = get_authenticated_user(db, token)
            add_relation(db, user, UUID(project_id), relation_type, UUID(source_id), UUID(target_id))
        except (AuthenticationError, ValueError) as exc:
            return str(exc)
    return "Hypothesis relationship saved."


def build_app():
    with gr.Blocks(title="AIPM Toolkit") as app:
        token = gr.State(None)
        status = gr.Markdown()
        with gr.Column(visible=True) as login_panel:
            username = gr.Textbox(label="Team alias or instructor username")
            password = gr.Textbox(label="Password", type="password")
            submit = gr.Button("Sign in", variant="primary")
        with gr.Column(visible=False) as workspace_panel:
            workspace_text = gr.Markdown()
        with gr.Column(visible=False) as instructor_panel:
            gr.Markdown("## Instructor area\nCourse progress, teams, baseline imports, and catalog administration will appear here.")
        with gr.Column(visible=False) as team_panel:
            gr.Markdown("## Project Brief")
            with gr.Row():
                project_dropdown = gr.Dropdown(label="Your projects", choices=[], interactive=True)
                new_project_name = gr.Textbox(label="New product name", placeholder="Only the product name is required")
                create_button = gr.Button("Create draft")
            project_title = gr.Markdown()
            with gr.Row():
                product_name = gr.Textbox(label="Product name")
                product_type = gr.Dropdown(label="AI product type", choices=["Feature", "Plugin", "Native", "Mixed/Undecided"], value=None)
            description = gr.Textbox(label="Short description", lines=3)
            target_user = gr.Textbox(label="Target user")
            job = gr.Textbox(label="Job to be done", lines=3)
            problem = gr.Textbox(label="Current problem or workflow", lines=3)
            hypothesis = gr.Textbox(label="Main value hypothesis", lines=4, placeholder="If we help [user] accomplish [job] through [capability], we expect [outcome] to improve while maintaining [constraint].")
            figma_url = gr.Textbox(label="Figma prototype URL (optional)")
            save_button = gr.Button("Save brief", variant="primary")
            project_id = gr.State(None)
            project_revision = gr.State(None)
            gr.Markdown("## Dimension Explorer")
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
            save_assessments_button = gr.Button("Save dimension assessments", variant="primary")
            gr.Markdown("## Comparator")
            gr.Markdown("Historical profiles are classroom assessments, not current product ratings or rankings.")
            comparator = gr.Dropdown(label="Historical comparator", choices=[])
            comparator_purpose = gr.Radio(label="Comparison purpose", choices=[("Task comparator", "task_comparator"), ("Design contrast", "design_contrast")], value="task_comparator")
            comparator_scope = gr.Textbox(label="Comparison scope or explanation", lines=2)
            save_comparator_button = gr.Button("Save comparator selection")
            gr.Markdown("## Notes")
            note_type = gr.Dropdown(label="Note type", choices=[("Observation", "observation"), ("Assumption", "assumption"), ("Question", "question"), ("Design decision", "design_decision")], value="observation")
            note_text = gr.Textbox(label="Note", lines=3)
            note_dimensions = gr.CheckboxGroup(label="Linked dimensions", choices=[definition["title"] for definition in DEFAULT_DIMENSIONS])
            save_note_button = gr.Button("Save note")
            notes_display = gr.Textbox(label="Saved notes", interactive=False, lines=5)
            gr.Markdown("## Hypothesis Backlog")
            hypothesis_statement = gr.Textbox(label="Supporting hypothesis statement", lines=3)
            hypothesis_value_link = gr.Textbox(label="Why it matters / value link", lines=2)
            hypothesis_impact = gr.Dropdown(label="Impact if wrong", choices=["unknown", "low", "medium", "high"], value="unknown")
            hypothesis_evidence = gr.Dropdown(label="Evidence strength", choices=["unknown", "none", "limited", "moderate", "strong"], value="unknown")
            hypothesis_evidence_rationale = gr.Textbox(label="Evidence rationale", lines=2)
            hypothesis_note = gr.Dropdown(label="Originating note (optional)", choices=[])
            save_hypothesis_button = gr.Button("Create supporting hypothesis")
            hypotheses_display = gr.Textbox(label="Hypothesis backlog", interactive=False, lines=7)
            gr.Markdown("### Link hypotheses")
            relation_type = gr.Dropdown(label="Relationship", choices=[("Contributes to", "contributes_to"), ("Depends on", "depends_on"), ("Alternative to", "alternative_to"), ("In tension with", "in_tension_with")], value="contributes_to")
            relation_source = gr.Dropdown(label="From hypothesis", choices=[])
            relation_target = gr.Dropdown(label="To hypothesis", choices=[])
            save_relation_button = gr.Button("Save relationship")
        submit.click(login, [username, password], [status, token, login_panel, workspace_panel]).then(workspace, token, [workspace_text, login_panel, instructor_panel, team_panel, project_dropdown])
        create_button.click(create_project_from_ui, [token, new_project_name], [status, project_dropdown, product_name, project_revision])
        project_dropdown.change(load_project_from_ui, [token, project_dropdown], [project_title, product_name, description, target_user, job, problem, hypothesis, product_type, figma_url, project_id, project_revision]).then(load_estimates_from_ui, [token, project_id], assessment_components).then(load_comparator_choices, outputs=comparator).then(load_backlog_from_ui, [token, project_id], [notes_display, hypotheses_display, hypothesis_note, relation_source, relation_target])
        save_button.click(save_project_from_ui, [token, project_id, project_revision, product_name, product_type, description, target_user, job, problem, hypothesis, figma_url], [status, project_revision])
        save_assessments_button.click(save_estimates_from_ui, [token, project_id, *assessment_components], status)
        save_comparator_button.click(save_comparator_from_ui, [token, project_id, comparator, comparator_purpose, comparator_scope], status)
        save_note_button.click(save_note_from_ui, [token, project_id, note_type, note_text, note_dimensions], [status, notes_display])
        save_hypothesis_button.click(save_hypothesis_from_ui, [token, project_id, hypothesis_statement, hypothesis_value_link, hypothesis_impact, hypothesis_evidence, hypothesis_evidence_rationale, hypothesis_note], [status, hypotheses_display, relation_source]).then(load_backlog_from_ui, [token, project_id], [notes_display, hypotheses_display, hypothesis_note, relation_source, relation_target])
        save_relation_button.click(save_relation_from_ui, [token, project_id, relation_type, relation_source, relation_target], status)
    return app


app = build_app()


if __name__ == "__main__":
    app.launch()
