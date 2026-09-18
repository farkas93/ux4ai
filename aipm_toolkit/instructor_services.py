from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from .auth import hash_password, require_role
from .baseline_services import import_legacy_reference_json, publish_all_reference_datasets
from .experiment_services import completion_checklist
from .models import Course, Project, Role, Team, User


def course_overview(db: Session, actor: User) -> list[dict]:
    require_role(actor, Role.INSTRUCTOR)
    rows = db.execute(select(Project, Team.alias).join(Team, Project.team_id == Team.id).order_by(Team.alias, Project.product_name)).all()
    overview = []
    for project, alias in rows:
        checklist = completion_checklist(db, actor, project.id)
        overview.append({"project_id": str(project.id), "team_alias": alias, "product_name": project.product_name, "completed_items": sum(checklist.values()), "total_items": len(checklist)})
    return overview


def import_baselines_as_instructor(db: Session, actor: User, directory: str, cohort_label: str, publish: bool) -> dict:
    require_role(actor, Role.INSTRUCTOR)
    source = Path(directory)
    if not source.is_dir():
        raise ValueError("Import directory does not exist")
    report = import_legacy_reference_json(db, source, cohort_label)
    if publish:
        publish_all_reference_datasets(db, cohort_label)
    return report


def provision_team_account(db: Session, actor: User, course_name: str, alias: str, password: str) -> Team:
    require_role(actor, Role.INSTRUCTOR)
    course_name = course_name.strip()
    alias = alias.strip().lower()
    if not course_name or not alias:
        raise ValueError("Course name and team alias are required")
    if len(password) < 12:
        raise ValueError("Team passwords must contain at least 12 characters")
    if db.scalar(select(User).where(User.username == alias)) is not None:
        raise ValueError("That team alias is already in use")
    course = db.scalar(select(Course).where(Course.name == course_name))
    if course is None:
        course = Course(name=course_name)
        db.add(course)
        db.flush()
    if db.scalar(select(Team).where(Team.course_id == course.id, Team.alias == alias)) is not None:
        raise ValueError("That team alias already exists in this course")
    team = Team(course_id=course.id, alias=alias)
    db.add(team)
    db.flush()
    db.add(User(username=alias, password_hash=hash_password(password), role=Role.TEAM.value, team_id=team.id))
    db.commit()
    return team
