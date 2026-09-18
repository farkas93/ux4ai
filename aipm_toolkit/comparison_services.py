import json
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from .auth import AuthorizationError
from .dimensions import DIMENSION_KEYS
from .models import ComparisonSnapshot, DimensionEstimate, Product, User
from .services import get_project


def comparison_rows(db: Session, actor: User, project_id: UUID, snapshot_id: UUID) -> list[dict]:
    get_project(db, actor, project_id)
    snapshot = db.get(ComparisonSnapshot, snapshot_id)
    if snapshot is None or snapshot.project_id != project_id:
        raise AuthorizationError("Comparison snapshot not found")
    frozen = json.loads(snapshot.frozen_profile)
    estimates = {item.dimension_key: item for item in db.scalars(select(DimensionEstimate).where(DimensionEstimate.project_id == project_id))}
    rows = []
    for key in DIMENSION_KEYS:
        estimate = estimates.get(key)
        our_score = estimate.score if estimate and estimate.status == "estimated" else None
        baseline = frozen.get(key, {})
        baseline_median = baseline.get("median")
        compatible = baseline.get("compatible", True)
        difference = our_score - baseline_median if compatible and our_score is not None and baseline_median is not None else None
        rows.append({"dimension": key, "our_score": our_score, "baseline_median": baseline_median, "baseline_p25": baseline.get("p25"), "baseline_p75": baseline.get("p75"), "count": baseline.get("count", 0), "difference": difference, "compatible": compatible})
    return rows


def comparator_name(db: Session, snapshot_id: UUID) -> str:
    snapshot = db.get(ComparisonSnapshot, snapshot_id)
    product = db.get(Product, snapshot.product_id) if snapshot else None
    return product.display_name if product else "Unknown comparator"
