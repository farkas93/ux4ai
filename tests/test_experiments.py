import pytest

from aipm_toolkit.auth import AuthorizationError, RevisionConflict, hash_password
from aipm_toolkit.experiment_services import (
    completion_checklist,
    create_experiment,
    save_reflection,
    update_experiment,
)
from aipm_toolkit.hypothesis_services import create_hypothesis
from aipm_toolkit.models import Course, Role, Team, User
from aipm_toolkit.services import create_project


def user_project(db, alias="experiment-team"):
    course = Course(name=f"Course {alias}")
    db.add(course)
    db.flush()
    team = Team(course_id=course.id, alias=alias)
    db.add(team)
    db.flush()
    user = User(username=alias, password_hash=hash_password("P" * 16), role=Role.TEAM.value, team_id=team.id)
    db.add(user)
    db.commit()
    return user, create_project(db, user, "Experiment prototype")


def test_experiment_requires_project_hypothesis_and_does_not_validate_it(db):
    user, project = user_project(db)
    hypothesis = create_hypothesis(db, user, project.id, "Users will complete the task")
    experiment = create_experiment(db, user, project.id, hypothesis.id, "Walk through prototype", "prototype_walkthrough")
    assert experiment.status == "planned"
    updated = update_experiment(db, user, experiment.id, experiment.revision, status="completed", results="Two participants completed the flow", conclusion="Inconclusive", resulting_decision="retest")
    assert updated.resulting_decision == "retest"


def test_cross_project_and_stale_experiment_updates_are_rejected(db):
    user_a, project_a = user_project(db, "a")
    user_b, project_b = user_project(db, "b")
    hypothesis_a = create_hypothesis(db, user_a, project_a.id, "A")
    hypothesis_b = create_hypothesis(db, user_b, project_b.id, "B")
    with pytest.raises(AuthorizationError):
        create_experiment(db, user_a, project_a.id, hypothesis_b.id, "Foreign", "pilot")
    experiment = create_experiment(db, user_a, project_a.id, hypothesis_a.id, "Valid", "pilot")
    with pytest.raises(RevisionConflict):
        update_experiment(db, user_a, experiment.id, experiment.revision - 1, title="Stale")


def test_completion_requires_planned_experiment_and_reflection_is_separate(db):
    user, project = user_project(db)
    hypothesis = create_hypothesis(db, user, project.id, "A claim")
    checklist = completion_checklist(db, user, project.id)
    assert checklist["Next experiment defined"] is False
    create_experiment(db, user, project.id, hypothesis.id, "Next test", "user_interview")
    assert completion_checklist(db, user, project.id)["Next experiment defined"] is True
    reflection = save_reflection(db, user, project.id, "adversarial_risk", "Prompt injection could alter an action.")
    assert reflection.reflection_type == "adversarial_risk"
