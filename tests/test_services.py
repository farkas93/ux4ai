import pytest

from aipm_toolkit.auth import AuthorizationError, RevisionConflict, hash_password
from aipm_toolkit.models import Role, Team, User
from aipm_toolkit.services import (
    create_project,
    get_main_hypothesis,
    update_project,
    validate_figma_url,
)

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


def test_brief_and_main_hypothesis_persist(db):
    user = team_user(db)
    project = create_project(db, user, "Prototype")
    updated = update_project(
        db,
        user,
        project.id,
        project.revision,
        short_description="A workshop prototype",
        target_user="Student teams",
        product_type="Plugin",
    )
    main = get_main_hypothesis(db, user, project.id)
    from aipm_toolkit.services import update_main_hypothesis
    update_main_hypothesis(db, user, project.id, main.revision, "Teams will identify a better next test.")
    assert updated.short_description == "A workshop prototype"
    assert get_main_hypothesis(db, user, project.id).statement == "Teams will identify a better next test."


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


def test_figma_url_validation(db):
    assert validate_figma_url("https://www.figma.com/file/example")
    with pytest.raises(ValueError):
        validate_figma_url("javascript:alert(1)")


def test_project_setup_updates_main_hypothesis_with_supporting_hypotheses(db, monkeypatch):
    from aipm_toolkit.hypothesis_services import create_hypothesis
    from aipm_toolkit.ui import callbacks as cb_mod

    user = team_user(db, "hyp_rev_test")
    project = create_project(db, user, "Project With Multiple Hypotheses")

    # Add supporting hypothesis with higher revision
    h_supp = create_hypothesis(db, user, project.id, "Supporting claim text", kind="supporting")
    h_supp.revision = 7
    db.commit()

    monkeypatch.setattr(cb_mod, "SessionLocal", lambda: db)
    monkeypatch.setattr(cb_mod, "get_authenticated_user", lambda _db, _token: user)

    # load_project_from_ui must load the MAIN hypothesis statement, not the supporting one
    loaded = cb_mod.load_project_from_ui("token", str(project.id))
    main_stmt = loaded[4]
    assert main_stmt != "Supporting claim text"

    # save_project_from_ui must update the main hypothesis cleanly even if revision drifted
    msg, _rev = cb_mod.save_project_from_ui(
        "token",
        str(project.id),
        revision=1,
        product_type="Native",
        description="Updated description",
        target_user="Users",
        job="Job",
        problem="Problem",
        hypothesis="Updated Main Hypothesis Statement",
        figma_url="https://figma.com/file/test",
    )

    assert "saved" in msg.lower()
    main_db = get_main_hypothesis(db, user, project.id)
    assert main_db.statement == "Updated Main Hypothesis Statement"
