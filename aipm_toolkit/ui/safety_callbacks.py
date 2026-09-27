"""Gradio adapters for safety and individual improvement-loop assessments."""

import json
from uuid import UUID

import gradio as gr

from ..auth import AuthenticationError, AuthorizationError, RevisionConflict, get_authenticated_user
from ..db import SessionLocal
from ..hypothesis_services import create_note, list_notes
from ..improvement_services import QUESTIONS, classify_loop, list_loops, save_loop
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


def _loop_fields(loop):
    if loop is None:
        return ("", *[val for _ in QUESTIONS for val in (None, "")], "intended", [], "product_behavior", "unspecified", "", "", "", None, loop_card(None))
    answers = json.loads(loop.capabilities_json or "{}")
    return (loop.name, *[val for key in QUESTIONS for val in (answers.get(key, {}).get("answer"), answers.get(key, {}).get("explanation", ""))],
            loop.status, json.loads(loop.change_scopes_json or "[]"), loop.recursion_scope, loop.release_approval,
            loop.approval_boundary, loop.success_checks, loop.rollback, loop.revision, loop_card(loop))


def loop_card(loop):
    if loop is None:
        return "### Name a specific improvement loop to classify it.\nCourse-specific classification—not a standardized benchmark."
    answers = {key: value.get("answer") for key, value in json.loads(loop.capabilities_json or "{}").items()}
    result = classify_loop(answers, loop.release_approval, loop.success_checks, loop.rollback, loop.approval_boundary)
    possible = (f"; provisional potential: level {result['possible_level']} (unresolved prerequisites)" if result["provisional"] else "")
    return (f"### Level {result['level']} — {result['name']}{possible}\n"
            f"**Status:** {loop.status.title()} · **Scope:** {', '.join(json.loads(loop.change_scopes_json or '[]')) or 'Not specified'} "
            f"· **Release approval:** {loop.release_approval.replace('_', ' ').title()}\n\n"
            "Course-specific classification—not a standardized benchmark. Status is the team's claim, not certification.")


def live_loop_card(*values):
    name = (values[0] or "").strip()
    if not name:
        return loop_card(None)
    answers = {key: (values[1 + i * 2] if (values[2 + i * 2] or "").strip() else "unknown") for i, key in enumerate(QUESTIONS)}
    offset = 1 + 2 * len(QUESTIONS)
    status, scopes, _recursion, release, boundary, checks, rollback = values[offset:offset + 7]
    result = classify_loop(answers, release or "unspecified", checks or "", rollback or "", boundary or "")
    possible = f" · Provisional potential: level {result['possible_level']} (unresolved prerequisites)" if result["provisional"] else ""
    return (f"### Level {result['level']} — {result['name']}{possible}\n"
            f"**Status:** {(status or 'intended').title()} · **Scope:** {', '.join(scopes or []) or 'Not specified'} "
            f"· **Release approval:** {(release or 'unspecified').replace('_', ' ').title()}\n\n"
            "Course-specific classification—not a standardized benchmark. Status is the team's claim, not certification.")


def save_primary_loop_ui(token, project_id, loop_id, revision, *values, request: gr.Request | None = None):
    if not project_id:
        return "Select a product first.", loop_id, revision, loop_card(None)
    name = values[0]
    answers = {key: {"answer": values[1 + i * 2], "explanation": values[2 + i * 2]} for i, key in enumerate(QUESTIONS)}
    offset = 1 + len(QUESTIONS) * 2
    status, scopes, recursion, release, boundary, checks, rollback = values[offset:offset + 7]
    data = {"name": name, "answers": answers, "status": status, "scopes": scopes or [], "recursion_scope": recursion,
            "release_approval": release, "approval_boundary": boundary or "", "success_checks": checks or "", "rollback": rollback or ""}
    with SessionLocal() as db:
        try:
            actor = get_authenticated_user(db, _resolve_token(token, request))
            loop = save_loop(db, actor, UUID(project_id), UUID(loop_id) if loop_id else None, revision, data)
            return "Improvement loop saved.", str(loop.id), loop.revision, loop_card(loop)
        except (AuthenticationError, AuthorizationError, RevisionConflict, ValueError) as exc:
            return str(exc), loop_id, revision, "Save failed. Review your answers and retry."


def load_primary_loop_ui(token, project_id, request: gr.Request | None = None):
    if not project_id:
        return None, *_loop_fields(None)
    with SessionLocal() as db:
        try:
            actor = get_authenticated_user(db, _resolve_token(token, request))
            loops = list_loops(db, actor, UUID(project_id))
            first = loops[0] if loops else None
            return str(first.id) if first else None, *_loop_fields(first)
        except (AuthenticationError, AuthorizationError, ValueError):
            return None, *_loop_fields(None)
