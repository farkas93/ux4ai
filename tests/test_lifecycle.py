import pytest

from aipm_toolkit.auth import AuthorizationError, hash_password
from aipm_toolkit.lifecycle_services import delete_project
from aipm_toolkit.models import Course, Role, Team, User
from aipm_toolkit.services import create_project


def setup_course(db):
    course = Course(name="Lifecycle course")
    db.add(course)
    db.flush()
    team_a = Team(course_id=course.id, alias="lifecycle-a")
    team_b = Team(course_id=course.id, alias="lifecycle-b")
    db.add_all([team_a, team_b])
    db.flush()
    instructor = User(username="lifecycle-instructor", password_hash=hash_password("P" * 16), role=Role.INSTRUCTOR.value)
    owner = User(username="lifecycle-a", password_hash=hash_password("Q" * 16), role=Role.TEAM.value, team_id=team_a.id)
    other = User(username="lifecycle-b", password_hash=hash_password("R" * 16), role=Role.TEAM.value, team_id=team_b.id)
    db.add_all([instructor, owner, other])
    db.commit()
    return instructor, owner, other


def test_owner_and_instructor_can_delete_with_confirmation(db):
    instructor, owner, _ = setup_course(db)
    project = create_project(db, owner, "Owned product")
    with pytest.raises(ValueError):
        delete_project(db, owner, project.id, False)
    delete_project(db, owner, project.id, True)
    assert db.get(type(project), project.id) is None
    second = create_project(db, owner, "Instructor target")
    delete_project(db, instructor, second.id, True)
    assert db.get(type(second), second.id) is None


def test_other_team_cannot_delete(db):
    _, owner, other = setup_course(db)
    project = create_project(db, owner, "Protected product")
    with pytest.raises(AuthorizationError):
        delete_project(db, other, project.id, True)
