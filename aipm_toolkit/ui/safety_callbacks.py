"""Gradio adapters for safety and individual improvement-loop assessments."""

import json
from uuid import UUID

import gradio as gr

from ..auth import AuthenticationError, AuthorizationError, RevisionConflict, get_authenticated_user
from ..db import SessionLocal
from ..hypothesis_services import create_hypothesis
from ..improvement_services import QUESTIONS, classify_loop, list_loops, save_loop
from ..models import SafetyHypothesisLink
from ..project_history_services import record_project_event
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


def create_safety_hypothesis_ui(token, project_id, checkpoint_key, statement, request: gr.Request | None = None):
    if not project_id or checkpoint_key not in CHECKPOINTS or not (statement or "").strip():
        return "Select a product and write a testable hypothesis first.", statement
    with SessionLocal() as db:
        try:
            actor = get_authenticated_user(db, _resolve_token(token, request))
            hypothesis = create_hypothesis(db, actor, UUID(project_id), statement)
            db.add(SafetyHypothesisLink(hypothesis_id=hypothesis.id, checkpoint_key=checkpoint_key))
            record_project_event(db, actor, UUID(project_id), "safety.hypothesis_created", "hypothesis", hypothesis.id,
                                 f"Linked supporting hypothesis to Safety: {CHECKPOINTS[checkpoint_key][0]}", {"checkpoint": checkpoint_key, "statement": statement.strip()})
            db.commit()
            return "Supporting hypothesis created; find it in Backlog Creator.", ""
        except (AuthenticationError, AuthorizationError, ValueError) as exc:
            return str(exc), statement


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


def load_loop_choices_ui(token, project_id, request: gr.Request | None = None):
    if not project_id:
        return gr.update(choices=[], value=None), *_loop_fields(None)
    with SessionLocal() as db:
        try:
            actor = get_authenticated_user(db, _resolve_token(token, request))
            loops = list_loops(db, actor, UUID(project_id))
            selected = loops[0] if loops else None
            return gr.update(choices=[(loop.name, str(loop.id)) for loop in loops], value=str(selected.id) if selected else None), *_loop_fields(selected)
        except (AuthenticationError, AuthorizationError, ValueError):
            return gr.update(choices=[], value=None), *_loop_fields(None)


def load_loop_ui(token, project_id, loop_id, request: gr.Request | None = None):
    if not project_id or not loop_id:
        return _loop_fields(None)
    with SessionLocal() as db:
        try:
            actor = get_authenticated_user(db, _resolve_token(token, request))
            loop = next((item for item in list_loops(db, actor, UUID(project_id)) if str(item.id) == loop_id), None)
            return _loop_fields(loop)
        except (AuthenticationError, AuthorizationError, ValueError):
            return _loop_fields(None)


def save_loop_ui(token, project_id, loop_id, revision, *values, request: gr.Request | None = None):
    if not project_id:
        return "Select a product first.", gr.update(), revision, loop_card(None)
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
            choices = [(item.name, str(item.id)) for item in list_loops(db, actor, UUID(project_id))]
            return "Improvement loop saved.", gr.update(choices=choices, value=str(loop.id)), loop.revision, loop_card(loop)
        except (AuthenticationError, AuthorizationError, RevisionConflict, ValueError) as exc:
            return str(exc), gr.update(), revision, "Save failed. Review your answers and retry."


def blank_loop_ui():
    return gr.update(value=None), *_loop_fields(None)
