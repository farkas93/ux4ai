"""Gradio adapters for safety and individual improvement-loop assessments."""

import json
from uuid import UUID

import gradio as gr

from ..auth import AuthenticationError, AuthorizationError, RevisionConflict, get_authenticated_user
from ..db import SessionLocal
from ..hypothesis_services import create_note, list_notes
from ..improvement_services import QUESTIONS, list_loops, save_loop
from ..models import ImprovementLoop
from ..safety_services import CHECKPOINTS, get_safety, safety_result, save_safety
from .callbacks import _resolve_token


def safety_card(rows, risk):
    result = safety_result(rows, risk)
    coverage = (f"{result['score']:.1f}/5" if result["score"] is not None else
                f"{result['range'][0]:.1f}–{result['range'][1]:.1f}/5 possible ({result['incomplete']} incomplete)")
    return (f"### Safety design coverage: {coverage}\n"
            f"**Evidence: {result['tested']} of 6 checkpoints marked Tested** (team claim; testing adequacy is not certified).\n\n"
            f"**Critical unresolved risk:** {result['critical_risk'] or 'Not specified.'}")


def _rows_from_flat(values):
    return [{"key": key, "coverage": values[i * 3], "maturity": values[i * 3 + 1], "evidence": values[i * 3 + 2] or ""}
            for i, key in enumerate(CHECKPOINTS)]


def live_safety_card(*args):
    return safety_card(_rows_from_flat(args[:-1]), args[-1] or "")


def load_safety_ui(token, project_id, request: gr.Request | None = None):
    blank = [value for _ in CHECKPOINTS for value in (None, None, "")]
    if not project_id:
        return (*blank, "", None, safety_card(_rows_from_flat(blank), ""))
    with SessionLocal() as db:
        try:
            actor = get_authenticated_user(db, _resolve_token(token, request))
            assessment, rows = get_safety(db, actor, UUID(project_id))
            flat = [value for row in rows for value in (row["coverage"], row["maturity"], row["evidence"])]
            risk = assessment.critical_risk if assessment else ""
            return (*flat, risk, assessment.revision if assessment else None, safety_card(rows, risk))
        except (AuthenticationError, AuthorizationError, ValueError):
            return (*blank, "", None, safety_card(_rows_from_flat(blank), ""))


def save_safety_ui(token, project_id, revision, *values, request: gr.Request | None = None):
    if not project_id:
        return "Select a product first.", revision, live_safety_card(*values)
    rows, risk = _rows_from_flat(values[:-1]), values[-1] or ""
    with SessionLocal() as db:
        try:
            actor = get_authenticated_user(db, _resolve_token(token, request))
            assessment = save_safety(db, actor, UUID(project_id), revision, rows, risk)
            return "AI safety assessment saved.", assessment.revision, safety_card(rows, risk)
        except (AuthenticationError, AuthorizationError, RevisionConflict, ValueError) as exc:
            return str(exc), revision, safety_card(rows, risk)


def learning_notes_ui(token, project_id, section, key=None, request: gr.Request | None = None):
    if not project_id:
        return "No questions or assumptions yet."
    with SessionLocal() as db:
        try:
            actor = get_authenticated_user(db, _resolve_token(token, request))
            notes = [note for note in list_notes(db, actor, UUID(project_id)) if note.origin_section == section and note.origin_key == key and note.note_type in {"question", "assumption"}]
            return "\n".join(f"[{note.note_type}] {note.text}" for note in notes) or "No questions or assumptions yet."
        except (AuthenticationError, AuthorizationError, ValueError) as exc:
            return str(exc)


def add_learning_note_ui(token, project_id, section, key, note_type, text, request: gr.Request | None = None):
    if section not in {"safety", "self_improvement"} or (section == "safety" and key not in CHECKPOINTS) or (section == "self_improvement" and key is not None):
        return "Select a learning area first.", gr.update(), text
    if not project_id or not (text or "").strip():
        return "Select a product and write a question or assumption.", learning_notes_ui(token, project_id, section, key, request=request), text
    with SessionLocal() as db:
        try:
            actor = get_authenticated_user(db, _resolve_token(token, request))
            create_note(db, actor, UUID(project_id), (note_type or "").lower(), text, origin_section=section, origin_key=key)
        except (AuthenticationError, AuthorizationError, ValueError) as exc:
            return str(exc), gr.update(), text
    return "Added. Develop it into a hypothesis in Backlog Creator.", learning_notes_ui(token, project_id, section, key, request=request), ""


def load_primary_loop_ui(token, project_id, request: gr.Request | None = None):
    empty = (None, "", *[value for _ in list(QUESTIONS.values())[:5] for value in (None, "")], None)
    if not project_id:
        return empty
    with SessionLocal() as db:
        try:
            actor = get_authenticated_user(db, _resolve_token(token, request))
            loops = list_loops(db, actor, UUID(project_id))
            first = loops[0] if loops else None
            if first is None:
                return empty
            saved = json.loads(first.capabilities_json or "{}")
            return (str(first.id), first.name,
                    *[value for key in list(QUESTIONS)[:5] for value in (saved.get(key, {}).get("answer"), saved.get(key, {}).get("explanation", ""))],
                    first.revision)
        except (AuthenticationError, AuthorizationError, ValueError):
            return empty


def save_primary_loop_ui(token, project_id, loop_id, revision, *values, request: gr.Request | None = None):
    if not project_id:
        return "Select a product first.", loop_id, revision
    name = values[0]
    data_answers = {key: {"answer": values[1 + i * 2], "explanation": values[2 + i * 2]} for i, key in enumerate(list(QUESTIONS)[:5])}
    with SessionLocal() as db:
        try:
            actor = get_authenticated_user(db, _resolve_token(token, request))
            existing = db.get(ImprovementLoop, UUID(loop_id)) if loop_id else None
            old_answers = json.loads(existing.capabilities_json or "{}") if existing else {}
            for key in list(QUESTIONS)[5:]:
                data_answers[key] = old_answers.get(key, {"answer": "unknown", "explanation": ""})
            data = {
                "name": name,
                "answers": data_answers,
                "status": existing.status if existing else "intended",
                "scopes": json.loads(existing.change_scopes_json or "[]") if existing else [],
                "recursion_scope": existing.recursion_scope if existing else "product_behavior",
                "release_approval": existing.release_approval if existing else "unspecified",
                "approval_boundary": existing.approval_boundary if existing else "",
                "success_checks": existing.success_checks if existing else "",
                "rollback": existing.rollback if existing else "",
            }
            loop = save_loop(db, actor, UUID(project_id), UUID(loop_id) if loop_id else None, revision, data)
            return "Learning loop saved.", str(loop.id), loop.revision
        except (AuthenticationError, AuthorizationError, RevisionConflict, ValueError) as exc:
            return str(exc), loop_id, revision
