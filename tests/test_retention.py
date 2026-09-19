import pytest

from aipm_toolkit.auth import AuthorizationError, hash_password
from aipm_toolkit.models import Course, Role, Team, User
from aipm_toolkit.retention_services import delete_project_as_instructor, update_course_retention
from aipm_toolkit.services import create_project


def setup_course(db):
    course = Course(name="Retention course")
    db.add(course)
    db.flush()
    team = Team(course_id=course.id, alias="retention-team")
    db.add(team)
    db.flush()
    instructor = User(username="retention-instructor", password_hash=hash_password("P" * 16), role=Role.INSTRUCTOR.value)
    team_user = User(username="retention-team", password_hash=hash_password("Q" * 16), role=Role.TEAM.value, team_id=team.id)
    db.add_all([instructor, team_user])
    db.commit()
    return course, instructor, team_user


def test_instructor_can_update_retention_and_delete_project(db):
    course, instructor, team_user = setup_course(db)
    updated = update_course_retention(db, instructor, course.name, 365, "Delete after one year")
    assert updated.retention_days == 365
    project = create_project(db, team_user, "Delete me")
    delete_project_as_instructor(db, instructor, project.id, True)
    assert db.get(type(project), project.id) is None


def test_team_and_unconfirmed_deletion_are_rejected(db):
    _course, instructor, team_user = setup_course(db)
    project = create_project(db, team_user, "Keep me")
    with pytest.raises(AuthorizationError):
        delete_project_as_instructor(db, team_user, project.id, True)
    with pytest.raises(ValueError):
        delete_project_as_instructor(db, instructor, project.id, False)
