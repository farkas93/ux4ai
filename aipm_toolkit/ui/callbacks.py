"""Callback functions for the AIPM Toolkit workspace.

These functions are intentionally free of Gradio layout code; they resolve the
authenticated actor from the request cookie and delegate to application
services.
"""

import json
from uuid import UUID

import gradio as gr
import plotly.graph_objects as go
from sqlalchemy import delete, select

from ..assessment_services import (
    ensure_scale_definitions,
    get_project_estimates,
    save_project_estimates,
)
from ..auth import (
    AuthenticationError,
    AuthorizationError,
    RevisionConflict,
    authenticate,
    get_authenticated_user,
)
from ..baseline_services import published_datasets, select_comparator
from ..comparison_services import comparison_rows
from ..db import SessionLocal
from ..dimensions import DEFAULT_DIMENSIONS
from ..experiment_services import (
    completion_checklist,
    create_experiment,
    list_experiments,
    priority_guidance,
    save_reflection,
    update_experiment,
)
from ..export_services import export_project_markdown, write_export_files
from ..hypothesis_services import (
    add_relation,
    create_hypothesis,
    create_note,
    list_notes,
    set_placement,
    update_hypothesis,
    update_note,
)
from ..i18n import load_catalog
from ..instructor_services import (
    course_overview,
    import_baselines_as_instructor,
    provision_team_account,
)
from ..lifecycle_services import delete_project
from ..models import (
    ComparisonSnapshot,
    Experiment,
    Hypothesis,
    HypothesisDimension,
    HypothesisSource,
    Note,
    NoteDimension,
    Role,
)
from ..services import (
    create_project,
    get_project,
    list_projects,
    update_main_hypothesis,
    update_project,
    validate_figma_url,
)
from ..upload_services import preview_upload, publish_upload


def login(username: str, password: str):
    with SessionLocal() as db:
        try:
            token, user = authenticate(db, username, password)
        except AuthenticationError as exc:
            return gr.update(value=str(exc)), None, gr.update(visible=True), gr.update(visible=False)
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
            return "Session expired. Please sign in again.", gr.update(visible=True), gr.update(visible=False), gr.update(visible=False), gr.update()
    if user.role == Role.INSTRUCTOR.value:
        return "Instructor area: course progress, teams, and baselines.", gr.update(visible=False), gr.update(visible=True), gr.update(visible=False), gr.update()
    with SessionLocal() as db:
        projects = list_projects(db, user)
    choices = [(project.product_name, str(project.id)) for project in projects]
    return "Select an existing product or create a new draft.", gr.update(visible=False), gr.update(visible=False), gr.update(visible=True), gr.update(choices=choices, value=choices[0][1] if choices else None)


def create_project_from_ui(token: str, product_name: str, request: gr.Request | None = None):
    token = _resolve_token(token, request)
    if not product_name or not product_name.strip():
        return "Please specify a product name.", gr.update(), "", gr.update(visible=True)
    with SessionLocal() as db:
        try:
            user = get_authenticated_user(db, token)
            project = create_project(db, user, product_name.strip())
            choices = [(item.product_name, str(item.id)) for item in list_projects(db, user)]
        except (AuthenticationError, ValueError) as exc:
            return str(exc), gr.update(), "", gr.update(visible=True)
    return (
        f"Product '{project.product_name}' created.",
        gr.update(choices=choices, value=str(project.id)),
        "",
        gr.update(visible=False),
    )


def load_project_from_ui(token: str, project_id: str | None, request: gr.Request | None = None):
    token = _resolve_token(token, request)
    if not project_id:
        return "", "", "", "", "", None, "", None
    with SessionLocal() as db:
        try:
            user = get_authenticated_user(db, token)
            project = get_project(db, user, UUID(project_id))
            hypothesis = next(iter(project.hypotheses), None)
        except (AuthenticationError, ValueError, LookupError):
            return "", "", "", "", "", None, "", None
    return (
        project.short_description,
        project.target_user,
        project.job_to_be_done,
        project.current_problem,
        hypothesis.statement if hypothesis else "",
        project.product_type,
        project.figma_url,
        project.revision,
    )


def save_project_from_ui(token: str, project_id: str | None, revision: int | None, product_type: str | None, description: str, target_user: str, job: str, problem: str, hypothesis: str, figma_url: str, request: gr.Request | None = None):
    token = _resolve_token(token, request)
    if not project_id or revision is None:
        return "Select a product first.", revision
    with SessionLocal() as db:
        try:
            user = get_authenticated_user(db, token)
            updated_url = validate_figma_url(figma_url)
            project = update_project(db, user, UUID(project_id), revision, product_type=product_type, short_description=description, target_user=target_user, job_to_be_done=job, current_problem=problem, figma_url=updated_url)
            main = next(iter(project.hypotheses), None)
            if main:
                update_main_hypothesis(db, user, project.id, main.revision, hypothesis)
        except (AuthenticationError, RevisionConflict, ValueError) as exc:
            return str(exc), revision
    return "Product setup saved.", project.revision


def save_project_action(token: str, project_id: str | None, revision: int | None, product_type: str | None, description: str, target_user: str, job: str, problem: str, hypothesis: str, figma_url: str, request: gr.Request | None = None):
    token = _resolve_token(token, request)
    status, new_revision = save_project_from_ui(token, project_id, revision, product_type, description, target_user, job, problem, hypothesis, figma_url)
    return status, new_revision, not status.startswith("Product setup saved")


def autosave_project_from_ui(token: str, project_id: str | None, revision: int | None, dirty: bool, product_type: str | None, description: str, target_user: str, job: str, problem: str, hypothesis: str, figma_url: str, request: gr.Request | None = None):
    token = _resolve_token(token, request)
    if not dirty:
        return gr.update(), revision, dirty
    status, new_revision = save_project_from_ui(token, project_id, revision, product_type, description, target_user, job, problem, hypothesis, figma_url)
    if status.startswith("Product setup saved"):
        return "Product setup saved automatically.", new_revision, False
    return f"Save failed: {status}", new_revision, True


def load_estimates_from_ui(token: str, project_id: str | None, request: gr.Request | None = None):
    token = _resolve_token(token, request)
    blank = []
    if not project_id:
        return (*[value for _ in DEFAULT_DIMENSIONS for value in (2.5, "")], [])
    with SessionLocal() as db:
        try:
            user = get_authenticated_user(db, token)
            ensure_scale_definitions(db)
            estimates = get_project_estimates(db, user, UUID(project_id))
        except (AuthenticationError, ValueError):
            return (*[value for _ in DEFAULT_DIMENSIONS for value in (2.5, "")], [])
    revisions = []
    for estimate in estimates:
        score = 2.5 if estimate.score is None else float(estimate.score)
        blank.extend([score, estimate.rationale or ""])
        revisions.append(estimate.revision)
    return (*blank, revisions)


def save_estimates_from_ui(token: str, project_id: str | None, revisions: list[int] | None, *values, request: gr.Request | None = None):
    token = _resolve_token(token, request)
    if not project_id:
        return "Select a product before saving dimension assessments.", revisions or []
    revisions = revisions or [None] * len(DEFAULT_DIMENSIONS)
    records = []
    for index, definition in enumerate(DEFAULT_DIMENSIONS):
        offset = index * 2
        score = values[offset] if offset < len(values) and values[offset] is not None else 2.5
        reasoning = values[offset + 1] if offset + 1 < len(values) and values[offset + 1] is not None else ""
        records.append(
            {
                "dimension_key": definition["key"],
                "status": "estimated",
                "score": float(score),
                "rationale": str(reasoning),
                "revision": revisions[index],
            }
        )
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


def load_frozen_profile_from_ui(token: str | None, project_id: str | None, snapshot_id: str | None, request: gr.Request | None = None):
    token = _resolve_token(token, request)
    if not project_id or not snapshot_id:
        return {}
    with SessionLocal() as db:
        try:
            user = get_authenticated_user(db, token)
            snapshot = db.get(ComparisonSnapshot, UUID(snapshot_id))
            if snapshot is None or snapshot.project_id != UUID(project_id):
                raise ValueError("Snapshot not found")
            get_project(db, user, snapshot.project_id)
        except (AuthenticationError, ValueError, AuthorizationError):
            return {}
    return json.loads(snapshot.frozen_profile or "{}")


def comparison_table_from_ui(token: str | None, project_id: str | None, snapshot_id: str | None, request: gr.Request | None = None):
    token = _resolve_token(token, request)
    if not project_id or not snapshot_id:
        return "Select a comparator to see the comparison table."
    with SessionLocal() as db:
        try:
            user = get_authenticated_user(db, token)
            rows = comparison_rows(db, user, UUID(project_id), UUID(snapshot_id))
        except (AuthenticationError, ValueError) as exc:
            return str(exc)
    lines = ["Dimension | Our score | Baseline median | Baseline spread | Difference | Compatibility", "---|---:|---:|---|---:|---"]
    for row in rows:
        ours_value = "unknown" if row["our_score"] is None else f"{row['our_score']:.1f}"
        median_value = "unknown" if row["baseline_median"] is None else f"{row['baseline_median']:.1f}"
        spread = "unknown" if row["baseline_p25"] is None else f"{row['baseline_p25']:.1f}-{row['baseline_p75']:.1f} (n={row['count']})"
        difference = "not calculated" if row["difference"] is None else f"{row['difference']:+.1f}"
        lines.append(f"{row['dimension']} | {ours_value} | {median_value} | {spread} | {difference} | {'Compatible' if row['compatible'] else 'Incompatible'}")
    return "\n".join(lines)


def live_profile_from_ui(frozen_state: dict | None, *values):
    """Draw the spider chart from the 5 dimension slider values plus an optional frozen baseline."""
    frozen = frozen_state or {}
    labels = [definition["key"] for definition in DEFAULT_DIMENSIONS]
    ours = []
    for index in range(len(DEFAULT_DIMENSIONS)):
        if index < len(values) and values[index] is not None:
            ours.append(float(values[index]))
        else:
            ours.append(2.5)
    fig = go.Figure()
    theta = labels + [labels[0]]
    fig.add_trace(
        go.Scatterpolar(
            r=[v for v in ours] + [ours[0]],
            theta=theta,
            name="Current product",
            line={"color": "#1f77b4", "width": 3},
            fill="toself",
            fillcolor="rgba(31, 119, 180, 0.15)",
        )
    )
    baseline = [
        None if not frozen.get(key, {}).get("compatible", True) else frozen.get(key, {}).get("median")
        for key in labels
    ]
    if any(value is not None for value in baseline):
        baseline_closed = baseline + [baseline[0]]
        fig.add_trace(
            go.Scatterpolar(
                r=baseline_closed,
                theta=theta,
                name="Historical comparator",
                line={"color": "#d62728", "width": 2, "dash": "dash"},
                fill="none",
            )
        )
    fig.update_layout(
        polar={"radialaxis": {"visible": True, "range": [0, 5], "tickvals": [0, 1, 2, 3, 4, 5]}},
        showlegend=True,
        title="Live Dimension Profile (0–5)",
        margin={"l": 40, "r": 40, "t": 40, "b": 40},
        height=380,
    )
    return fig


def on_comparator_selected(token: str | None, project_id: str | None, dataset_id: str | None, request: gr.Request | None = None):
    token = _resolve_token(token, request)
    if not project_id or not dataset_id:
        return {}, "No comparator selected."
    with SessionLocal() as db:
        try:
            user = get_authenticated_user(db, token)
            snapshot = select_comparator(db, user, UUID(project_id), UUID(dataset_id), "task_comparator", "Direct comparison")
            frozen = json.loads(snapshot.frozen_profile or "{}")
            table_text = comparison_table_from_ui(token, project_id, str(snapshot.id))
            return frozen, table_text
        except (AuthenticationError, ValueError) as exc:
            return {}, str(exc)


def dimension_notes_from_ui(token: str | None, project_id: str | None, dimension_key: str, request: gr.Request | None = None):
    token = _resolve_token(token, request)
    if not project_id or not dimension_key:
        return "No questions or assumptions for this dimension yet."
    with SessionLocal() as db:
        try:
            user = get_authenticated_user(db, token)
            get_project(db, user, UUID(project_id))
            rows = db.execute(select(Note.note_type, Note.text).join(NoteDimension, NoteDimension.note_id == Note.id).where(Note.project_id == UUID(project_id), NoteDimension.dimension_key == dimension_key).order_by(Note.created_at)).all()
        except AuthenticationError:
            return "Session expired."
    if not rows:
        return "No questions or assumptions for this dimension yet."
    return "\n".join(f"[{note_type}] {text}" for note_type, text in rows)


def add_dimension_note_from_ui(token: str | None, project_id: str | None, dimension_key: str, note_type: str, text: str, request: gr.Request | None = None):
    token = _resolve_token(token, request)
    if not project_id or not dimension_key or not text or not text.strip():
        return "Select a product and enter note text.", dimension_notes_from_ui(token, project_id, dimension_key), ""
    with SessionLocal() as db:
        try:
            user = get_authenticated_user(db, token)
            create_note(db, user, UUID(project_id), note_type.lower(), text.strip(), [dimension_key])
        except (AuthenticationError, ValueError) as exc:
            return str(exc), "", ""
    return "Added to this dimension.", dimension_notes_from_ui(token, project_id, dimension_key), ""


def save_comparator_from_ui(token: str, project_id: str | None, dataset_id: str | None, purpose: str, scope: str, request: gr.Request | None = None):
    token = _resolve_token(token, request)
    if not project_id or not dataset_id:
        return "Select a product and comparator first.", None
    with SessionLocal() as db:
        try:
            user = get_authenticated_user(db, token)
            snapshot = select_comparator(db, user, UUID(project_id), UUID(dataset_id), purpose, scope)
        except (AuthenticationError, ValueError) as exc:
            return str(exc), None
    return "Comparator selection saved as a frozen snapshot. Previous snapshots remain unchanged.", str(snapshot.id)


def preview_upload_from_ui(token: str | None, files, manifest_file, request: gr.Request | None = None):
    token = _resolve_token(token, request)
    with SessionLocal() as db:
        try:
            user = get_authenticated_user(db, token)
            batch, report = preview_upload(db, user, files, manifest_file)
        except (AuthenticationError, ValueError) as exc:
            return str(exc), "", None
    return f"Preview ready: {report['records']} records from {report['files']} files. Review before publishing.", json.dumps(report, ensure_ascii=False, indent=2), str(batch.id)


def publish_upload_from_ui(token: str | None, batch_id: str | None, request: gr.Request | None = None):
    token = _resolve_token(token, request)
    if not batch_id:
        return "Preview an upload before publishing.", ""
    with SessionLocal() as db:
        try:
            user = get_authenticated_user(db, token)
            report = publish_upload(db, user, UUID(batch_id))
        except (AuthenticationError, AuthorizationError, ValueError) as exc:
            return str(exc), ""
    return f"Published {report['records']} records from {report['files']} files.", json.dumps(report, ensure_ascii=False, indent=2)


def _hypotheses(db, project_id: str) -> list[Hypothesis]:
    return list(db.query(Hypothesis).filter(Hypothesis.project_id == UUID(project_id)).order_by(Hypothesis.kind, Hypothesis.created_at))


def _hypothesis_text(items: list[Hypothesis]) -> str:
    return "\n".join(f"[{item.kind}] {item.statement} | impact: {item.impact_if_wrong} | evidence: {item.evidence_strength} | status: {item.workflow_status}" for item in items) or "No hypotheses yet."


def _notes_text(items) -> str:
    return "\n".join(f"[{item.note_type}] {item.text}" for item in items) or "No notes yet."


MAX_BACKLOG_ROWS = 16


def show_next_row_from_ui(current_visible: int | None):
    count = min((current_visible or 1) + 1, MAX_BACKLOG_ROWS)
    return count, *(gr.update(visible=(i < count)) for i in range(MAX_BACKLOG_ROWS))


def update_relations_from_ui(token: str | None, project_id: str | None, request: gr.Request | None = None):
    token = _resolve_token(token, request)
    if not project_id:
        return gr.update(choices=[]), gr.update(choices=[]), "No hypotheses yet."
    with SessionLocal() as db:
        try:
            user = get_authenticated_user(db, token)
            get_project(db, user, UUID(project_id))
            all_hyps = list(db.scalars(
                select(Hypothesis)
                .where(Hypothesis.project_id == UUID(project_id))
                .order_by(Hypothesis.kind, Hypothesis.created_at)
            ))
        except (AuthenticationError, AuthorizationError, ValueError):
            return gr.update(choices=[]), gr.update(choices=[]), "Session expired."
    choices = [(f"[{h.kind}] {h.statement[:80]}", str(h.id)) for h in all_hyps]
    return gr.update(choices=choices), gr.update(choices=choices), _hypothesis_text(all_hyps)


def save_backlog_row_from_ui(
    token: str | None,
    project_id: str | None,
    dimension_key: str,
    assumption_text: str,
    question_text: str,
    hypothesis_text: str,
    note_id: str | None,
    hyp_id: str | None,
    hyp_rev: int | None,
    request: gr.Request | None = None,
):
    token = _resolve_token(token, request)
    if not project_id:
        return "Select a product first.", note_id, hyp_id, hyp_rev

    with SessionLocal() as db:
        try:
            user = get_authenticated_user(db, token)
            project = get_project(db, user, UUID(project_id))

            clean_dim = (dimension_key or "conversational").strip()
            clean_assumption = (assumption_text or "").strip()
            clean_question = (question_text or "").strip()
            clean_hypothesis = (hypothesis_text or "").strip()

            if not clean_assumption and not clean_question and not clean_hypothesis:
                return "Row is empty. Enter an assumption, question, or hypothesis.", note_id, hyp_id, hyp_rev

            primary_note = None
            if note_id:
                existing_note = db.get(Note, UUID(note_id))
                if existing_note and existing_note.project_id == project.id:
                    primary_note = existing_note
                    if existing_note.note_type == "assumption" and clean_assumption:
                        existing_note.text = clean_assumption
                    elif existing_note.note_type == "question" and clean_question:
                        existing_note.text = clean_question
                    db.execute(delete(NoteDimension).where(NoteDimension.note_id == existing_note.id))
                    db.add(NoteDimension(note_id=existing_note.id, dimension_key=clean_dim))

            if not primary_note:
                if clean_assumption:
                    primary_note = Note(project_id=project.id, note_type="assumption", text=clean_assumption)
                    db.add(primary_note)
                    db.flush()
                    db.add(NoteDimension(note_id=primary_note.id, dimension_key=clean_dim))
                elif clean_question:
                    primary_note = Note(project_id=project.id, note_type="question", text=clean_question)
                    db.add(primary_note)
                    db.flush()
                    db.add(NoteDimension(note_id=primary_note.id, dimension_key=clean_dim))

            # If user also filled the counterpart column that didn't exist before:
            if primary_note and primary_note.note_type == "question" and clean_assumption:
                # Add assumption note as well if not already present
                existing_a = db.scalar(select(Note).where(Note.project_id == project.id, Note.note_type == "assumption", Note.text == clean_assumption))
                if not existing_a:
                    extra_a = Note(project_id=project.id, note_type="assumption", text=clean_assumption)
                    db.add(extra_a)
                    db.flush()
                    db.add(NoteDimension(note_id=extra_a.id, dimension_key=clean_dim))
            elif primary_note and primary_note.note_type == "assumption" and clean_question:
                existing_q = db.scalar(select(Note).where(Note.project_id == project.id, Note.note_type == "question", Note.text == clean_question))
                if not existing_q:
                    extra_q = Note(project_id=project.id, note_type="question", text=clean_question)
                    db.add(extra_q)
                    db.flush()
                    db.add(NoteDimension(note_id=extra_q.id, dimension_key=clean_dim))

            saved_hyp_id = hyp_id
            saved_hyp_rev = hyp_rev

            if clean_hypothesis:
                if hyp_id and hyp_rev is not None:
                    existing_hyp = db.get(Hypothesis, UUID(hyp_id))
                    if existing_hyp and existing_hyp.project_id == project.id:
                        existing_hyp.statement = clean_hypothesis
                        existing_hyp.revision += 1
                        saved_hyp_rev = existing_hyp.revision
                        db.execute(delete(HypothesisDimension).where(HypothesisDimension.hypothesis_id == existing_hyp.id))
                        db.add(HypothesisDimension(hypothesis_id=existing_hyp.id, dimension_key=clean_dim))
                        if primary_note:
                            exists = db.scalar(select(HypothesisSource).where(HypothesisSource.hypothesis_id == existing_hyp.id, HypothesisSource.note_id == primary_note.id))
                            if not exists:
                                db.add(HypothesisSource(hypothesis_id=existing_hyp.id, note_id=primary_note.id))
                else:
                    new_hyp = Hypothesis(
                        project_id=project.id,
                        kind="supporting",
                        statement=clean_hypothesis,
                        value_link=f"Supports {clean_dim} dimension",
                        priority_risk=0.0,
                        priority_evidence=0.0,
                        revision=1,
                    )
                    db.add(new_hyp)
                    db.flush()
                    db.add(HypothesisDimension(hypothesis_id=new_hyp.id, dimension_key=clean_dim))
                    if primary_note:
                        db.add(HypothesisSource(hypothesis_id=new_hyp.id, note_id=primary_note.id))
                    saved_hyp_id = str(new_hyp.id)
                    saved_hyp_rev = new_hyp.revision

            db.commit()
            msg = "Row saved: notes and hypothesis updated." if clean_hypothesis else "Row saved: notes updated."
            return (
                msg,
                str(primary_note.id) if primary_note else note_id,
                saved_hyp_id,
                saved_hyp_rev,
            )
        except (AuthenticationError, AuthorizationError, ValueError, RevisionConflict) as exc:
            return str(exc), note_id, hyp_id, hyp_rev


def load_backlog_table_from_ui(
    token: str | None,
    project_id: str | None,
    request: gr.Request | None = None,
):
    token = _resolve_token(token, request)
    empty_slot = (
        gr.update(visible=False),
        gr.update(value="conversational"),
        "",
        "",
        "",
        None,
        None,
        None,
    )
    if not project_id:
        row_0 = (gr.update(visible=True), gr.update(value="conversational"), "", "", "", None, None, None)
        slots = [row_0] + [empty_slot for _ in range(MAX_BACKLOG_ROWS - 1)]
        flat = [val for slot in slots for val in slot]
        return (*flat, 1, "No hypotheses yet.", gr.update(choices=[]), gr.update(choices=[]))

    with SessionLocal() as db:
        try:
            user = get_authenticated_user(db, token)
            project = get_project(db, user, UUID(project_id))

            notes = list(db.scalars(
                select(Note)
                .where(Note.project_id == project.id, Note.note_type.in_(["assumption", "question"]))
                .order_by(Note.created_at)
            ))
            note_dims = {}
            if notes:
                for nd in db.execute(select(NoteDimension.note_id, NoteDimension.dimension_key).where(NoteDimension.note_id.in_([n.id for n in notes]))).all():
                    note_dims[nd[0]] = nd[1]

            hypotheses = list(db.scalars(
                select(Hypothesis)
                .where(Hypothesis.project_id == project.id, Hypothesis.kind == "supporting")
                .order_by(Hypothesis.created_at)
            ))
            hyp_dims = {}
            if hypotheses:
                for hd in db.execute(select(HypothesisDimension.hypothesis_id, HypothesisDimension.dimension_key).where(HypothesisDimension.hypothesis_id.in_([h.id for h in hypotheses]))).all():
                    hyp_dims[hd[0]] = hd[1]

            hyp_sources = list(db.scalars(
                select(HypothesisSource)
                .where(HypothesisSource.hypothesis_id.in_([h.id for h in hypotheses]))
            )) if hypotheses else []
            note_to_hyp = {hs.note_id: hs.hypothesis_id for hs in hyp_sources if hs.note_id}
            hyp_by_id = {h.id: h for h in hypotheses}

            rows = []
            used_hyp_ids = set()

            for note in notes:
                dim = note_dims.get(note.id, "conversational")
                a_text = note.text if note.note_type == "assumption" else ""
                q_text = note.text if note.note_type == "question" else ""

                h_text = ""
                h_id = None
                h_rev = None

                if note.id in note_to_hyp:
                    matched_hyp = hyp_by_id.get(note_to_hyp[note.id])
                    if matched_hyp:
                        h_text = matched_hyp.statement
                        h_id = str(matched_hyp.id)
                        h_rev = matched_hyp.revision
                        used_hyp_ids.add(matched_hyp.id)
                        dim = hyp_dims.get(matched_hyp.id, dim)

                rows.append({
                    "dim": dim,
                    "assumption": a_text,
                    "question": q_text,
                    "hypothesis": h_text,
                    "note_id": str(note.id),
                    "hyp_id": h_id,
                    "hyp_rev": h_rev,
                })

            for hyp in hypotheses:
                if hyp.id not in used_hyp_ids:
                    dim = hyp_dims.get(hyp.id, "conversational")
                    rows.append({
                        "dim": dim,
                        "assumption": "",
                        "question": "",
                        "hypothesis": hyp.statement,
                        "note_id": None,
                        "hyp_id": str(hyp.id),
                        "hyp_rev": hyp.revision,
                    })

            slots = []
            m = len(rows)
            for i in range(MAX_BACKLOG_ROWS):
                if i < m:
                    r = rows[i]
                    slots.append((
                        gr.update(visible=True),
                        gr.update(value=r["dim"]),
                        r["assumption"],
                        r["question"],
                        r["hypothesis"],
                        r["note_id"],
                        r["hyp_id"],
                        r["hyp_rev"],
                    ))
                elif i == m:
                    slots.append((
                        gr.update(visible=True),
                        gr.update(value="conversational"),
                        "",
                        "",
                        "",
                        None,
                        None,
                        None,
                    ))
                else:
                    slots.append(empty_slot)

            visible_count = min(m + 1, MAX_BACKLOG_ROWS)
            flat = [val for slot in slots for val in slot]

            all_hyps = list(db.scalars(
                select(Hypothesis)
                .where(Hypothesis.project_id == project.id)
                .order_by(Hypothesis.kind, Hypothesis.created_at)
            ))
            choices = [(f"[{h.kind}] {h.statement[:80]}", str(h.id)) for h in all_hyps]
            hyps_text = _hypothesis_text(all_hyps)

            return (*flat, visible_count, hyps_text, gr.update(choices=choices), gr.update(choices=choices))
        except (AuthenticationError, AuthorizationError, ValueError):
            row_0 = (gr.update(visible=True), gr.update(value="conversational"), "", "", "", None, None, None)
            slots = [row_0] + [empty_slot for _ in range(MAX_BACKLOG_ROWS - 1)]
            flat = [val for slot in slots for val in slot]
            return (*flat, 1, "Unable to load backlog.", gr.update(choices=[]), gr.update(choices=[]))


def backlog_columns_from_ui(token: str | None, project_id: str | None, request: gr.Request | None = None):
    token = _resolve_token(token, request)
    if not project_id:
        return gr.update(choices=[]), gr.update(choices=[]), "No assumptions yet.", "No questions yet."
    with SessionLocal() as db:
        try:
            user = get_authenticated_user(db, token)
            get_project(db, user, UUID(project_id))
            notes = list_notes(db, user, UUID(project_id))
        except AuthenticationError:
            return gr.update(choices=[]), gr.update(choices=[]), "Session expired.", "Session expired."
    assumptions = [(f"{index}. {note.text[:100]}", str(note.id)) for index, note in enumerate((item for item in notes if item.note_type == "assumption"), start=1)]
    questions = [(f"{index}. {note.text[:100]}", str(note.id)) for index, note in enumerate((item for item in notes if item.note_type == "question"), start=1)]
    assumptions_text = "\n".join(label for label, _ in assumptions) or "No assumptions yet."
    questions_text = "\n".join(label for label, _ in questions) or "No questions yet."
    return gr.update(choices=assumptions), gr.update(choices=questions), assumptions_text, questions_text


def derive_hypothesis_from_note(token: str | None, note_id: str | None, request: gr.Request | None = None):
    token = _resolve_token(token, request)
    if not note_id:
        return "Select an assumption or question first.", gr.update()
    with SessionLocal() as db:
        try:
            user = get_authenticated_user(db, token)
            note = db.get(Note, UUID(note_id))
            if note is None:
                raise ValueError("Note not found")
            get_project(db, user, note.project_id)
        except (AuthenticationError, ValueError, AuthorizationError) as exc:
            return str(exc), gr.update()
    prefill = f"Derived from {note.note_type}: {note.text}"
    return prefill, gr.update(value=note_id)


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
        return "Select a product first.", "No notes yet."
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
        return "observation", "", None, []
    with SessionLocal() as db:
        try:
            user = get_authenticated_user(db, token)
            note = db.get(Note, UUID(note_id))
            if note is None:
                raise ValueError("Note not found")
            get_project(db, user, note.project_id)
            linked = [item.dimension_key for item in db.query(NoteDimension).filter_by(note_id=note.id).all()]
        except (AuthenticationError, ValueError, AuthorizationError) as exc:
            return str(exc), "", None, []
    titles = [definition["title"] for definition in DEFAULT_DIMENSIONS if definition["key"] in linked]
    return note.note_type, note.text, note.revision, titles


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
        return "Select a product first.", "", gr.update(choices=[])
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
        return "Select a product and two hypotheses."
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
        return "Select a product and primary hypothesis first.", None, None
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
        return "Select a product to see the workshop checklist."
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
        return "Select a product to see priority guidance."
    with SessionLocal() as db:
        try:
            user = get_authenticated_user(db, token)
            return priority_guidance(db, user, UUID(project_id))
        except AuthenticationError:
            return "Session expired."


PLACEMENT_SLOTS = 10


def _ranking_items(ids, statements, risks, evidences):
    items = []
    for index in range(len(ids)):
        if not ids[index]:
            continue
        risk = risks[index] if risks[index] is not None else 0.0
        evidence = evidences[index] if evidences[index] is not None else 0.0
        priority = risk + (10 - evidence)
        items.append({"index": index, "statement": statements[index], "risk": risk, "evidence": evidence, "priority": priority})
    items.sort(key=lambda item: (-item["priority"], item["index"]))
    return items


def ranked_backlog_from_ui(*args):
    slot_count = len(args) // 4
    ids = args[0:slot_count]
    statements = args[slot_count:slot_count * 2]
    risks = args[slot_count * 2:slot_count * 3]
    evidences = args[slot_count * 3:slot_count * 4]
    items = _ranking_items(ids, statements, risks, evidences)
    if not items:
        return "No supporting hypotheses to rank yet.", go.Figure()
    lines = ["Backlog ranking (risk + (10 - evidence); ties keep creation order)"]
    for rank, item in enumerate(items, start=1):
        lines.append(f"{rank}. [risk {item['risk']:.1f} | evidence {item['evidence']:.1f}] {item['statement']}")
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=[item["evidence"] for item in items], y=[item["risk"] for item in items], mode="markers+text", text=[f"H{rank}" for rank, _ in enumerate(items, start=1)], textposition="top center", customdata=[item["statement"] for item in items], hovertemplate="%{customdata}<br>risk %{y:.1f} | evidence %{x:.1f}<extra></extra>", marker={"size": 12, "color": "#1f77b4"}))
    fig.update_layout(xaxis={"title": "Evidence provided", "range": [0, 10]}, yaxis={"title": "Risk to project", "range": [0, 10]}, title="Risk versus evidence matrix")
    return "\n".join(lines), fig


def save_placement_from_ui(token: str | None, hypothesis_id: str | None, revision: int | None, risk, evidence, request: gr.Request | None = None):
    token = _resolve_token(token, request)
    if not hypothesis_id or revision is None:
        return gr.update(), revision
    try:
        with SessionLocal() as db:
            user = get_authenticated_user(db, token)
            hypothesis = set_placement(db, user, UUID(hypothesis_id), revision, risk, evidence)
            return gr.update(), hypothesis.revision
    except (AuthenticationError, AuthorizationError, RevisionConflict, ValueError) as exc:
        return gr.update(value=f"Placement save failed: {exc}"), revision


def load_placements_from_ui(token: str | None, project_id: str | None, request: gr.Request | None = None):
    token = _resolve_token(token, request)
    hypotheses = []
    if project_id:
        with SessionLocal() as db:
            try:
                user = get_authenticated_user(db, token)
                get_project(db, user, UUID(project_id))
                hypotheses = list(db.scalars(select(Hypothesis).where(Hypothesis.project_id == UUID(project_id), Hypothesis.kind == "supporting").order_by(Hypothesis.created_at)))[:PLACEMENT_SLOTS]
            except (AuthenticationError, ValueError, AuthorizationError):
                hypotheses = []
    outputs = []
    for index in range(PLACEMENT_SLOTS):
        if index < len(hypotheses):
            hypothesis = hypotheses[index]
            outputs.extend([
                gr.update(visible=True, label=f"H{index + 1}", open=False),
                hypothesis.statement,
                hypothesis.priority_risk,
                hypothesis.priority_evidence,
                str(hypothesis.id),
                hypothesis.revision,
            ])
        else:
            outputs.extend([gr.update(visible=False, label=f"H{index + 1}", open=False), "", 0.0, 0.0, None, None])
    ranking, fig = ranked_backlog_from_ui(*[output for slot in [(hypotheses[index].id if index < len(hypotheses) else None, hypotheses[index].statement if index < len(hypotheses) else "", hypotheses[index].priority_risk if index < len(hypotheses) else 0.0, hypotheses[index].priority_evidence if index < len(hypotheses) else 0.0) for index in range(PLACEMENT_SLOTS)] for output in slot])
    return (*outputs, ranking, fig)


def export_project_from_ui(token: str | None, project_id: str | None, request: gr.Request | None = None):
    token = _resolve_token(token, request)
    if not project_id:
        return "Select a product before exporting.", None, None, None
    with SessionLocal() as db:
        try:
            user = get_authenticated_user(db, token)
            json_path, markdown_path, pdf_path = write_export_files(db, user, UUID(project_id))
        except (AuthenticationError, ValueError) as exc:
            return str(exc), None, None, None
    return "Exports generated.", json_path, markdown_path, pdf_path


def summary_preview_from_ui(token: str | None, project_id: str | None, request: gr.Request | None = None):
    token = _resolve_token(token, request)
    if not project_id:
        return "Select a product to view its summary."
    with SessionLocal() as db:
        try:
            user = get_authenticated_user(db, token)
            return export_project_markdown(db, user, UUID(project_id))
        except (AuthenticationError, ValueError) as exc:
            return str(exc)


def save_risk_reflection_from_ui(token: str | None, project_id: str | None, score, entry: str, behavior: str, affected: str, consequence: str, safeguard: str, uncertainty: str, request: gr.Request | None = None):
    token = _resolve_token(token, request)
    if not project_id:
        return "Select a product first."
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
        return "Select a product first."
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
        return "No products yet."
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
    return f"Team account '{team.alias}' created. Share the password securely and do not store it in product content."


def delete_product_from_ui(token: str | None, project_id: str | None, confirm: bool, request: gr.Request | None = None):
    token = _resolve_token(token, request)
    if not project_id:
        return "Select a product to delete.", gr.update()
    with SessionLocal() as db:
        try:
            user = get_authenticated_user(db, token)
            delete_project(db, user, UUID(project_id), confirm)
            choices = [(item.product_name, str(item.id)) for item in list_projects(db, user)]
            next_value = choices[0][1] if choices else None
        except (AuthenticationError, AuthorizationError, ValueError) as exc:
            return str(exc), gr.update()
    return "Product and its editable content were deleted.", gr.update(choices=choices, value=next_value)


def section_context(section: str, language: str = "en") -> str:
    descriptions = load_catalog(language)["sections"]
    return descriptions.get(section, descriptions["Project Setup"])
