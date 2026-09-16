from uuid import UUID

from aipm_toolkit.assessment_services import ensure_scale_definitions, save_project_estimates
from aipm_toolkit.auth import hash_password
from aipm_toolkit.experiment_services import completion_checklist, create_experiment
from aipm_toolkit.export_services import build_project_export
from aipm_toolkit.hypothesis_services import add_relation, create_hypothesis, create_note
from aipm_toolkit.models import Course, Role, Team, User
from aipm_toolkit.services import create_project, get_main_hypothesis, get_project, update_project


def test_representative_team_workflow_survives_reload_and_export(db):
    course = Course(name="Integration course")
    db.add(course)
    db.flush()
    team = Team(course_id=course.id, alias="integration-team")
    db.add(team)
    db.flush()
    actor = User(username="integration-team", password_hash=hash_password("P" * 16), role=Role.TEAM.value, team_id=team.id)
    db.add(actor)
    db.commit()

    project = create_project(db, actor, "Workshop product")
    project = update_project(db, actor, project.id, project.revision, short_description="A useful prototype", target_user="Workshop teams", job_to_be_done="Find the next test", current_problem="Uncertainty is scattered")
    main = get_main_hypothesis(db, actor, project.id)
    update_project(db, actor, project.id, project.revision, product_type="Plugin")
    project = get_project(db, actor, project.id)
    assert project.short_description == "A useful prototype"

    ensure_scale_definitions(db)
    estimates = [{"dimension_key": key, "status": "unknown", "score": None, "revision": 1} for key in ("conversational", "specialization", "autonomy", "accessibility", "explainability")]
    estimates[0].update(status="estimated", score=0.0)
    save_project_estimates(db, actor, project.id, estimates)

    note = create_note(db, actor, project.id, "observation", "The prototype makes the next action visible.")
    supporting = create_hypothesis(db, actor, project.id, "If the next action is visible, teams will choose a test sooner.", value_link="Contributes to the main value hypothesis.", note_id=note.id)
    add_relation(db, actor, project.id, "contributes_to", supporting.id, main.id)
    create_experiment(db, actor, project.id, supporting.id, "Prototype walkthrough", "prototype_walkthrough")

    reloaded = get_project(db, actor, UUID(str(project.id)))
    document = build_project_export(db, actor, reloaded.id)
    assert document["project"]["product_name"] == "Workshop product"
    assert len(document["dimension_assessments"]) == 5
    assert document["notes"][0]["text"].startswith("The prototype")
    assert any(item["kind"] == "supporting" for item in document["hypotheses"])
    assert len(document["experiments"]) == 1
    assert completion_checklist(db, actor, project.id)["Next experiment defined"] is True
