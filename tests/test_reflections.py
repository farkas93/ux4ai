import pytest

from aipm_toolkit.auth import hash_password
from aipm_toolkit.experiment_services import save_reflection
from aipm_toolkit.models import Course, ProjectReflection, Role, Team, User
from aipm_toolkit.services import create_project


def user_project(db):
    course = Course(name="Reflection course")
    db.add(course)
    db.flush()
    team = Team(course_id=course.id, alias="reflection-team")
    db.add(team)
    db.flush()
    user = User(username="reflection-team", password_hash=hash_password("P" * 16), role=Role.TEAM.value, team_id=team.id)
    db.add(user)
    db.commit()
    return user, create_project(db, user, "Reflection product")


def test_structured_reflections_persist_and_update(db):
    user, project = user_project(db)
    risk = save_reflection(db, user, project.id, "adversarial_risk", "uncertain", subjective_score=0, attack_entry_point="Prompt input", unwanted_behavior="Unsafe action", affected_data_action="Account data", consequence="Loss of trust", proposed_safeguard="Approval step")
    assert risk.subjective_score == 0
    feedback = save_reflection(db, user, project.id, "feedback_loop", "", signal_to_collect="Approval rate", signal_meaning="Where users hesitate", possible_product_change="Add explanation", human_interpretation_needed="Product review", evaluation_after_change="Repeat walkthrough")
    assert feedback.signal_to_collect == "Approval rate"
    assert db.scalar(__import__("sqlalchemy").select(ProjectReflection).where(ProjectReflection.project_id == project.id, ProjectReflection.reflection_type == "feedback_loop")) is not None


def test_invalid_risk_score_is_rejected(db):
    user, project = user_project(db)
    with pytest.raises(ValueError):
        save_reflection(db, user, project.id, "adversarial_risk", "", subjective_score=5.1)
