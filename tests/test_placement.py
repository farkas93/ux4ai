import pytest

from aipm_toolkit.auth import RevisionConflict, hash_password
from aipm_toolkit.hypothesis_services import create_hypothesis, set_placement
from aipm_toolkit.models import Course, Role, Team, User
from aipm_toolkit.services import create_project
from aipm_toolkit.ui.callbacks import ranked_backlog_from_ui


def user_project(db, alias="placement-team"):
    course = Course(name=f"Course {alias}")
    db.add(course)
    db.flush()
    team = Team(course_id=course.id, alias=alias)
    db.add(team)
    db.flush()
    user = User(username=alias, password_hash=hash_password("P" * 16), role=Role.TEAM.value, team_id=team.id)
    db.add(user)
    db.commit()
    return user, create_project(db, user, "Placement product")


def test_placement_validates_range_and_revision(db):
    user, project = user_project(db)
    hypothesis = create_hypothesis(db, user, project.id, "A claim")
    stale_revision = hypothesis.revision
    with pytest.raises(ValueError):
        set_placement(db, user, hypothesis.id, hypothesis.revision, risk=10.5, evidence=0)
    placed = set_placement(db, user, hypothesis.id, hypothesis.revision, risk=10, evidence=0)
    assert placed.priority_risk == 10
    assert placed.priority_evidence == 0
    with pytest.raises(RevisionConflict):
        set_placement(db, user, hypothesis.id, stale_revision, risk=0, evidence=10)


def test_ranking_puts_high_risk_low_evidence_first(db):
    user, project = user_project(db)
    first = create_hypothesis(db, user, project.id, "Urgent uncertain claim")
    set_placement(db, user, first.id, first.revision, risk=10, evidence=0)
    second = create_hypothesis(db, user, project.id, "Well-evidenced claim")
    set_placement(db, user, second.id, second.revision, risk=0, evidence=10)
    ids = [str(first.id), str(second.id)]
    statements = [first.statement, second.statement]
    risks = [first.priority_risk, second.priority_risk]
    evidences = [first.priority_evidence, second.priority_evidence]
    ranking, _ = ranked_backlog_from_ui(*(ids + statements + risks + evidences))
    lines = ranking.splitlines()
    assert lines[1].startswith("1. [risk 10.0 | evidence 0.0] Urgent uncertain claim")
    assert lines[2].startswith("2. [risk 0.0 | evidence 10.0] Well-evidenced claim")
