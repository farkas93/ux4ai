import json
from datetime import timedelta
from uuid import UUID

import pytest
from sqlalchemy import select

from aipm_toolkit.auth import AuthorizationError, RevisionConflict, hash_password
from aipm_toolkit.experiment_services import save_reflection
from aipm_toolkit.export_services import build_project_export, export_project_markdown
from aipm_toolkit.hypothesis_services import create_hypothesis
from aipm_toolkit.improvement_services import QUESTIONS, classify_loop, list_loops, save_loop
from aipm_toolkit.lifecycle_services import delete_project
from aipm_toolkit.models import (
    Course,
    Hypothesis,
    HypothesisSource,
    ImprovementLoop,
    ProjectEvent,
    Role,
    SafetyHypothesisLink,
    Team,
    User,
)
from aipm_toolkit.safety_services import CHECKPOINTS, get_safety, safety_result, save_safety
from aipm_toolkit.services import create_project
from aipm_toolkit.ui import callbacks as cb_mod
from aipm_toolkit.ui import safety_callbacks


def project_for(db, alias):
    course = Course(name=f"Course {alias}")
    db.add(course)
    db.flush()
    team = Team(course_id=course.id, alias=alias)
    db.add(team)
    db.flush()
    user = User(username=alias, password_hash=hash_password("P" * 16), role=Role.TEAM.value, team_id=team.id)
    db.add(user)
    db.commit()
    return user, create_project(db, user, alias)


def rows(coverage="clearly_specified", maturity="planned"):
    return [{"key": key, "coverage": coverage, "maturity": maturity, "evidence": f"Test plan for {key}"} for key in CHECKPOINTS]


def data(name, **overrides):
    result = {
        "name": name,
        "answers": {key: {"answer": "unknown", "explanation": ""} for key in QUESTIONS},
        "status": "intended", "scopes": ["prompts"], "recursion_scope": "product_behavior",
        "release_approval": "unspecified", "approval_boundary": "", "success_checks": "", "rollback": "",
    }
    result.update(overrides)
    return result


def test_safety_unknown_is_a_range_but_not_addressed_is_zero(db):
    partial = rows("not_addressed")
    partial[0]["coverage"] = "unknown"
    partial[1]["coverage"] = None
    partial[2]["coverage"] = "clearly_specified"
    partial[2]["maturity"] = "tested"
    result = safety_result(partial, "Disclosure of retrieved information")
    assert result == {"score": None, "range": (0.8, 2.5), "incomplete": 2, "tested": 1,
                      "critical_risk": "Disclosure of retrieved information"}
    complete = safety_result(rows("not_addressed"))
    assert complete["score"] == 0
    assert complete["incomplete"] == 0


def test_safety_reloads_with_revision_and_history(db):
    user, project = project_for(db, "safety-team")
    assessment = save_safety(db, user, project.id, None, rows(), "Unauthorized data disclosure")
    persisted, saved_rows = get_safety(db, user, project.id)
    assert persisted.critical_risk == "Unauthorized data disclosure"
    assert saved_rows[0]["coverage"] == "clearly_specified"
    with pytest.raises(RevisionConflict):
        save_safety(db, user, project.id, None, rows(), "Stale")
    updated = save_safety(db, user, project.id, assessment.revision, rows("partly_specified"), "New risk")
    assert updated.revision == 2
    assert db.scalar(select(ProjectEvent).where(ProjectEvent.event_type == "safety.updated")) is not None


def test_loop_levels_are_gated_by_capabilities_and_release_boundary():
    values = {key: "yes" for key in QUESTIONS}
    assert classify_loop(values, "human", "baseline/regression", "rollback", "human reviews releases")["level"] == 4
    assert classify_loop(values, "bounded_automatic", "baseline/regression", "rollback", "bounded approval")["level"] == 5
    assert classify_loop(values, "bounded_automatic", "baseline/regression", "", "bounded approval")["level"] == 3
    values["evaluate"] = "partly"
    assert classify_loop(values, "human", "baseline/regression", "rollback")["level"] == 3
    values["evaluate"] = "unknown"
    provisional = classify_loop(values, "human", "baseline/regression", "rollback")
    assert provisional["level"] == 3 and provisional["possible_level"] == 4 and provisional["provisional"]


def test_multiple_loops_reload_and_are_project_scoped(db, monkeypatch):
    user, project = project_for(db, "loop-team")
    user2, _other = project_for(db, "other-team")
    observation = data("Summarize failed support chats")
    observation["answers"]["observe"]["answer"] = "yes"
    observation["answers"]["observe"]["explanation"] = "Summaries reviewed by the team"
    first = save_loop(db, user, project.id, None, None, observation)
    with pytest.raises(ValueError, match="already has a learning loop"):
        save_loop(db, user, project.id, None, None, data("Review prompt regressions"))
    # Preserve additional loops from before the single-loop teaching flow.
    second = ImprovementLoop(project_id=project.id, name="Legacy extra loop", created_at=first.created_at + timedelta(seconds=1))
    db.add(second)
    db.commit()
    assert len(list_loops(db, user, project.id)) == 2
    monkeypatch.setattr(safety_callbacks, "SessionLocal", lambda: db)
    monkeypatch.setattr(safety_callbacks, "get_authenticated_user", lambda _db, _token: user)
    assert safety_callbacks.load_primary_loop_ui("token", str(project.id))[0] == str(first.id)
    assert len(build_project_export(db, user, project.id)["improvement_loops"]) == 2
    with pytest.raises(ValueError, match="first saved loop"):
        save_loop(db, user, project.id, second.id, second.revision, data("Can't edit old loop"))
    assert json.loads(first.capabilities_json)["observe"]["answer"] == "yes"
    assert classify_loop({key: item["answer"] for key, item in json.loads(first.capabilities_json).items()}, first.release_approval, first.success_checks, first.rollback)["level"] == 1
    with pytest.raises(RevisionConflict):
        save_loop(db, user, project.id, first.id, None, observation)
    with pytest.raises(AuthorizationError):
        list_loops(db, user2, project.id)
    observation["status"] = "implemented"
    saved = save_loop(db, user, project.id, first.id, first.revision, observation)
    assert saved.revision == 2
    assert second.status == "intended"


def test_safety_question_develops_in_backlog_and_legacy_hypothesis_survives(db, monkeypatch):
    user, project = project_for(db, "hyp-safety")
    monkeypatch.setattr(safety_callbacks, "SessionLocal", lambda: db)
    monkeypatch.setattr(safety_callbacks, "get_authenticated_user", lambda _db, _token: user)
    status, visible, cleared = safety_callbacks.add_learning_note_ui("token", str(project.id), "safety", "harms", "Question", "Could retrieval disclose another user's data?")
    assert "Backlog Creator" in status and "disclose" in visible and cleared == ""
    monkeypatch.setattr(cb_mod, "SessionLocal", lambda: db)
    monkeypatch.setattr(cb_mod, "get_authenticated_user", lambda _db, _token: user)
    backlog = cb_mod.load_backlog_table_from_ui("token", str(project.id))
    assert backlog[1] == "AI Safety · Harms"
    assert backlog[2]["value"] is None  # Safety is independent of product dimensions.
    assert backlog[4] == "Could retrieval disclose another user's data?"
    saved, note_id, hyp_id, _revision = cb_mod.save_backlog_row_from_ui("token", str(project.id), None, "", backlog[4], "If retrieval leaks, users lose trust", backlog[8], None, None)
    assert "saved" in saved
    assert db.get(Hypothesis, UUID(hyp_id)).statement == "If retrieval leaks, users lose trust"
    assert db.scalar(select(HypothesisSource).where(HypothesisSource.hypothesis_id == UUID(hyp_id))).note_id == UUID(note_id)
    assert cb_mod.load_backlog_table_from_ui("token", str(project.id))[1] == "AI Safety · Harms"
    saved, _, _, new_revision = cb_mod.save_backlog_row_from_ui("token", str(project.id), None, "", "Could retrieval expose another user's records?", "If retrieval is restricted, exposure decreases", note_id, hyp_id, _revision)
    assert "saved" in saved and new_revision > _revision
    assert "Could retrieval expose another user's records?" in safety_callbacks.learning_notes_ui("token", str(project.id), "safety", "harms")
    assert "data?" not in safety_callbacks.learning_notes_ui("token", str(project.id), "safety", "controls")
    assert "preserved" in cb_mod.archive_backlog_row_from_ui("token", str(project.id), note_id, hyp_id)
    assert safety_callbacks.learning_notes_ui("token", str(project.id), "safety", "harms") == "No questions or assumptions yet."

    legacy = create_hypothesis(db, user, project.id, "Existing safety hypothesis")
    db.add(SafetyHypothesisLink(hypothesis_id=legacy.id, checkpoint_key="harms"))
    db.commit()
    save_safety(db, user, project.id, None, rows(), "Data leakage")
    save_loop(db, user, project.id, None, None, data("Improve prompt failure handling"))
    save_reflection(db, user, project.id, "adversarial_risk", "Legacy concern")
    document = build_project_export(db, user, project.id)
    assert document["safety_assessment"]["critical_risk"] == "Data leakage"
    assert len(document["safety_assessment"]["checkpoints"]) == 6
    assert document["improvement_loops"][0]["name"] == "Improve prompt failure handling"
    assert document["safety_hypothesis_links"][0]["checkpoint_key"] == "harms"
    assert document["notes"][0]["origin_section"] == "safety"
    assert document["reflections"][0]["content"] == "Legacy concern"
    markdown = export_project_markdown(db, user, project.id)
    assert "AI Safety (design coverage" not in markdown
    assert "Self-Improvement (course-specific classification)" not in markdown
    assert "Level 5" not in markdown


def test_assessment_can_add_question_and_backlog_loads_it(db, monkeypatch):
    user, project = project_for(db, "assessment-add")
    monkeypatch.setattr(cb_mod, "SessionLocal", lambda: db)
    monkeypatch.setattr(cb_mod, "get_authenticated_user", lambda _db, _token: user)
    status, visible, cleared = cb_mod.add_dimension_note_from_ui("token", str(project.id), "autonomy", "Question", "Can users intervene?")
    assert status == "Added to this dimension."
    assert "Can users intervene?" in visible and cleared == ""
    loaded = cb_mod.load_backlog_table_from_ui("token", str(project.id))
    assert loaded[1] == "Assessment"
    assert loaded[4] == "Can users intervene?"
    assert loaded[-1] == 1


def test_callbacks_reload_safety_and_loop_per_selected_project(db, monkeypatch):
    user, project = project_for(db, "reload-new")
    second = create_project(db, user, "Second product")
    monkeypatch.setattr(safety_callbacks, "SessionLocal", lambda: db)
    monkeypatch.setattr(safety_callbacks, "get_authenticated_user", lambda _db, _token: user)
    safety_values = [value for row in rows() for value in (row["coverage"], row["maturity"], row["evidence"])]
    status, revision, _card = safety_callbacks.save_safety_ui("token", str(project.id), None, *safety_values, "Risk")
    assert "saved" in status.lower()
    assert safety_callbacks.load_safety_ui("token", str(project.id))[-2] == revision
    assert safety_callbacks.load_safety_ui("token", str(second.id))[-2] is None

    values = ["Review support chats", *[item for _ in range(5) for item in ("unknown", "Not yet measured")]]
    status, selected_id, loop_revision = safety_callbacks.save_primary_loop_ui("token", str(project.id), None, None, *values)
    assert "saved" in status.lower() and loop_revision == 1
    assert safety_callbacks.load_primary_loop_ui("token", str(project.id))[0] == selected_id
    assert safety_callbacks.load_primary_loop_ui("token", str(second.id))[0] is None
    assert safety_callbacks.load_primary_loop_ui("token", str(project.id))[1] == "Review support chats"
    loop = db.get(ImprovementLoop, UUID(selected_id))
    loop.status = "implemented"
    loop.approval_boundary = "A human approves release"
    db.commit()
    _, _, loop_revision = safety_callbacks.save_primary_loop_ui("token", str(project.id), selected_id, loop_revision, *values)
    persisted_loop = db.get(ImprovementLoop, UUID(selected_id))
    assert persisted_loop.status == "implemented"
    assert persisted_loop.approval_boundary == "A human approves release"
    added, listed, _ = safety_callbacks.add_learning_note_ui("token", str(project.id), "self_improvement", None, "Assumption", "Summaries reveal repeat failures")
    assert "Backlog Creator" in added and "repeat failures" in listed
    monkeypatch.setattr(cb_mod, "SessionLocal", lambda: db)
    monkeypatch.setattr(cb_mod, "get_authenticated_user", lambda _db, _token: user)
    backlog = cb_mod.load_backlog_table_from_ui("token", str(project.id))
    assert backlog[1] == "Self-Improvement" and backlog[2]["value"] is None
    assert backlog[3] == "Summaries reveal repeat failures"
    assert safety_callbacks.learning_notes_ui("token", str(second.id), "self_improvement") == "No questions or assumptions yet."


def test_product_deletion_cleans_up_safety_and_loops(db):
    user, project = project_for(db, "remove-safety-product")
    save_safety(db, user, project.id, None, rows(), "Unknown use")
    save_loop(db, user, project.id, None, None, data("Review incident patterns"))
    delete_project(db, user, project.id, confirm=True)
    from aipm_toolkit.models import ImprovementLoop, SafetyAssessment, SafetyCheckpoint

    assert db.scalar(select(SafetyAssessment).where(SafetyAssessment.project_id == project.id)) is None
    assert db.scalar(select(SafetyCheckpoint)) is None
    assert db.scalar(select(ImprovementLoop).where(ImprovementLoop.project_id == project.id)) is None
