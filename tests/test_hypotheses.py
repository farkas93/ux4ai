import pytest

from aipm_toolkit.auth import AuthorizationError, RevisionConflict, hash_password
from aipm_toolkit.hypothesis_services import (
    add_relation,
    create_hypothesis,
    create_note,
    update_hypothesis,
)
from aipm_toolkit.models import Course, Hypothesis, Role, Team, User
from aipm_toolkit.services import create_project


def users_and_project(db, alias="hypothesis-team"):
    course = Course(name=f"Course {alias}")
    db.add(course)
    db.flush()
    team = Team(course_id=course.id, alias=alias)
    db.add(team)
    db.flush()
    user = User(username=alias, password_hash=hash_password("P" * 16), role=Role.TEAM.value, team_id=team.id)
    db.add(user)
    db.commit()
    return user, create_project(db, user, "Hypothesis prototype")


def test_note_to_hypothesis_preserves_provenance(db):
    user, project = users_and_project(db)
    note = create_note(db, user, project.id, "observation", "Users need confidence before approving an action.", ["explainability"])
    hypothesis = create_hypothesis(db, user, project.id, "If we show evidence, users will approve more confidently.", value_link="Supports the main value hypothesis.", note_id=note.id)
    assert hypothesis.kind == "supporting"
    assert db.get(Hypothesis, hypothesis.id).statement.startswith("If we show")


def test_relationships_reject_cross_project_and_dependency_cycles(db):
    user_a, project_a = users_and_project(db, "a")
    user_b, project_b = users_and_project(db, "b")
    one = create_hypothesis(db, user_a, project_a.id, "One")
    two = create_hypothesis(db, user_a, project_a.id, "Two")
    foreign = create_hypothesis(db, user_b, project_b.id, "Foreign")
    add_relation(db, user_a, project_a.id, "depends_on", one.id, two.id)
    with pytest.raises(ValueError, match="cycles"):
        add_relation(db, user_a, project_a.id, "depends_on", two.id, one.id)
    with pytest.raises(AuthorizationError):
        add_relation(db, user_a, project_a.id, "contributes_to", one.id, foreign.id)


def test_evidence_rationale_and_revision_are_enforced(db):
    user, project = users_and_project(db)
    hypothesis = create_hypothesis(db, user, project.id, "A testable claim")
    with pytest.raises(ValueError):
        update_hypothesis(db, user, hypothesis.id, hypothesis.revision, evidence_strength="strong")
    updated = update_hypothesis(db, user, hypothesis.id, hypothesis.revision, evidence_strength="strong", evidence_rationale="Observed in a prototype walkthrough.")
    assert updated.evidence_strength == "strong"
    with pytest.raises(RevisionConflict):
        update_hypothesis(db, user, hypothesis.id, hypothesis.revision - 1, statement="Stale")
