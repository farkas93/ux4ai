"""Minimal authenticated Gradio shell for the Phase 1 foundation."""

from uuid import UUID

import gradio as gr
import plotly.graph_objects as go

from .assessment_services import (
    ensure_scale_definitions,
    get_project_estimates,
    save_project_estimates,
)
from .auth import (
    AuthenticationError,
    AuthorizationError,
    RevisionConflict,
    authenticate,
    get_authenticated_user,
)
from .baseline_services import published_datasets, select_comparator
from .comparison_services import comparator_name, comparison_rows
from .db import SessionLocal
from .dimensions import DEFAULT_DIMENSIONS
from .experiment_services import (
    completion_checklist,
    create_experiment,
    list_experiments,
    priority_guidance,
    save_reflection,
    update_experiment,
)
from .export_services import write_export_files
from .hypothesis_services import (
    add_relation,
    create_hypothesis,
    create_note,
    list_notes,
    update_hypothesis,
    update_note,
)
from .i18n import load_catalog
from .instructor_services import (
    course_overview,
    import_baselines_as_instructor,
    provision_team_account,
)
from .models import Experiment, Hypothesis, HypothesisDimension, Note, Role
from .retention_services import delete_project_as_instructor, update_course_retention
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


def _resolve_token(token: str | None, request: gr.Request | None) -> str | None:
    if request:
        cookies = getattr(getattr(request, "request", None), "cookies", {})
        return cookies.get("aipm_session") or token
    return token


def auto_login(request: gr.Request):
    cookies = getattr(getattr(request, "request", None), "cookies", {}) if request else {}
    raw_token = cookies.get("aipm_session")
    if not raw_token:
        return "Please sign in.", None, gr.update(visible=True), gr.update(visible=False)
    with SessionLocal() as db:
        try:
            user = get_authenticated_user(db, raw_token)
        except AuthenticationError:
            return "Session expired. Please sign in again.", None, gr.update(visible=True), gr.update(visible=False)
    return f"Signed in as {user.username}", None, gr.update(visible=False), gr.update(visible=True)


def workspace(token: str | None, request: gr.Request | None = None):
    token = _resolve_token(token, request)
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


def create_project_from_ui(token: str, product_name: str, request: gr.Request | None = None):
    token = _resolve_token(token, request)
    with SessionLocal() as db:
        try:
            user = get_authenticated_user(db, token)
            project = create_project(db, user, product_name)
            choices = [(item.product_name, str(item.id)) for item in list_projects(db, user)]
        except (AuthenticationError, ValueError) as exc:
            return str(exc), gr.update(), gr.update(), gr.update()
    return "Draft created. Your project brief is ready.", gr.update(choices=choices, value=str(project.id)), gr.update(value=project.product_name), gr.update(value=project.revision)


def load_project_from_ui(token: str, project_id: str | None, request: gr.Request | None = None):
    token = _resolve_token(token, request)
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


def save_project_from_ui(token: str, project_id: str | None, revision: int | None, product_name: str, product_type: str | None, description: str, target_user: str, job: str, problem: str, hypothesis: str, figma_url: str, request: gr.Request | None = None):
    token = _resolve_token(token, request)
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


def save_project_action(token: str, project_id: str | None, revision: int | None, product_name: str, product_type: str | None, description: str, target_user: str, job: str, problem: str, hypothesis: str, figma_url: str, request: gr.Request | None = None):
    token = _resolve_token(token, request)
    status, new_revision = save_project_from_ui(token, project_id, revision, product_name, product_type, description, target_user, job, problem, hypothesis, figma_url)
    return status, new_revision, not status.startswith("Saved")


def autosave_project_from_ui(token: str, project_id: str | None, revision: int | None, dirty: bool, product_name: str, product_type: str | None, description: str, target_user: str, job: str, problem: str, hypothesis: str, figma_url: str, request: gr.Request | None = None):
    token = _resolve_token(token, request)
    if not dirty:
        return gr.update(), revision, dirty
    status, new_revision = save_project_from_ui(token, project_id, revision, product_name, product_type, description, target_user, job, problem, hypothesis, figma_url)
    if status.startswith("Saved"):
        return "Saved automatically.", new_revision, False
    return f"Save failed: {status}", new_revision, True


def load_estimates_from_ui(token: str, project_id: str | None, request: gr.Request | None = None):
    token = _resolve_token(token, request)
    blank = []
    if not project_id:
        return [value for _ in DEFAULT_DIMENSIONS for value in ("unassessed", None, "", None, "", "")], []
    with SessionLocal() as db:
        try:
            user = get_authenticated_user(db, token)
            ensure_scale_definitions(db)
            estimates = get_project_estimates(db, user, UUID(project_id))
        except (AuthenticationError, ValueError):
            return [value for _ in DEFAULT_DIMENSIONS for value in ("unassessed", None, "", None, "", "")], []
    revisions = []
    for estimate in estimates:
        blank.extend([estimate.status, estimate.score, estimate.rationale, estimate.basis, estimate.evidence, estimate.uncertainty])
        revisions.append(estimate.revision)
    return blank, revisions


def save_estimates_from_ui(token: str, project_id: str | None, revisions: list[int] | None, *values, request: gr.Request | None = None):
    token = _resolve_token(token, request)
    if not project_id:
        return "Select a project before saving dimension assessments.", revisions or []
    revisions = revisions or [None] * len(DEFAULT_DIMENSIONS)
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
            "revision": revisions[index],
        })
    with SessionLocal() as db:
        try:
            user = get_authenticated_user(db, token)
            ensure_scale_definitions(db)
            save_project_estimates(db, user, UUID(project_id), records)
            saved = get_project_estimates(db, user, UUID(project_id))
        except (AuthenticationError, RevisionConflict, ValueError) as exc:
            return str(exc), revisions
    return "Dimension assessments saved.", [estimate.revision for estimate in saved]


def save_assessments_action(token: str, project_id: str | None, revisions: list[int] | None, *values, request: gr.Request | None = None):
    token = _resolve_token(token, request)
    status, new_revisions = save_estimates_from_ui(token, project_id, revisions, *values)
    return status, new_revisions, not status.endswith("saved.")


def autosave_assessments_from_ui(token: str, project_id: str | None, revisions: list[int] | None, dirty: bool, *values, request: gr.Request | None = None):
    token = _resolve_token(token, request)
    if not dirty:
        return gr.update(), revisions or [], dirty
    status, new_revisions = save_estimates_from_ui(token, project_id, revisions, *values)
    if status.endswith("saved."):
        return "Dimension assessments saved automatically.", new_revisions, False
    return f"Save failed: {status}", new_revisions, True


def load_comparator_choices():
    with SessionLocal() as db:
        return gr.update(choices=[(name, str(dataset_id)) for name, dataset_id in published_datasets(db)])


def save_comparator_from_ui(token: str, project_id: str | None, dataset_id: str | None, purpose: str, scope: str, request: gr.Request | None = None):
    token = _resolve_token(token, request)
    if not project_id or not dataset_id:
        return "Select a project and comparator first.", None
    with SessionLocal() as db:
        try:
            user = get_authenticated_user(db, token)
            snapshot = select_comparator(db, user, UUID(project_id), UUID(dataset_id), purpose, scope)
        except (AuthenticationError, ValueError) as exc:
            return str(exc), None
    return "Comparator selection saved as a frozen snapshot. Previous snapshots remain unchanged.", str(snapshot.id)


def load_comparison_from_ui(token: str, project_id: str | None, snapshot_id: str | None, request: gr.Request | None = None):
    token = _resolve_token(token, request)
    if not project_id or not snapshot_id:
        return go.Figure(), "Save a comparator selection to view the comparison."
    with SessionLocal() as db:
        try:
            user = get_authenticated_user(db, token)
            rows = comparison_rows(db, user, UUID(project_id), UUID(snapshot_id))
            name = comparator_name(db, UUID(snapshot_id))
        except (AuthenticationError, ValueError) as exc:
            return go.Figure(), str(exc)
    labels = [row["dimension"] for row in rows]
    ours = [row["our_score"] for row in rows]
    baseline = [row["baseline_median"] if row["compatible"] else None for row in rows]
    theta = labels + [labels[0]]
    ours_closed = ours + [ours[0]]
    baseline_closed = baseline + [baseline[0]]
    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(r=ours_closed, theta=theta, name="Our estimate", line={"color": "#1f77b4"}, fill="none"))
    fig.add_trace(go.Scatterpolar(r=baseline_closed, theta=theta, name=f"Historical median: {name}", line={"color": "#d62728", "dash": "dash"}, fill="none"))
    fig.update_layout(polar={"radialaxis": {"visible": True, "range": [0, 5]}}, showlegend=True, title="Prototype and historical comparison")
    lines = ["Dimension | Our score | Baseline median | Baseline spread | Difference | Compatibility", "---|---:|---:|---|---:|---"]
    for row in rows:
        ours_value = "unknown" if row["our_score"] is None else f"{row['our_score']:.1f}"
        median_value = "unknown" if row["baseline_median"] is None else f"{row['baseline_median']:.1f}"
        spread = "unknown" if row["baseline_p25"] is None else f"{row['baseline_p25']:.1f}-{row['baseline_p75']:.1f} (n={row['count']})"
        difference = "not calculated" if row["difference"] is None else f"{row['difference']:+.1f}"
        lines.append(f"{row['dimension']} | {ours_value} | {median_value} | {spread} | {difference} | {'Compatible' if row['compatible'] else 'Incompatible'}")
    return fig, "\n".join(lines)


def _hypotheses(db, project_id: str) -> list[Hypothesis]:
    return list(db.query(Hypothesis).filter(Hypothesis.project_id == UUID(project_id)).order_by(Hypothesis.kind, Hypothesis.created_at))


def _hypothesis_text(items: list[Hypothesis]) -> str:
    return "\n".join(f"[{item.kind}] {item.statement} | impact: {item.impact_if_wrong} | evidence: {item.evidence_strength} | status: {item.workflow_status}" for item in items) or "No hypotheses yet."


def _notes_text(items) -> str:
    return "\n".join(f"[{item.note_type}] {item.text}" for item in items) or "No notes yet."


def load_backlog_from_ui(token: str, project_id: str | None, request: gr.Request | None = None):
    token = _resolve_token(token, request)
    if not project_id:
        return "No notes yet.", "No hypotheses yet.", gr.update(choices=[]), gr.update(choices=[]), gr.update(choices=[]), gr.update(choices=[]), gr.update(choices=[])
    with SessionLocal() as db:
        try:
            user = get_authenticated_user(db, token)
            notes = list_notes(db, user, UUID(project_id))
            hypotheses = _hypotheses(db, project_id)
        except AuthenticationError:
            return "Session expired.", "Session expired.", gr.update(choices=[]), gr.update(choices=[]), gr.update(choices=[]), gr.update(choices=[]), gr.update(choices=[])
    choices = [(item.statement[:80], str(item.id)) for item in hypotheses]
    note_choices = [(item.text[:80], str(item.id)) for item in notes]
    return _notes_text(notes), _hypothesis_text(hypotheses), gr.update(choices=note_choices), gr.update(choices=choices), gr.update(choices=choices), gr.update(choices=note_choices), gr.update(choices=choices)


def save_note_from_ui(token: str, project_id: str | None, note_type: str, text: str, dimensions: list[str], request: gr.Request | None = None):
    token = _resolve_token(token, request)
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


def load_note_edit_from_ui(token: str, note_id: str | None, request: gr.Request | None = None):
    token = _resolve_token(token, request)
    if not note_id:
        return "observation", "", None
    with SessionLocal() as db:
        try:
            user = get_authenticated_user(db, token)
            note = db.get(Note, UUID(note_id))
            if note is None:
                raise ValueError("Note not found")
            get_project(db, user, note.project_id)
        except (AuthenticationError, ValueError, AuthorizationError) as exc:
            return str(exc), "", None
    return note.note_type, note.text, note.revision


def save_note_edit_from_ui(token: str, note_id: str | None, revision: int | None, note_type: str, text: str, dimensions: list[str], request: gr.Request | None = None):
    token = _resolve_token(token, request)
    if not note_id or revision is None:
        return "Select a saved note first.", None, ""
    dimension_keys = [definition["key"] for definition in DEFAULT_DIMENSIONS if definition["title"] in (dimensions or [])]
    with SessionLocal() as db:
        try:
            user = get_authenticated_user(db, token)
            note = update_note(db, user, UUID(note_id), revision, note_type, text, dimension_keys)
            notes = list_notes(db, user, note.project_id)
        except (AuthenticationError, AuthorizationError, RevisionConflict, ValueError) as exc:
            return str(exc), revision, ""
    return "Note updated.", note.revision, _notes_text(notes)


def load_hypothesis_edit_from_ui(token: str, hypothesis_id: str | None, request: gr.Request | None = None):
    token = _resolve_token(token, request)
    if not hypothesis_id:
        return "", "", "unknown", "unknown", "", None
    with SessionLocal() as db:
        try:
            user = get_authenticated_user(db, token)
            hypothesis = db.get(Hypothesis, UUID(hypothesis_id))
            if hypothesis is None:
                raise ValueError("Hypothesis not found")
            get_project(db, user, hypothesis.project_id)
        except (AuthenticationError, AuthorizationError, ValueError) as exc:
            return str(exc), "", "unknown", "unknown", "", None
    return hypothesis.statement, hypothesis.value_link, hypothesis.impact_if_wrong, hypothesis.evidence_strength, hypothesis.evidence_rationale, hypothesis.revision


def save_hypothesis_edit_from_ui(token: str, hypothesis_id: str | None, revision: int | None, statement: str, value_link: str, impact: str, evidence: str, evidence_rationale: str, request: gr.Request | None = None):
    token = _resolve_token(token, request)
    if not hypothesis_id or revision is None:
        return "Select a saved hypothesis first.", None, ""
    with SessionLocal() as db:
        try:
            user = get_authenticated_user(db, token)
            hypothesis = update_hypothesis(db, user, UUID(hypothesis_id), revision, statement=statement, value_link=value_link, impact_if_wrong=impact, evidence_strength=evidence, evidence_rationale=evidence_rationale)
            hypotheses = _hypotheses(db, str(hypothesis.project_id))
        except (AuthenticationError, AuthorizationError, RevisionConflict, ValueError) as exc:
            return str(exc), revision, ""
    return "Hypothesis updated.", hypothesis.revision, _hypothesis_text(hypotheses)


def save_hypothesis_from_ui(token: str, project_id: str | None, statement: str, value_link: str, impact: str, evidence: str, evidence_rationale: str, note_id: str | None, request: gr.Request | None = None):
    token = _resolve_token(token, request)
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


def filter_hypotheses_from_ui(token: str | None, project_id: str | None, dimension: str, status: str, impact: str, evidence: str, request: gr.Request | None = None):
    token = _resolve_token(token, request)
    if not project_id:
        return "No hypotheses yet.", gr.update(choices=[]), gr.update(choices=[])
    with SessionLocal() as db:
        try:
            _user = get_authenticated_user(db, token)
            hypotheses = _hypotheses(db, project_id)
            if dimension != "all":
                ids = {item.hypothesis_id for item in db.query(HypothesisDimension).filter_by(dimension_key=dimension).all()}
                hypotheses = [item for item in hypotheses if item.id in ids]
            if status != "all":
                hypotheses = [item for item in hypotheses if item.workflow_status == status]
            if impact != "all":
                hypotheses = [item for item in hypotheses if item.impact_if_wrong == impact]
            if evidence != "all":
                hypotheses = [item for item in hypotheses if item.evidence_strength == evidence]
        except AuthenticationError:
            return "Session expired.", gr.update(choices=[]), gr.update(choices=[])
    choices = [(item.statement[:80], str(item.id)) for item in hypotheses]
    return _hypothesis_text(hypotheses), gr.update(choices=choices), gr.update(choices=choices)


def save_relation_from_ui(token: str, project_id: str | None, relation_type: str, source_id: str | None, target_id: str | None, request: gr.Request | None = None):
    token = _resolve_token(token, request)
    if not project_id or not source_id or not target_id:
        return "Select a project and two hypotheses."
    with SessionLocal() as db:
        try:
            user = get_authenticated_user(db, token)
            add_relation(db, user, UUID(project_id), relation_type, UUID(source_id), UUID(target_id))
        except (AuthenticationError, ValueError) as exc:
            return str(exc)
    return "Hypothesis relationship saved."


def save_experiment_plan(token: str, project_id: str | None, primary_id: str | None, title: str, method: str, request: gr.Request | None = None):
    token = _resolve_token(token, request)
    if not project_id or not primary_id:
        return "Select a project and primary hypothesis first.", None, None
    with SessionLocal() as db:
        try:
            user = get_authenticated_user(db, token)
            experiment = create_experiment(db, user, UUID(project_id), UUID(primary_id), title, method)
        except (AuthenticationError, ValueError) as exc:
            return str(exc), None, None
    return "Experiment plan created. Add the procedure and success criteria below.", str(experiment.id), experiment.revision


def load_experiment_choices(token: str, project_id: str | None, request: gr.Request | None = None):
    token = _resolve_token(token, request)
    if not project_id:
        return gr.update(choices=[])
    with SessionLocal() as db:
        try:
            user = get_authenticated_user(db, token)
            experiments = list_experiments(db, user, UUID(project_id))
        except AuthenticationError:
            return gr.update(choices=[])
    return gr.update(choices=[(item.title[:80], str(item.id)) for item in experiments])


def load_experiment_edit_from_ui(token: str, experiment_id: str | None, request: gr.Request | None = None):
    token = _resolve_token(token, request)
    if not experiment_id:
        return "", "prototype_walkthrough", "", "", "", "", "", "", "", "", "planned", "", "", "", "", "undecided", None
    with SessionLocal() as db:
        try:
            user = get_authenticated_user(db, token)
            experiment = db.get(Experiment, UUID(experiment_id))
            if experiment is None:
                raise ValueError("Experiment not found")
            get_project(db, user, experiment.project_id)
        except (AuthenticationError, AuthorizationError, ValueError) as exc:
            return str(exc), "prototype_walkthrough", "", "", "", "", "", "", "", "", "planned", "", "", "", "", "undecided", None
    return (experiment.title, experiment.method, experiment.procedure, experiment.participants, experiment.comparison_baseline, experiment.metric, experiment.success_criterion, experiment.guardrail, experiment.resources, experiment.owner, experiment.planned_date, experiment.status, experiment.results, experiment.evidence_links, experiment.limitations, experiment.conclusion, experiment.resulting_decision, experiment.revision)


def save_experiment_details(token: str, project_id: str | None, experiment_id: str | None, revision: int | None, procedure: str, participants: str, baseline: str, metric: str, success: str, guardrail: str, resources: str, owner: str, planned_date: str, status_value: str, results: str, evidence_links: str, limitations: str, conclusion: str, decision: str, request: gr.Request | None = None):
    token = _resolve_token(token, request)
    if not project_id or not experiment_id or revision is None:
        return "Create an experiment plan first.", revision
    with SessionLocal() as db:
        try:
            user = get_authenticated_user(db, token)
            update_experiment(db, user, UUID(experiment_id), revision, procedure=procedure, participants=participants, comparison_baseline=baseline, metric=metric, success_criterion=success, guardrail=guardrail, resources=resources, owner=owner, planned_date=planned_date, status=status_value, results=results, evidence_links=evidence_links, limitations=limitations, conclusion=conclusion, resulting_decision=decision)
        except (AuthenticationError, RevisionConflict, ValueError) as exc:
            return str(exc), revision
    return "Experiment saved. Completion does not automatically support the hypothesis.", revision + 1


def save_experiment_action(token: str | None, project_id: str | None, experiment_id: str | None, revision: int | None, procedure: str, participants: str, baseline: str, metric: str, success: str, guardrail: str, resources: str, owner: str, planned_date: str, status_value: str, results: str, evidence_links: str, limitations: str, conclusion: str, decision: str, request: gr.Request | None = None):
    status, new_revision = save_experiment_details(token, project_id, experiment_id, revision, procedure, participants, baseline, metric, success, guardrail, resources, owner, planned_date, status_value, results, evidence_links, limitations, conclusion, decision, request=request)
    return status, new_revision, not status.startswith("Experiment saved")


def autosave_experiment_from_ui(token: str | None, project_id: str | None, experiment_id: str | None, revision: int | None, dirty: bool, procedure: str, participants: str, baseline: str, metric: str, success: str, guardrail: str, resources: str, owner: str, planned_date: str, status_value: str, results: str, evidence_links: str, limitations: str, conclusion: str, decision: str, request: gr.Request | None = None):
    if not dirty:
        return gr.update(), revision, dirty
    status, new_revision = save_experiment_details(token, project_id, experiment_id, revision, procedure, participants, baseline, metric, success, guardrail, resources, owner, planned_date, status_value, results, evidence_links, limitations, conclusion, decision, request=request)
    if status.startswith("Experiment saved"):
        return "Experiment saved automatically.", new_revision, False
    return f"Save failed: {status}", new_revision, True


def checklist_text(token: str | None, project_id: str | None, request: gr.Request | None = None):
    token = _resolve_token(token, request)
    if not project_id:
        return "Select a project to see the workshop checklist."
    with SessionLocal() as db:
        try:
            user = get_authenticated_user(db, token)
            checklist = completion_checklist(db, user, UUID(project_id))
        except AuthenticationError:
            return "Session expired."
    return "\n".join(f"{'[x]' if complete else '[ ]'} {label}" for label, complete in checklist.items())


def priority_text(token: str | None, project_id: str | None, request: gr.Request | None = None):
    token = _resolve_token(token, request)
    if not project_id:
        return "Select a project to see priority guidance."
    with SessionLocal() as db:
        try:
            user = get_authenticated_user(db, token)
            return priority_guidance(db, user, UUID(project_id))
        except AuthenticationError:
            return "Session expired."


def export_project_from_ui(token: str | None, project_id: str | None, request: gr.Request | None = None):
    token = _resolve_token(token, request)
    if not project_id:
        return "Select a project before exporting.", None, None
    with SessionLocal() as db:
        try:
            user = get_authenticated_user(db, token)
            json_path, markdown_path = write_export_files(db, user, UUID(project_id))
        except (AuthenticationError, ValueError) as exc:
            return str(exc), None, None
    return "Exports generated.", json_path, markdown_path


def save_risk_reflection_from_ui(token: str | None, project_id: str | None, score, entry: str, behavior: str, affected: str, consequence: str, safeguard: str, uncertainty: str, request: gr.Request | None = None):
    token = _resolve_token(token, request)
    if not project_id:
        return "Select a project first."
    with SessionLocal() as db:
        try:
            user = get_authenticated_user(db, token)
            save_reflection(db, user, UUID(project_id), "adversarial_risk", uncertainty, subjective_score=score, attack_entry_point=entry, unwanted_behavior=behavior, affected_data_action=affected, consequence=consequence, proposed_safeguard=safeguard)
        except (AuthenticationError, ValueError) as exc:
            return str(exc)
    return "Adversarial-risk reflection saved. The score is a subjective discussion input, not a calibrated security assessment."


def save_feedback_reflection_from_ui(token: str | None, project_id: str | None, signal: str, meaning: str, change: str, human: str, evaluation: str, request: gr.Request | None = None):
    token = _resolve_token(token, request)
    if not project_id:
        return "Select a project first."
    with SessionLocal() as db:
        try:
            user = get_authenticated_user(db, token)
            save_reflection(db, user, UUID(project_id), "feedback_loop", "", signal_to_collect=signal, signal_meaning=meaning, possible_product_change=change, human_interpretation_needed=human, evaluation_after_change=evaluation)
        except (AuthenticationError, ValueError) as exc:
            return str(exc)
    return "Feedback-loop reflection saved."


def instructor_overview_from_ui(token: str | None, request: gr.Request | None = None):
    token = _resolve_token(token, request)
    with SessionLocal() as db:
        try:
            user = get_authenticated_user(db, token)
            rows = course_overview(db, user)
        except (AuthenticationError, ValueError) as exc:
            return str(exc)
    if not rows:
        return "No projects yet."
    return "\n".join(f"{row['team_alias']} | {row['product_name']} | checklist {row['completed_items']}/{row['total_items']} | id {row['project_id']}" for row in rows)


def import_baselines_from_ui(token: str | None, directory: str, cohort: str, publish: bool, request: gr.Request | None = None):
    token = _resolve_token(token, request)
    with SessionLocal() as db:
        try:
            user = get_authenticated_user(db, token)
            report = import_baselines_as_instructor(db, user, directory, cohort, publish)
        except (AuthenticationError, ValueError) as exc:
            return str(exc), ""
    return f"Imported {report['records']} records from {report['files']} files.", str(report)


def provision_team_from_ui(token: str | None, course_name: str, alias: str, password: str, request: gr.Request | None = None):
    token = _resolve_token(token, request)
    with SessionLocal() as db:
        try:
            user = get_authenticated_user(db, token)
            team = provision_team_account(db, user, course_name, alias, password)
        except (AuthenticationError, ValueError) as exc:
            return str(exc)
    return f"Team account '{team.alias}' created. Share the password securely and do not store it in project content."


def update_retention_from_ui(token: str | None, course_name: str, retention_days: int, policy: str, request: gr.Request | None = None):
    token = _resolve_token(token, request)
    with SessionLocal() as db:
        try:
            user = get_authenticated_user(db, token)
            update_course_retention(db, user, course_name, retention_days, policy)
        except (AuthenticationError, ValueError) as exc:
            return str(exc)
    return "Retention settings saved."


def delete_project_from_ui(token: str | None, project_id: str, confirm: bool, request: gr.Request | None = None):
    token = _resolve_token(token, request)
    with SessionLocal() as db:
        try:
            user = get_authenticated_user(db, token)
            delete_project_as_instructor(db, user, UUID(project_id), confirm)
        except (AuthenticationError, ValueError) as exc:
            return str(exc)
    return "Project and its editable content were deleted."


def section_context(section: str, language: str = "en") -> str:
    descriptions = load_catalog(language)["sections"]
    return descriptions.get(section, descriptions["Project Brief"])


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
            gr.Markdown("### Retention and deletion")
            retention_course = gr.Textbox(label="Course name", value="AIPM Workshop")
            retention_days = gr.Number(label="Retention days", value=180, precision=0)
            retention_policy = gr.Textbox(label="Deletion policy", value="Delete course data after the configured retention period.", lines=2)
            save_retention_button = gr.Button("Save retention settings")
            save_retention_button.click(update_retention_from_ui, [token, retention_course, retention_days, retention_policy], status)
            delete_project_id = gr.Textbox(label="Project UUID to delete")
            confirm_delete = gr.Checkbox(label="I understand this permanently deletes the project", value=False)
            delete_project_button = gr.Button("Delete project", variant="stop")
            delete_project_button.click(delete_project_from_ui, [token, delete_project_id, confirm_delete], status)
        with gr.Column(visible=False) as team_panel:
            language_selector = gr.Dropdown(label="Language / Sprache", choices=[("English", "en"), ("Deutsch", "de")], value="en")
            section_selector = gr.Radio(label="Current section", choices=["Project Brief", "Dimension Explorer", "Notes", "Hypothesis Backlog", "Experiments", "Summary & Export"], value="Project Brief")
            section_context_display = gr.Markdown(section_context("Project Brief", "en"))
            section_selector.change(section_context, [section_selector, language_selector], section_context_display, js="""(section) => { const ids = {'Project Brief': 'section-project-brief', 'Dimension Explorer': 'section-dimension-explorer', 'Notes': 'section-notes', 'Hypothesis Backlog': 'section-hypothesis-backlog', 'Experiments': 'section-experiments', 'Summary & Export': 'section-summary-export'}; document.getElementById(ids[section])?.scrollIntoView({behavior: 'smooth', block: 'start'}); }""")
            language_selector.change(section_context, [section_selector, language_selector], section_context_display)
            gr.Markdown("## 1. Project Brief", elem_id="section-project-brief")
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
            brief_dirty = gr.State(False)
            brief_timer = gr.Timer(2.0)
            brief_fields = [product_name, product_type, description, target_user, job, problem, hypothesis, figma_url]
            for brief_field in brief_fields:
                brief_field.input(lambda: True, outputs=brief_dirty)
            gr.Markdown("## 2. Dimension Explorer", elem_id="section-dimension-explorer")
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
            gr.Markdown("## 2. Dimension Explorer: Comparator")
            gr.Markdown("Historical profiles are classroom assessments, not current product ratings or rankings.")
            comparator = gr.Dropdown(label="Historical comparator", choices=[])
            comparator_purpose = gr.Radio(label="Comparison purpose", choices=[("Task comparator", "task_comparator"), ("Design contrast", "design_contrast")], value="task_comparator")
            comparator_scope = gr.Textbox(label="Comparison scope or explanation", lines=2)
            save_comparator_button = gr.Button("Save comparator selection")
            comparator_snapshot_id = gr.State(None)
            comparison_chart = gr.Plot(label="Comparison radar")
            comparison_table = gr.Textbox(label="Comparison table", interactive=False, lines=8)
            gr.Markdown("## 3. Notes", elem_id="section-notes")
            note_type = gr.Dropdown(label="Note type", choices=[("Observation", "observation"), ("Assumption", "assumption"), ("Question", "question"), ("Design decision", "design_decision")], value="observation")
            note_text = gr.Textbox(label="Note", lines=3)
            note_dimensions = gr.CheckboxGroup(label="Linked dimensions", choices=[definition["title"] for definition in DEFAULT_DIMENSIONS])
            save_note_button = gr.Button("Save note")
            notes_display = gr.Textbox(label="Saved notes", interactive=False, lines=5)
            note_edit_selector = gr.Dropdown(label="Reopen note", choices=[])
            note_edit_type = gr.Dropdown(label="Edited note type", choices=[("Observation", "observation"), ("Assumption", "assumption"), ("Question", "question"), ("Design decision", "design_decision")], value="observation")
            note_edit_text = gr.Textbox(label="Edited note", lines=3)
            note_edit_revision = gr.State(None)
            update_note_button = gr.Button("Update note")
            gr.Markdown("## 4. Hypothesis Backlog", elem_id="section-hypothesis-backlog")
            hypothesis_statement = gr.Textbox(label="Supporting hypothesis statement", lines=3)
            hypothesis_value_link = gr.Textbox(label="Why it matters / value link", lines=2)
            hypothesis_impact = gr.Dropdown(label="Impact if wrong", choices=["unknown", "low", "medium", "high"], value="unknown")
            hypothesis_evidence = gr.Dropdown(label="Evidence strength", choices=["unknown", "none", "limited", "moderate", "strong"], value="unknown")
            hypothesis_evidence_rationale = gr.Textbox(label="Evidence rationale", lines=2)
            hypothesis_note = gr.Dropdown(label="Originating note (optional)", choices=[])
            save_hypothesis_button = gr.Button("Create supporting hypothesis")
            hypotheses_display = gr.Textbox(label="Hypothesis backlog", interactive=False, lines=7)
            hypothesis_filter_dimension = gr.Dropdown(label="Filter dimension", choices=[("All dimensions", "all")] + [(definition["title"], definition["key"]) for definition in DEFAULT_DIMENSIONS], value="all")
            hypothesis_filter_status = gr.Dropdown(label="Filter workflow status", choices=[("All statuses", "all"), "draft", "ready_to_test", "testing", "reviewed", "archived"], value="all")
            hypothesis_filter_impact = gr.Dropdown(label="Filter impact", choices=[("All impact", "all"), "unknown", "low", "medium", "high"], value="all")
            hypothesis_filter_evidence = gr.Dropdown(label="Filter evidence", choices=[("All evidence", "all"), "unknown", "none", "limited", "moderate", "strong"], value="all")
            hypothesis_edit_selector = gr.Dropdown(label="Reopen hypothesis", choices=[])
            hypothesis_edit_statement = gr.Textbox(label="Edited hypothesis statement", lines=3)
            hypothesis_edit_value = gr.Textbox(label="Edited value link", lines=2)
            hypothesis_edit_impact = gr.Dropdown(label="Edited impact if wrong", choices=["unknown", "low", "medium", "high"], value="unknown")
            hypothesis_edit_evidence = gr.Dropdown(label="Edited evidence strength", choices=["unknown", "none", "limited", "moderate", "strong"], value="unknown")
            hypothesis_edit_rationale = gr.Textbox(label="Edited evidence rationale", lines=2)
            hypothesis_edit_revision = gr.State(None)
            update_hypothesis_button = gr.Button("Update hypothesis")
            gr.Markdown("### Link hypotheses")
            relation_type = gr.Dropdown(label="Relationship", choices=[("Contributes to", "contributes_to"), ("Depends on", "depends_on"), ("Alternative to", "alternative_to"), ("In tension with", "in_tension_with")], value="contributes_to")
            relation_source = gr.Dropdown(label="From hypothesis", choices=[])
            relation_target = gr.Dropdown(label="To hypothesis", choices=[])
            save_relation_button = gr.Button("Save relationship")
            gr.Markdown("## 5. Experiments", elem_id="section-experiments")
            experiment_selector = gr.Dropdown(label="Reopen experiment", choices=[])
            experiment_primary = gr.Dropdown(label="Primary hypothesis", choices=[])
            experiment_title = gr.Textbox(label="Experiment title")
            experiment_method = gr.Dropdown(label="Method", choices=[("Prototype walkthrough", "prototype_walkthrough"), ("User interview", "user_interview"), ("Comparative usability test", "comparative_usability_test"), ("Model/output evaluation", "model_output_evaluation"), ("Technical feasibility test", "technical_feasibility_test"), ("Cost estimate/simulation", "cost_estimate_simulation"), ("Pilot", "pilot"), ("Other", "other")], value="prototype_walkthrough")
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
            checklist_display = gr.Textbox(label="Workshop checklist", interactive=False, lines=8)
            priority_display = gr.Textbox(label="Priority guidance", interactive=False, lines=8)
            gr.Markdown("## 6. Summary & Export", elem_id="section-summary-export")
            export_button = gr.Button("Generate JSON and Markdown exports")
            json_download = gr.File(label="JSON export")
            markdown_download = gr.File(label="Markdown export")
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
        submit.click(login, [username, password], [status, token, login_panel, workspace_panel]).then(workspace, token, [workspace_text, login_panel, instructor_panel, team_panel, project_dropdown])
        create_button.click(create_project_from_ui, [token, new_project_name], [status, project_dropdown, product_name, project_revision])
        with gr.Row():
            project_dropdown.change(load_project_from_ui, [token, project_dropdown], [project_title, product_name, description, target_user, job, problem, hypothesis, product_type, figma_url, project_id, project_revision]).then(load_estimates_from_ui, [token, project_id], assessment_components + [assessment_revisions]).then(load_comparator_choices, outputs=comparator).then(load_backlog_from_ui, [token, project_id], [notes_display, hypotheses_display, hypothesis_note, relation_source, relation_target, note_edit_selector, hypothesis_edit_selector]).then(lambda choices: choices, relation_source, experiment_primary).then(load_experiment_choices, [token, project_id], experiment_selector).then(checklist_text, [token, project_id], checklist_display).then(priority_text, [token, project_id], priority_display).then(lambda: False, outputs=brief_dirty).then(lambda: False, outputs=assessment_dirty)
            save_button.click(save_project_action, [token, project_id, project_revision, product_name, product_type, description, target_user, job, problem, hypothesis, figma_url], [status, project_revision, brief_dirty])
            brief_timer.tick(autosave_project_from_ui, [token, project_id, project_revision, brief_dirty, product_name, product_type, description, target_user, job, problem, hypothesis, figma_url], [status, project_revision, brief_dirty])
            save_assessments_button.click(save_assessments_action, [token, project_id, assessment_revisions, *assessment_components], [status, assessment_revisions, assessment_dirty])
            assessment_timer.tick(autosave_assessments_from_ui, [token, project_id, assessment_revisions, assessment_dirty, *assessment_components], [status, assessment_revisions, assessment_dirty])
        save_comparator_button.click(save_comparator_from_ui, [token, project_id, comparator, comparator_purpose, comparator_scope], [status, comparator_snapshot_id]).then(load_comparison_from_ui, [token, project_id, comparator_snapshot_id], [comparison_chart, comparison_table])
        save_note_button.click(save_note_from_ui, [token, project_id, note_type, note_text, note_dimensions], [status, notes_display])
        save_hypothesis_button.click(save_hypothesis_from_ui, [token, project_id, hypothesis_statement, hypothesis_value_link, hypothesis_impact, hypothesis_evidence, hypothesis_evidence_rationale, hypothesis_note], [status, hypotheses_display, relation_source]).then(load_backlog_from_ui, [token, project_id], [notes_display, hypotheses_display, hypothesis_note, relation_source, relation_target, note_edit_selector, hypothesis_edit_selector])
        for hypothesis_filter in [hypothesis_filter_dimension, hypothesis_filter_status, hypothesis_filter_impact, hypothesis_filter_evidence]:
            hypothesis_filter.change(filter_hypotheses_from_ui, [token, project_id, hypothesis_filter_dimension, hypothesis_filter_status, hypothesis_filter_impact, hypothesis_filter_evidence], [hypotheses_display, relation_source, relation_target])
        note_edit_selector.change(load_note_edit_from_ui, [token, note_edit_selector], [note_edit_type, note_edit_text, note_edit_revision])
        update_note_button.click(save_note_edit_from_ui, [token, note_edit_selector, note_edit_revision, note_edit_type, note_edit_text, note_dimensions], [status, note_edit_revision, notes_display]).then(load_backlog_from_ui, [token, project_id], [notes_display, hypotheses_display, hypothesis_note, relation_source, relation_target, note_edit_selector, hypothesis_edit_selector])
        hypothesis_edit_selector.change(load_hypothesis_edit_from_ui, [token, hypothesis_edit_selector], [hypothesis_edit_statement, hypothesis_edit_value, hypothesis_edit_impact, hypothesis_edit_evidence, hypothesis_edit_rationale, hypothesis_edit_revision])
        update_hypothesis_button.click(save_hypothesis_edit_from_ui, [token, hypothesis_edit_selector, hypothesis_edit_revision, hypothesis_edit_statement, hypothesis_edit_value, hypothesis_edit_impact, hypothesis_edit_evidence, hypothesis_edit_rationale], [status, hypothesis_edit_revision, hypotheses_display]).then(load_backlog_from_ui, [token, project_id], [notes_display, hypotheses_display, hypothesis_note, relation_source, relation_target, note_edit_selector, hypothesis_edit_selector])
        save_relation_button.click(save_relation_from_ui, [token, project_id, relation_type, relation_source, relation_target], status)
        create_experiment_button.click(save_experiment_plan, [token, project_id, experiment_primary, experiment_title, experiment_method], [status, experiment_id, experiment_revision]).then(load_experiment_choices, [token, project_id], experiment_selector).then(lambda: False, outputs=experiment_dirty).then(checklist_text, [token, project_id], checklist_display).then(priority_text, [token, project_id], priority_display)
        save_experiment_button.click(save_experiment_action, [token, project_id, experiment_id, experiment_revision, experiment_procedure, experiment_participants, experiment_baseline, experiment_metric, experiment_success, experiment_guardrail, experiment_resources, experiment_owner, experiment_date, experiment_status, experiment_results, experiment_links, experiment_limitations, experiment_conclusion, experiment_decision], [status, experiment_revision, experiment_dirty]).then(checklist_text, [token, project_id], checklist_display).then(priority_text, [token, project_id], priority_display)
        experiment_timer.tick(autosave_experiment_from_ui, [token, project_id, experiment_id, experiment_revision, experiment_dirty, experiment_procedure, experiment_participants, experiment_baseline, experiment_metric, experiment_success, experiment_guardrail, experiment_resources, experiment_owner, experiment_date, experiment_status, experiment_results, experiment_links, experiment_limitations, experiment_conclusion, experiment_decision], [status, experiment_revision, experiment_dirty])
        experiment_selector.change(load_experiment_edit_from_ui, [token, experiment_selector], [experiment_title, experiment_method, experiment_procedure, experiment_participants, experiment_baseline, experiment_metric, experiment_success, experiment_guardrail, experiment_resources, experiment_owner, experiment_date, experiment_status, experiment_results, experiment_links, experiment_limitations, experiment_conclusion, experiment_decision, experiment_revision]).then(lambda selected: selected, experiment_selector, experiment_id).then(lambda: False, outputs=experiment_dirty)
        export_button.click(export_project_from_ui, [token, project_id], [status, json_download, markdown_download])
        save_risk_button.click(save_risk_reflection_from_ui, [token, project_id, risk_score, risk_entry, risk_behavior, risk_affected, risk_consequence, risk_safeguard, risk_uncertainty], status)
        save_feedback_button.click(save_feedback_reflection_from_ui, [token, project_id, feedback_signal, feedback_meaning, feedback_change, feedback_human, feedback_evaluation], status)
        app.load(auto_login, outputs=[status, token, login_panel, workspace_panel]).then(workspace, token, [workspace_text, login_panel, instructor_panel, team_panel, project_dropdown])
    return app


app = build_app()


if __name__ == "__main__":
    app.launch()
