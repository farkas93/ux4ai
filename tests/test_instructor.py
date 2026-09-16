import json

import pytest

from aipm_toolkit.auth import AuthorizationError, hash_password
from aipm_toolkit.instructor_services import course_overview, import_baselines_as_instructor
from aipm_toolkit.models import Course, Role, Team, User
from aipm_toolkit.services import create_project


def setup_users(db):
    course = Course(name="Instructor course")
    db.add(course)
    db.flush()
    team = Team(course_id=course.id, alias="team-a")
    db.add(team)
    db.flush()
    instructor = User(username="instructor", password_hash=hash_password("P" * 16), role=Role.INSTRUCTOR.value)
    team_user = User(username="team-a", password_hash=hash_password("Q" * 16), role=Role.TEAM.value, team_id=team.id)
    db.add_all([instructor, team_user])
    db.commit()
    return instructor, team_user


def test_instructor_can_overview_but_team_cannot(db):
    instructor, team_user = setup_users(db)
    create_project(db, team_user, "Team product")
    assert course_overview(db, instructor)[0]["product_name"] == "Team product"
    with pytest.raises(AuthorizationError):
        course_overview(db, team_user)


def test_only_instructor_can_import_and_publish(db, tmp_path):
    instructor, team_user = setup_users(db)
    source = tmp_path / "product.json"
    source.write_text(json.dumps({"product_name": "Example", "scores": {key: 1 for key in ("conversational", "specialization", "autonomy", "accessibility", "explainability")}}), encoding="utf-8")
    report = import_baselines_as_instructor(db, instructor, str(tmp_path), "Cohort", True)
    assert report["records"] == 1
    with pytest.raises(AuthorizationError):
        import_baselines_as_instructor(db, team_user, str(tmp_path), "Other", False)
