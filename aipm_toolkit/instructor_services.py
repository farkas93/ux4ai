from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from .auth import require_role
from .baseline_services import import_legacy_reference_json, publish_all_reference_datasets
from .experiment_services import completion_checklist
from .models import Project, Role, Team, User


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
