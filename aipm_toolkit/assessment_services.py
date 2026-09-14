from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from .auth import RevisionConflict
from .dimensions import DEFAULT_DIMENSIONS, DIMENSION_KEYS
from .models import (
    AssessmentBasis,
    AssessmentStatus,
    DimensionEstimate,
    ScaleDefinition,
    User,
)
from .services import get_project


def ensure_scale_definitions(db: Session) -> None:
    existing = {item.key for item in db.scalars(select(ScaleDefinition).where(ScaleDefinition.version == 1))}
    for definition in DEFAULT_DIMENSIONS:
        if definition["key"] not in existing:
            db.add(ScaleDefinition(version=1, **definition))
    db.commit()


def get_project_estimates(db: Session, actor: User, project_id: UUID) -> list[DimensionEstimate]:
    get_project(db, actor, project_id)
    definitions = {item.key: item for item in db.scalars(select(ScaleDefinition).where(ScaleDefinition.version == 1))}
    estimates = {item.dimension_key: item for item in db.scalars(select(DimensionEstimate).where(DimensionEstimate.project_id == project_id))}
    return [estimates.setdefault(key, DimensionEstimate(project_id=project_id, dimension_key=key, scale_version=definitions[key].version)) for key in DIMENSION_KEYS]


def save_project_estimates(db: Session, actor: User, project_id: UUID, values: list[dict]) -> list[DimensionEstimate]:
    get_project(db, actor, project_id)
    if {value.get("dimension_key") for value in values} != set(DIMENSION_KEYS):
        raise ValueError("All five dimensions are required")
    definitions = {item.key: item for item in db.scalars(select(ScaleDefinition).where(ScaleDefinition.version == 1))}
    current = {item.dimension_key: item for item in db.scalars(select(DimensionEstimate).where(DimensionEstimate.project_id == project_id))}
    for value in values:
        key = value["dimension_key"]
        status = value.get("status", AssessmentStatus.UNASSESSED.value)
        score = value.get("score")
        if status == AssessmentStatus.ESTIMATED.value:
            if score is None or not 0 <= score <= 5 or round(score * 10) != score * 10:
                raise ValueError(f"{key} estimated scores must be from 0 to 5 in 0.1 steps")
        elif status in {AssessmentStatus.UNKNOWN.value, AssessmentStatus.UNASSESSED.value}:
            score = None
        else:
            raise ValueError(f"Unknown assessment status for {key}")
        basis = value.get("basis")
        if basis is not None and basis not in {item.value for item in AssessmentBasis}:
            raise ValueError(f"Unknown assessment basis for {key}")
        estimate = current.get(key)
        if estimate is None:
            estimate = DimensionEstimate(project_id=project_id, dimension_key=key, scale_version=definitions[key].version, revision=1)
            db.add(estimate)
        elif value.get("revision") != estimate.revision:
            raise RevisionConflict(f"{key} changed since it was loaded")
        estimate.status = status
        estimate.score = score
        estimate.rationale = value.get("rationale", "")
        estimate.basis = basis
        estimate.evidence = value.get("evidence", "")
        estimate.uncertainty = value.get("uncertainty", "")
        estimate.revision += 1
    db.commit()
    return get_project_estimates(db, actor, project_id)
