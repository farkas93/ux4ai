from urllib.parse import urlparse
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from .auth import AuthorizationError, RevisionConflict, can_access_project
from .models import Hypothesis, HypothesisKind, Project, Role, User


def get_project(db: Session, actor: User, project_id: UUID) -> Project:
    project = db.get(Project, project_id)
    if project is None or not can_access_project(actor, project.team_id):
        raise AuthorizationError("Project not found")
    return project


def update_project(db: Session, actor: User, project_id: UUID, revision: int, **fields) -> Project:
    project = get_project(db, actor, project_id)
    allowed = {"product_name", "short_description", "target_user", "job_to_be_done", "current_problem", "product_type", "figma_url"}
    values = {key: value for key, value in fields.items() if key in allowed}
    result = db.execute(update(Project).where(Project.id == project_id, Project.revision == revision).values(**values, revision=revision + 1))
    if result.rowcount != 1:
        db.rollback()
        raise RevisionConflict("The project changed since it was loaded")
    db.commit()
    db.expire(project)
    return db.get(Project, project_id)


def create_project(db: Session, actor: User, product_name: str) -> Project:
    if actor.role != Role.TEAM.value or actor.team_id is None:
        raise AuthorizationError("Only team members can create team projects")
    project = Project(team_id=actor.team_id, product_name=product_name.strip())
    db.add(project)
    db.flush()
    db.add(Hypothesis(project_id=project.id, kind=HypothesisKind.MAIN.value))
    db.commit()
    return project


def list_projects(db: Session, actor: User) -> list[Project]:
    if actor.role == Role.INSTRUCTOR.value:
        return list(db.scalars(select(Project).order_by(Project.updated_at.desc())))
    if actor.team_id is None:
        return []
    return list(db.scalars(select(Project).where(Project.team_id == actor.team_id).order_by(Project.updated_at.desc())))


def validate_figma_url(value: str | None) -> str | None:
    if not value:
        return None
    parsed = urlparse(value.strip())
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("Figma URL must use HTTP or HTTPS")
    return value.strip()


def update_main_hypothesis(db: Session, actor: User, project_id: UUID, revision: int, statement: str) -> Hypothesis:
    hypothesis = get_main_hypothesis(db, actor, project_id)
    result = db.execute(
        update(Hypothesis)
        .where(Hypothesis.id == hypothesis.id, Hypothesis.revision == revision)
        .values(statement=statement.strip(), revision=revision + 1)
    )
    if result.rowcount != 1:
        db.rollback()
        raise RevisionConflict("The hypothesis changed since it was loaded")
    db.commit()
    db.expire(hypothesis)
    return db.get(Hypothesis, hypothesis.id)


def get_main_hypothesis(db: Session, actor: User, project_id: UUID) -> Hypothesis:
    get_project(db, actor, project_id)
    hypothesis = db.scalar(select(Hypothesis).where(Hypothesis.project_id == project_id, Hypothesis.kind == HypothesisKind.MAIN.value))
    if hypothesis is None:
        raise LookupError("Project has no main hypothesis")
    return hypothesis
