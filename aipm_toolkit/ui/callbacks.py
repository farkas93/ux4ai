"""Callback functions for the AIPM Toolkit workspace.

These functions are intentionally free of Gradio layout code; they resolve the
authenticated actor from the request cookie and delegate to application
services.
"""

import json
from html import escape
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
from ..backlog_services import archive_backlog_entry
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
    SafetyHypothesisLink,
)
from ..priority_rules import (
    RANKING_RULE,
    hypothesis_header,
    priority_group_score,
    priority_score,
    test_first,
)
from ..project_history_services import list_project_events, record_project_event
from ..services import (
    create_project,
    get_main_hypothesis,
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
            try:
                hypothesis = get_main_hypothesis(db, user, project.id)
            except LookupError:
                hypothesis = None
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
    if not project_id:
        return "Select a product first.", revision
    with SessionLocal() as db:
        try:
            user = get_authenticated_user(db, token)
            updated_url = validate_figma_url(figma_url)
            project = get_project(db, user, UUID(project_id))
            before = {
                "product_type": project.product_type,
                "short_description": project.short_description,
                "target_user": project.target_user,
                "job_to_be_done": project.job_to_be_done,
                "current_problem": project.current_problem,
                "figma_url": project.figma_url,
            }
            try:
                old_hypothesis = get_main_hypothesis(db, user, project.id).statement
            except LookupError:
                old_hypothesis = ""
            target_rev = project.revision if (revision is None or revision != project.revision) else revision
            project = update_project(db, user, UUID(project_id), target_rev, product_type=product_type, short_description=description, target_user=target_user, job_to_be_done=job, current_problem=problem, figma_url=updated_url)
            try:
                main = get_main_hypothesis(db, user, project.id)
            except LookupError:
                main = None
            if main:
                update_main_hypothesis(db, user, project.id, main.revision, hypothesis)
            after = {
                "product_type": project.product_type,
                "short_description": project.short_description,
                "target_user": project.target_user,
                "job_to_be_done": project.job_to_be_done,
                "current_problem": project.current_problem,
                "figma_url": project.figma_url,
                "main_hypothesis": hypothesis.strip(),
            }
            before["main_hypothesis"] = old_hypothesis
            changed = {key: {"before": before[key], "after": after[key]} for key in before if before[key] != after[key]}
            if changed:
                record_project_event(db, user, project.id, "project_setup.updated", "project", project.id, "Updated project setup", changed)
                db.commit()
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


def save_estimates_from_ui(
    token: str,
    project_id: str | None,
    revisions: list[int] | None,
    s0: float = 2.5,
    r0: str = "",
    s1: float = 2.5,
    r1: str = "",
    s2: float = 2.5,
    r2: str = "",
    s3: float = 2.5,
    r3: str = "",
    s4: float = 2.5,
    r4: str = "",
    request: gr.Request | None = None,
):
    token = _resolve_token(token, request)
    if not project_id:
        return "Select a product before saving dimension assessments.", revisions or []
    revisions = revisions or [None] * len(DEFAULT_DIMENSIONS)
    scores = [s0, s1, s2, s3, s4]
    notes = [r0, r1, r2, r3, r4]
    records = []
    for index, definition in enumerate(DEFAULT_DIMENSIONS):
        score = scores[index] if index < len(scores) and scores[index] is not None else 2.5
        reasoning = notes[index] if index < len(notes) and notes[index] is not None else ""
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


def save_assessments_action(
    token: str,
    project_id: str | None,
    revisions: list[int] | None,
    s0: float = 2.5,
    r0: str = "",
    s1: float = 2.5,
    r1: str = "",
    s2: float = 2.5,
    r2: str = "",
    s3: float = 2.5,
    r3: str = "",
    s4: float = 2.5,
    r4: str = "",
    request: gr.Request | None = None,
):
    token = _resolve_token(token, request)
    status, new_revisions = save_estimates_from_ui(token, project_id, revisions, s0, r0, s1, r1, s2, r2, s3, r3, s4, r4, request=request)
    return status, new_revisions, not status.endswith("saved.")


def autosave_assessments_from_ui(
    token: str,
    project_id: str | None,
    revisions: list[int] | None,
    dirty: bool,
    s0: float = 2.5,
    r0: str = "",
    s1: float = 2.5,
    r1: str = "",
    s2: float = 2.5,
    r2: str = "",
    s3: float = 2.5,
    r3: str = "",
    s4: float = 2.5,
    r4: str = "",
    request: gr.Request | None = None,
):
    token = _resolve_token(token, request)
    if not dirty:
        return gr.update(), revisions or [], dirty
    status, new_revisions = save_estimates_from_ui(token, project_id, revisions, s0, r0, s1, r1, s2, r2, s3, r3, s4, r4, request=request)
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
    titles = [definition["title"] for definition in DEFAULT_DIMENSIONS]
    theta = titles + [titles[0]]
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
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"color": "#718096", "size": 11},
        legend={"orientation": "h", "y": -0.18},
        margin={"l": 70, "r": 70, "t": 30, "b": 55},
        height=340,
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
            record_project_event(
                db,
                user,
                UUID(project_id),
                "comparison.selected",
                "comparison_snapshot",
                snapshot.id,
                "Selected a historical comparator",
                {"dataset_id": str(dataset_id), "purpose": "task_comparator", "scope": "Direct comparison"},
            )
            db.commit()
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
            rows = db.execute(select(Note.note_type, Note.text).join(NoteDimension, NoteDimension.note_id == Note.id).where(Note.project_id == UUID(project_id), Note.archived_at.is_(None), NoteDimension.dimension_key == dimension_key).order_by(Note.created_at)).all()
        except AuthenticationError:
            return "Session expired."
    if not rows:
        return "No questions or assumptions for this dimension yet."
    return "\n".join(f"[{note_type}] {text}" for note_type, text in rows)


def project_history_from_ui(token: str | None, project_id: str | None, request: gr.Request | None = None):
    token = _resolve_token(token, request)
    if not project_id:
        return "Select a product to view its history."
    with SessionLocal() as db:
        try:
            user = get_authenticated_user(db, token)
            events = list_project_events(db, user, UUID(project_id))
        except (AuthenticationError, AuthorizationError, ValueError) as exc:
            return str(exc)
    if not events:
        return "No project history yet. Changes will appear here as the team works."
    lines = []
    for event, username in events:
        stamp = event.created_at.strftime("%Y-%m-%d %H:%M UTC") if event.created_at else "Time unavailable"
        actor_label = username or ("Former user" if event.actor_user_id else "System")
        try:
            details = json.loads(event.details_json or "{}")
        except json.JSONDecodeError:
            details = {}
        changed = []
        if event.event_type == "assessment.updated":
            before, after = details.get("before") or {}, details.get("after") or {}
            changed = [key.replace("_", " ") for key in after if before.get(key) != after.get(key)]
        elif event.event_type == "backlog.entry_saved":
            before, after = details.get("before") or {}, details.get("after") or {}
            changed = [key for key in ("assumption", "question", "hypothesis") if before.get(key, "") != after.get(key, "")]
        elif event.event_type == "backlog.entry_archived":
            before = details.get("before") or {}
            changed = [record.get("type", "hypothesis") for record in before.values() if isinstance(record, dict)]
        elif event.event_type == "dimension.assignment_normalized":
            before, after = details.get("before") or [], details.get("after") or []
            changed = [f"kept {after[0]} from {', '.join(before)}"] if after else []
        elif details and all(isinstance(value, dict) and {"before", "after"}.issubset(value) for value in details.values()):
            changed = [key.replace("_", " ") for key, value in details.items() if value["before"] != value["after"]]
        elif "before" in details and "after" in details:
            before, after = details["before"], details["after"]
            if isinstance(before, dict) and isinstance(after, dict):
                changed = [key.replace("_", " ") for key in after if before.get(key) != after.get(key)]
        detail_line = f"<p>Changed: {escape(', '.join(changed))}</p>" if changed else ""
        lines.append(f'<article class="toolkit-history-card"><small>{escape(stamp)} · {escape(actor_label)}</small><h3>{escape(event.summary)}</h3>{detail_line}</article>')
    return "".join(lines)


def add_dimension_note_from_ui(token: str | None, project_id: str | None, dimension_key: str, note_type: str, text: str, request: gr.Request | None = None):
    token = _resolve_token(token, request)
    if not project_id or not dimension_key or not text or not text.strip():
        return "Select a product and enter note text.", dimension_notes_from_ui(token, project_id, dimension_key), ""
    with SessionLocal() as db:
        try:
            user = get_authenticated_user(db, token)
            create_note(db, user, UUID(project_id), note_type.lower(), text.strip(), [dimension_key], origin_section="assessment")
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
            record_project_event(
                db,
                user,
                UUID(project_id),
                "comparison.selected",
                "comparison_snapshot",
                snapshot.id,
                "Selected a historical comparator",
                {"dataset_id": str(dataset_id), "purpose": purpose, "scope": scope},
            )
            db.commit()
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
    return list(db.query(Hypothesis).filter(Hypothesis.project_id == UUID(project_id), Hypothesis.archived_at.is_(None)).order_by(Hypothesis.kind, Hypothesis.created_at))


def _hypothesis_text(items: list[Hypothesis]) -> str:
    return "\n".join(f"[{item.kind}] {item.statement} | impact: {item.impact_if_wrong} | evidence: {item.evidence_strength} | status: {item.workflow_status}" for item in items) or "No hypotheses yet."


def _notes_text(items) -> str:
    return "\n".join(f"[{item.note_type}] {item.text}" for item in items) or "No notes yet."


MAX_BACKLOG_ROWS = 16


def show_next_row_from_ui(current_visible: int | None):
    count = min((current_visible or 0) + 1, MAX_BACKLOG_ROWS)
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
                .where(Hypothesis.project_id == UUID(project_id), Hypothesis.archived_at.is_(None))
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

            clean_dim = (dimension_key or "").strip()
            existing_note = db.get(Note, UUID(note_id)) if note_id else None
            legacy_safety = db.get(SafetyHypothesisLink, UUID(hyp_id)) if hyp_id else None
            if clean_dim not in {definition["key"] for definition in DEFAULT_DIMENSIONS} and clean_dim:
                raise ValueError("Select one valid product dimension")
            if not clean_dim and not (existing_note and existing_note.origin_section in {"safety", "self_improvement"}) and not legacy_safety:
                raise ValueError("Choose a product dimension for this entry")
            clean_assumption = (assumption_text or "").strip()
            clean_question = (question_text or "").strip()
            clean_hypothesis = (hypothesis_text or "").strip()

            if not clean_assumption and not clean_question and not clean_hypothesis:
                return "Row is empty. Enter an assumption, question, or hypothesis.", note_id, hyp_id, hyp_rev

            primary_note = None
            before = {"dimension": None, "assumption": "", "question": "", "hypothesis": ""}
            if note_id:
                if existing_note and existing_note.project_id == project.id and existing_note.archived_at is None:
                    primary_note = existing_note
                    old_dimensions = list(db.scalars(select(NoteDimension.dimension_key).where(NoteDimension.note_id == existing_note.id)))
                    before["dimension"] = old_dimensions[0] if old_dimensions else None
                    before[existing_note.note_type] = existing_note.text
                    original_text = existing_note.text
                    if existing_note.note_type == "assumption" and clean_assumption:
                        existing_note.text = clean_assumption
                    elif existing_note.note_type == "question" and clean_question:
                        existing_note.text = clean_question
                    if existing_note.text != original_text or old_dimensions != ([clean_dim] if clean_dim else []):
                        db.execute(delete(NoteDimension).where(NoteDimension.note_id == existing_note.id))
                        if clean_dim:
                            db.add(NoteDimension(note_id=existing_note.id, dimension_key=clean_dim))
                        existing_note.revision += 1
                else:
                    raise AuthorizationError("Backlog note not found")

            if not primary_note:
                if clean_assumption:
                    primary_note = Note(project_id=project.id, note_type="assumption", text=clean_assumption, origin_section="backlog")
                    db.add(primary_note)
                    db.flush()
                    db.add(NoteDimension(note_id=primary_note.id, dimension_key=clean_dim))
                elif clean_question:
                    primary_note = Note(project_id=project.id, note_type="question", text=clean_question, origin_section="backlog")
                    db.add(primary_note)
                    db.flush()
                    db.add(NoteDimension(note_id=primary_note.id, dimension_key=clean_dim))

            # If user also filled the counterpart column that didn't exist before:
            if primary_note and primary_note.note_type == "question" and clean_assumption:
                # Add assumption note as well if not already present
                existing_a = db.scalar(select(Note).where(Note.project_id == project.id, Note.note_type == "assumption", Note.text == clean_assumption, Note.archived_at.is_(None), Note.origin_section == primary_note.origin_section, Note.origin_key == primary_note.origin_key))
                if not existing_a:
                    extra_a = Note(project_id=project.id, note_type="assumption", text=clean_assumption, origin_section=primary_note.origin_section, origin_key=primary_note.origin_key)
                    db.add(extra_a)
                    db.flush()
                    if clean_dim:
                        db.add(NoteDimension(note_id=extra_a.id, dimension_key=clean_dim))
                else:
                    existing_dims = list(db.scalars(select(NoteDimension.dimension_key).where(NoteDimension.note_id == existing_a.id)))
                    if existing_dims != ([clean_dim] if clean_dim else []):
                        db.execute(delete(NoteDimension).where(NoteDimension.note_id == existing_a.id))
                        if clean_dim:
                            db.add(NoteDimension(note_id=existing_a.id, dimension_key=clean_dim))
                        existing_a.revision += 1
            elif primary_note and primary_note.note_type == "assumption" and clean_question:
                existing_q = db.scalar(select(Note).where(Note.project_id == project.id, Note.note_type == "question", Note.text == clean_question, Note.archived_at.is_(None), Note.origin_section == primary_note.origin_section, Note.origin_key == primary_note.origin_key))
                if not existing_q:
                    extra_q = Note(project_id=project.id, note_type="question", text=clean_question, origin_section=primary_note.origin_section, origin_key=primary_note.origin_key)
                    db.add(extra_q)
                    db.flush()
                    if clean_dim:
                        db.add(NoteDimension(note_id=extra_q.id, dimension_key=clean_dim))
                else:
                    existing_dims = list(db.scalars(select(NoteDimension.dimension_key).where(NoteDimension.note_id == existing_q.id)))
                    if existing_dims != ([clean_dim] if clean_dim else []):
                        db.execute(delete(NoteDimension).where(NoteDimension.note_id == existing_q.id))
                        if clean_dim:
                            db.add(NoteDimension(note_id=existing_q.id, dimension_key=clean_dim))
                        existing_q.revision += 1

            saved_hyp_id = hyp_id
            saved_hyp_rev = hyp_rev

            if clean_hypothesis:
                if hyp_id and hyp_rev is not None:
                    existing_hyp = db.get(Hypothesis, UUID(hyp_id))
                    if existing_hyp and existing_hyp.project_id == project.id and existing_hyp.archived_at is None:
                        if existing_hyp.revision != hyp_rev:
                            raise RevisionConflict("The hypothesis changed since it was loaded")
                        before["hypothesis"] = existing_hyp.statement
                        hyp_dimensions = list(db.scalars(select(HypothesisDimension.dimension_key).where(HypothesisDimension.hypothesis_id == existing_hyp.id)))
                        if hyp_dimensions:
                            before["dimension"] = hyp_dimensions[0]
                        if existing_hyp.statement != clean_hypothesis or hyp_dimensions != ([clean_dim] if clean_dim else []):
                            existing_hyp.statement = clean_hypothesis
                            existing_hyp.revision += 1
                            db.execute(delete(HypothesisDimension).where(HypothesisDimension.hypothesis_id == existing_hyp.id))
                            if clean_dim:
                                db.add(HypothesisDimension(hypothesis_id=existing_hyp.id, dimension_key=clean_dim))
                        saved_hyp_rev = existing_hyp.revision
                        if primary_note:
                            exists = db.scalar(select(HypothesisSource).where(HypothesisSource.hypothesis_id == existing_hyp.id, HypothesisSource.note_id == primary_note.id))
                            if not exists:
                                db.add(HypothesisSource(hypothesis_id=existing_hyp.id, note_id=primary_note.id))
                    else:
                        raise AuthorizationError("Supporting hypothesis not found")
                else:
                    new_hyp = Hypothesis(
                        project_id=project.id,
                        kind="supporting",
                        statement=clean_hypothesis,
                        value_link=f"Supports {clean_dim} dimension" if clean_dim else "Explores an open question or assumption",
                        priority_risk=0.0,
                        priority_evidence=0.0,
                        revision=1,
                    )
                    db.add(new_hyp)
                    db.flush()
                    before["hypothesis"] = ""
                    if clean_dim:
                        db.add(HypothesisDimension(hypothesis_id=new_hyp.id, dimension_key=clean_dim))
                    if primary_note:
                        db.add(HypothesisSource(hypothesis_id=new_hyp.id, note_id=primary_note.id))
                    saved_hyp_id = str(new_hyp.id)
                    saved_hyp_rev = new_hyp.revision

            area_label = clean_dim.replace("_", " ") if clean_dim else (
                f"AI Safety · {primary_note.origin_key}" if primary_note and primary_note.origin_section == "safety" else
                "Self-Improvement" if primary_note and primary_note.origin_section == "self_improvement" else
                "AI Safety" if legacy_safety else "Backlog Creator"
            )
            if before["dimension"] and before["dimension"] != clean_dim:
                event_summary = f"Moved backlog entry from {before['dimension'].replace('_', ' ')} to {area_label}"
            elif not note_id and not hyp_id:
                event_summary = f"Added backlog entry in {area_label}"
            else:
                event_summary = f"Updated backlog entry in {area_label}"
            after = {
                "dimension": clean_dim or None,
                "assumption": clean_assumption,
                "question": clean_question,
                "hypothesis": clean_hypothesis,
            }
            if before != after:
                record_project_event(
                    db,
                    user,
                    project.id,
                    "backlog.entry_saved",
                    "backlog_entry",
                    saved_hyp_id or (str(primary_note.id) if primary_note else None),
                    event_summary,
                    {"before": before, "after": after},
                )
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


def archive_backlog_row_from_ui(
    token: str | None,
    project_id: str | None,
    note_id: str | None,
    hyp_id: str | None,
    request: gr.Request | None = None,
):
    token = _resolve_token(token, request)
    if not project_id:
        return "Select a product first."
    try:
        note_uuid = UUID(note_id) if note_id else None
        hyp_uuid = UUID(hyp_id) if hyp_id else None
    except ValueError:
        return "Backlog entry not found. Reload the product and try again."
    with SessionLocal() as db:
        try:
            user = get_authenticated_user(db, token)
            archive_backlog_entry(db, user, UUID(project_id), note_uuid, hyp_uuid)
        except (AuthenticationError, AuthorizationError, ValueError) as exc:
            return str(exc)
    return "Removed from the active backlog. Its history and linked experiments are preserved."


def load_backlog_table_from_ui(
    token: str | None,
    project_id: str | None,
    request: gr.Request | None = None,
):
    token = _resolve_token(token, request)
    empty_slot = (
        gr.update(visible=False),
        "Backlog Creator",
        gr.update(value=None),
        "",
        "",
        "",
        gr.update(visible=False),
        gr.update(visible=False),
        None,
        None,
        None,
    )
    if not project_id:
        slots = [empty_slot for _ in range(MAX_BACKLOG_ROWS)]
        flat = [val for slot in slots for val in slot]
        return (*flat, 0)

    with SessionLocal() as db:
        try:
            user = get_authenticated_user(db, token)
            project = get_project(db, user, UUID(project_id))

            notes = list(db.scalars(
                select(Note)
                .where(Note.project_id == project.id, Note.note_type.in_(["assumption", "question"]), Note.archived_at.is_(None))
                .order_by(Note.created_at)
            ))
            note_dims = {}
            if notes:
                for nd in db.execute(select(NoteDimension.note_id, NoteDimension.dimension_key).where(NoteDimension.note_id.in_([n.id for n in notes]))).all():
                    note_dims[nd[0]] = nd[1]

            hypotheses = list(db.scalars(
                select(Hypothesis)
                .where(Hypothesis.project_id == project.id, Hypothesis.kind == "supporting", Hypothesis.archived_at.is_(None))
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
            legacy_safety_links = {link.hypothesis_id: link.checkpoint_key for link in db.scalars(select(SafetyHypothesisLink).where(SafetyHypothesisLink.hypothesis_id.in_([h.id for h in hypotheses])))} if hypotheses else {}

            rows = []
            used_hyp_ids = set()

            for note in notes:
                dim = note_dims.get(note.id)
                if note.origin_section == "safety":
                    source = f"AI Safety · {note.origin_key.title()}"
                elif note.origin_section == "self_improvement":
                    source = "Self-Improvement"
                else:
                    source = "Assessment" if note.origin_section == "assessment" else "Backlog Creator" if note.origin_section == "backlog" else "Earlier entry"
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
                    "source": source,
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
                    dim = hyp_dims.get(hyp.id)
                    rows.append({
                        "source": f"AI Safety · {legacy_safety_links[hyp.id].title()}" if hyp.id in legacy_safety_links else "Backlog Creator",
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
                        r["source"],
                        gr.update(value=r["dim"]),
                        r["assumption"],
                        r["question"],
                        r["hypothesis"],
                        gr.update(visible=bool(r["note_id"] or r["hyp_id"])),
                        gr.update(visible=False),
                        r["note_id"],
                        r["hyp_id"],
                        r["hyp_rev"],
                    ))
                else:
                    slots.append(empty_slot)

            visible_count = min(m, MAX_BACKLOG_ROWS)
            flat = [val for slot in slots for val in slot]
            return (*flat, visible_count)
        except (AuthenticationError, AuthorizationError, ValueError):
            slots = [empty_slot for _ in range(MAX_BACKLOG_ROWS)]
            flat = [val for slot in slots for val in slot]
            return (*flat, 0)


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
    empty_tuple = ("", "prototype_walkthrough", "", "", "", "", "", "", "", "", "", "planned", "", "", "", "", "undecided", None)
    if not experiment_id:
        return empty_tuple
    with SessionLocal() as db:
        try:
            user = get_authenticated_user(db, token)
            experiment = db.get(Experiment, UUID(experiment_id))
            if experiment is None:
                raise ValueError("Experiment not found")
            get_project(db, user, experiment.project_id)
        except (AuthenticationError, AuthorizationError, ValueError) as exc:
            return (str(exc), "prototype_walkthrough", "", "", "", "", "", "", "", "", "", "planned", "", "", "", "", "undecided", None)
    return (
        experiment.title,
        experiment.method,
        experiment.procedure,
        experiment.participants,
        experiment.comparison_baseline,
        experiment.metric,
        experiment.success_criterion,
        experiment.guardrail,
        experiment.resources,
        experiment.owner,
        experiment.planned_date or "",
        experiment.status,
        experiment.results,
        experiment.evidence_links,
        experiment.limitations,
        experiment.conclusion,
        experiment.resulting_decision,
        experiment.revision,
    )


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
        try:
            risk = float(risks[index]) if index < len(risks) and risks[index] is not None else 0.0
        except (ValueError, TypeError):
            risk = 0.0
        try:
            evidence = float(evidences[index]) if index < len(evidences) and evidences[index] is not None else 0.0
        except (ValueError, TypeError):
            evidence = 0.0
        priority = priority_score(risk, evidence)
        stmt = str(statements[index]) if index < len(statements) and statements[index] is not None else ""
        items.append({"index": index, "statement": stmt, "risk": risk, "evidence": evidence, "priority": priority, "test_first": test_first(risk, evidence)})
    items.sort(key=lambda item: (not item["test_first"], -item["priority"], item["index"]))
    return items


def ranked_backlog_from_ui(*args, sources=None):
    slot_count = len(args) // 4
    ids = args[0:slot_count]
    statements = args[slot_count:slot_count * 2]
    risks = args[slot_count * 2:slot_count * 3]
    evidences = args[slot_count * 3:slot_count * 4]
    items = _ranking_items(ids, statements, risks, evidences)
    lines = [f"<p>{escape(RANKING_RULE)}</p>"]
    if not items:
        lines.append("<p>No supporting hypotheses to rank yet.</p>")
    last_score, position = None, 0
    for index, item in enumerate(items):
        group_score = priority_group_score(item["risk"], item["evidence"])
        if group_score != last_score:
            position = index + 1
        last_score = group_score
        source = sources[item["index"]] if sources and item["index"] < len(sources) else ""
        reason = "High risk with limited evidence." if item["test_first"] else "Outside the Test first area; consider after higher-risk uncertainties."
        lines.append(
            f'<article class="toolkit-history-card"><small>TEST ORDER {position}</small>'
            f'<h3>H{item["index"] + 1} · {escape(item["statement"])}</h3>'
            f'<p><strong>Source question / assumption:</strong> {escape(source or "No linked question or assumption.")}</p>'
            f'<p>Risk if wrong: {item["risk"]:.1f}/10 · Evidence available: {item["evidence"]:.1f}/10</p>'
            f'<p>{reason}</p></article>'
        )
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=[item["evidence"] for item in items], y=[item["risk"] for item in items], mode="markers+text", text=[f"H{item['index'] + 1}" for item in items], textposition="top center", customdata=[item["statement"] for item in items], hovertemplate="%{text}: %{customdata}<br>risk %{y:.1f} | evidence %{x:.1f}<extra></extra>", marker={"size": 12, "color": "#1f77b4"}))
    fig.update_layout(xaxis={"title": "Evidence provided", "range": [0, 10]}, yaxis={"title": "Risk to project", "range": [0, 10]}, title="Risk versus evidence matrix")
    fig.add_shape(type="rect", x0=0, x1=5, y0=5, y1=10, fillcolor="rgba(20,184,166,0.12)", line={"width": 0}, layer="below")
    return "".join(lines), fig


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
    sources = {}
    if project_id:
        with SessionLocal() as db:
            try:
                user = get_authenticated_user(db, token)
                get_project(db, user, UUID(project_id))
                hypotheses = list(db.scalars(select(Hypothesis).where(Hypothesis.project_id == UUID(project_id), Hypothesis.kind == "supporting", Hypothesis.archived_at.is_(None)).order_by(Hypothesis.created_at, Hypothesis.id)))[:PLACEMENT_SLOTS]
                if hypotheses:
                    linked = db.execute(
                        select(HypothesisSource.hypothesis_id, Note.note_type, Note.text, Note.archived_at)
                        .join(Note, Note.id == HypothesisSource.note_id)
                        .where(HypothesisSource.hypothesis_id.in_([item.id for item in hypotheses]), Note.project_id == UUID(project_id))
                        .order_by(Note.created_at, Note.id)
                    ).all()
                    for hyp_id, note_type, note_text, archived in linked:
                        sources.setdefault(hyp_id, []).append(f"{note_type.title()}{' (archived)' if archived else ''}: {note_text}")
            except (AuthenticationError, ValueError, AuthorizationError):
                hypotheses = []
    outputs = []
    for index in range(PLACEMENT_SLOTS):
        if index < len(hypotheses):
            hypothesis = hypotheses[index]
            outputs.extend([
                gr.update(visible=True, label=hypothesis_header(index + 1, hypothesis.statement), open=False),
                hypothesis.statement,
                hypothesis.priority_risk,
                hypothesis.priority_evidence,
                str(hypothesis.id),
                hypothesis.revision,
                "\n".join(sources.get(hypothesis.id, [])),
            ])
        else:
            outputs.extend([gr.update(visible=False, label=f"H{index + 1}", open=False), "", 0.0, 0.0, None, None, ""])
    slot_ids = [str(hypotheses[i].id) if i < len(hypotheses) else None for i in range(PLACEMENT_SLOTS)]
    slot_statements = [hypotheses[i].statement if i < len(hypotheses) else "" for i in range(PLACEMENT_SLOTS)]
    slot_risks = [float(hypotheses[i].priority_risk) if i < len(hypotheses) else 0.0 for i in range(PLACEMENT_SLOTS)]
    slot_evidences = [float(hypotheses[i].priority_evidence) if i < len(hypotheses) else 0.0 for i in range(PLACEMENT_SLOTS)]
    ranking, fig = ranked_backlog_from_ui(*(slot_ids + slot_statements + slot_risks + slot_evidences), sources=["\n".join(sources.get(item.id, [])) for item in hypotheses])
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
