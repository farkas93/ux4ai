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
