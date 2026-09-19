from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from .auth import require_role
from .models import (
    ComparisonSnapshot,
    Course,
    DimensionEstimate,
    Experiment,
    Hypothesis,
    HypothesisDimension,
    HypothesisRelation,
    HypothesisSource,
    Note,
    NoteDimension,
    Project,
    ProjectReflection,
    Role,
    User,
)


def update_course_retention(db: Session, actor: User, course_name: str, retention_days: int, deletion_policy: str) -> Course:
    require_role(actor, Role.INSTRUCTOR)
    if retention_days < 1 or retention_days > 3650:
        raise ValueError("Retention must be between 1 and 3650 days")
    course = db.scalar(select(Course).where(Course.name == course_name.strip()))
    if course is None:
        raise ValueError("Course not found")
    course.retention_days = retention_days
    course.deletion_policy = deletion_policy.strip()
    course.revision += 1
    db.commit()
    return course


def delete_project_as_instructor(db: Session, actor: User, project_id: UUID, confirm: bool) -> None:
    require_role(actor, Role.INSTRUCTOR)
    if not confirm:
        raise ValueError("Explicit deletion confirmation is required")
    project = db.get(Project, project_id)
    if project is None:
        raise ValueError("Project not found")
    hypothesis_ids = list(db.scalars(select(Hypothesis.id).where(Hypothesis.project_id == project_id)))
    note_ids = list(db.scalars(select(Note.id).where(Note.project_id == project_id)))
    db.execute(delete(HypothesisRelation).where(HypothesisRelation.project_id == project_id))
    if hypothesis_ids:
        db.execute(delete(HypothesisSource).where(HypothesisSource.hypothesis_id.in_(hypothesis_ids)))
        db.execute(delete(HypothesisDimension).where(HypothesisDimension.hypothesis_id.in_(hypothesis_ids)))
        db.execute(delete(Experiment).where(Experiment.primary_hypothesis_id.in_(hypothesis_ids)))
    if note_ids:
        db.execute(delete(NoteDimension).where(NoteDimension.note_id.in_(note_ids)))
    db.execute(delete(DimensionEstimate).where(DimensionEstimate.project_id == project_id))
    db.execute(delete(ProjectReflection).where(ProjectReflection.project_id == project_id))
    db.execute(delete(ComparisonSnapshot).where(ComparisonSnapshot.project_id == project_id))
    db.execute(delete(Note).where(Note.project_id == project_id))
    db.execute(delete(Hypothesis).where(Hypothesis.project_id == project_id))
    db.delete(project)
    db.commit()
