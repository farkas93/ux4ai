import pytest

from aipm_toolkit.auth import AuthorizationError, RevisionConflict, hash_password
from aipm_toolkit.models import Role, Team, User
from aipm_toolkit.services import create_project, get_main_hypothesis, update_project

TEST_PASSWORD = "P" * 16


def team_user(db, alias="a"):
    from aipm_toolkit.models import Course
    course = Course(name=f"Course {alias}")
    db.add(course)
    db.flush()
    team = Team(course_id=course.id, alias=alias)
    db.add(team)
    db.flush()
    user = User(username=f"team-{alias}", password_hash=hash_password(TEST_PASSWORD), role=Role.TEAM.value, team_id=team.id)
    db.add(user)
    db.commit()
    return user


def test_project_has_one_authoritative_main_hypothesis(db):
    user = team_user(db)
    project = create_project(db, user, "Prototype")
    assert get_main_hypothesis(db, user, project.id).kind == "main"


def test_forged_project_id_is_denied(db):
    user_a = team_user(db, "a")
    user_b = team_user(db, "b")
    project_b = create_project(db, user_b, "Private")
    with pytest.raises(AuthorizationError):
        update_project(db, user_a, project_b.id, project_b.revision, product_name="Forged")


def test_stale_revision_is_rejected(db):
    user = team_user(db)
    project = create_project(db, user, "Prototype")
    stale_revision = project.revision
    update_project(db, user, project.id, stale_revision, product_name="Updated")
    with pytest.raises(RevisionConflict):
        update_project(db, user, project.id, stale_revision, product_name="Stale")
