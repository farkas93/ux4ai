"""Project lifecycle: explicit, manual deletion only.

There is no automatic deletion or retention policy in this application. Data
is removed only when a team member deletes their own product or an instructor
deletes a product, with explicit confirmation.
"""

from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from .auth import AuthorizationError
from .models import (
    ComparisonSnapshot,
    DimensionEstimate,
    Experiment,
    Hypothesis,
    HypothesisDimension,
    HypothesisRelation,
    HypothesisSource,
    Note,
    NoteDimension,
    ProjectReflection,
    Role,
    User,
)
from .services import get_project


def delete_project(db: Session, actor: User, project_id: UUID, confirm: bool) -> None:
    project = get_project(db, actor, project_id)
    is_instructor = actor.role == Role.INSTRUCTOR.value
    is_owner = project.team_id == actor.team_id
    if not is_instructor and not is_owner:
        raise AuthorizationError("Only the owning team or an instructor can delete this product")
    if not confirm:
        raise ValueError("Explicit deletion confirmation is required")
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
