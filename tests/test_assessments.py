import pytest

from aipm_toolkit.assessment_services import (
    ensure_scale_definitions,
    get_project_estimates,
    save_project_estimates,
)
from aipm_toolkit.auth import RevisionConflict, hash_password
from aipm_toolkit.dimensions import DIMENSION_KEYS
from aipm_toolkit.models import Course, Role, Team, User
from aipm_toolkit.services import create_project


def team_user(db):
    course = Course(name="Assessment course")
    db.add(course)
    db.flush()
    team = Team(course_id=course.id, alias="assessment-team")
    db.add(team)
    db.flush()
    user = User(username="assessment-team", password_hash=hash_password("P" * 16), role=Role.TEAM.value, team_id=team.id)
    db.add(user)
    db.commit()
    return user


def test_unknown_and_zero_are_distinct(db):
    user = team_user(db)
    project = create_project(db, user, "Assessment prototype")
    ensure_scale_definitions(db)
    values = [
        {"dimension_key": key, "status": "unknown", "score": 4.0, "revision": 1}
        for key in DIMENSION_KEYS
    ]
    values[0].update(status="estimated", score=0.0, basis="intended_design")
    save_project_estimates(db, user, project.id, values)
    estimates = {estimate.dimension_key: estimate for estimate in get_project_estimates(db, user, project.id)}
    assert estimates["conversational"].score == 0.0
    assert estimates["specialization"].score is None
    assert estimates["specialization"].status == "unknown"


def test_invalid_score_and_stale_revision_are_rejected(db):
    user = team_user(db)
    project = create_project(db, user, "Assessment prototype")
    ensure_scale_definitions(db)
    values = [{"dimension_key": key, "status": "estimated", "score": 2.55, "revision": 1} for key in DIMENSION_KEYS]
    with pytest.raises(ValueError):
        save_project_estimates(db, user, project.id, values)
    valid = [{"dimension_key": key, "status": "unknown", "score": None, "revision": 1} for key in DIMENSION_KEYS]
    save_project_estimates(db, user, project.id, valid)
    with pytest.raises(RevisionConflict):
        save_project_estimates(db, user, project.id, valid)


def test_assessments_can_be_saved_repeatedly_with_returned_revisions(db):
    user = team_user(db)
    project = create_project(db, user, "Assessment prototype")
    ensure_scale_definitions(db)
    first = [{"dimension_key": key, "status": "unknown", "score": None, "revision": 1} for key in DIMENSION_KEYS]
    saved = save_project_estimates(db, user, project.id, first)
    saved_revisions = [item.revision for item in saved]
    second = [{"dimension_key": key, "status": "unknown", "score": None, "revision": revision} for key, revision in zip(DIMENSION_KEYS, saved_revisions)]
    second[0]["rationale"] = "Updated after discussion"
    updated = save_project_estimates(db, user, project.id, second)
    assert updated[0].revision > saved_revisions[0]
    assert updated[0].rationale == "Updated after discussion"


def test_assessment_scores_and_reasoning_persist_and_reload_cleanly(db, monkeypatch):
    user = team_user(db)
    project = create_project(db, user, "Reload Prototype")
    ensure_scale_definitions(db)

    from aipm_toolkit.ui import callbacks as cb_mod
    monkeypatch.setattr(cb_mod, "SessionLocal", lambda: db)
    monkeypatch.setattr(cb_mod, "get_authenticated_user", lambda _db, _token: user)

    # Initial load for a fresh product returns 2.5 default
    initial = cb_mod.load_estimates_from_ui("token", str(project.id))
    assert initial[0] == 2.5
    assert initial[1] == ""

    # Save custom scores and reasoning notes
    custom_scores = [4.1, "Custom note 1", 1.3, "Custom note 2", 3.7, "Custom note 3", 5.0, "Custom note 4", 0.2, "Custom note 5"]
    msg, revs = cb_mod.save_estimates_from_ui(
        "token",
        str(project.id),
        initial[-1],  # revisions list
        *custom_scores,
    )
    assert "saved" in msg.lower()
    assert len(revs) == 5

    # Reload estimates: must return the exact custom scores and notes, NOT 2.5!
    reloaded = cb_mod.load_estimates_from_ui("token", str(project.id))
    assert reloaded[0] == 4.1
    assert reloaded[1] == "Custom note 1"
    assert reloaded[2] == 1.3
    assert reloaded[3] == "Custom note 2"
    assert reloaded[4] == 3.7
    assert reloaded[5] == "Custom note 3"
    assert reloaded[6] == 5.0
    assert reloaded[7] == "Custom note 4"
    assert reloaded[8] == 0.2
    assert reloaded[9] == "Custom note 5"
    assert reloaded[10] == revs
