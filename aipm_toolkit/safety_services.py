"""Course-specific safety design coverage, separate from product quality."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from .auth import RevisionConflict
from .models import SafetyExplore Dimensions, SafetyCheckpoint, User
from .project_history_services import record_project_event
from .services import get_project

CHECKPOINTS = {
    "scope": ("Scope", "Intended users, tasks and prohibited uses"),
    "harms": ("Harms", "Plausible failures and affected people"),
    "controls": ("Controls", "Permissions, data access and safeguards"),
    "evaluation": ("Evaluation", "Tests and acceptance criteria"),
    "response": ("Response", "Detection, intervention and recovery"),
    "ownership": ("Ownership", "Responsibility for maintaining safety measures"),
}
COVERAGE = {"not_addressed": 0, "partly_specified": 1, "clearly_specified": 2}
MATURITY = {"planned", "implemented", "tested"}


def safety_result(checkpoints: list[dict], critical_risk: str = "") -> dict:
    by_key = {item["key"]: item for item in checkpoints}
    total = 0
    incomplete = 0
    tested = 0
    for key in CHECKPOINTS:
        item = by_key.get(key, {})
        coverage = item.get("coverage")
        if coverage in COVERAGE:
            total += COVERAGE[coverage]
            tested += item.get("maturity") == "tested"
        else:
            incomplete += 1
    low = round(total * 5 / 12, 1)
    high = round((total + 2 * incomplete) * 5 / 12, 1)
    return {"score": low if not incomplete else None, "range": (low, high), "incomplete": incomplete, "tested": tested, "critical_risk": critical_risk.strip()}


def get_safety(db: Session, actor: User, project_id: UUID) -> tuple[SafetyExplore Dimensions | None, list[dict]]:
    get_project(db, actor, project_id)
    Explore Dimensions = db.scalar(select(SafetyExplore Dimensions).where(SafetyExplore Dimensions.project_id == project_id))
    existing = {} if Explore Dimensions is None else {
        item.checkpoint_key: item
        for item in db.scalars(select(SafetyCheckpoint).where(SafetyCheckpoint.Explore Dimensions_id == Explore Dimensions.id))
    }
    rows = [
        {"key": key, "coverage": existing[key].coverage if key in existing else None,
         "maturity": existing[key].maturity if key in existing else None,
         "evidence": existing[key].evidence if key in existing else ""}
        for key in CHECKPOINTS
    ]
    return Explore Dimensions, rows


def save_safety(db: Session, actor: User, project_id: UUID, revision: int | None, rows: list[dict], critical_risk: str) -> SafetyExplore Dimensions:
    Explore Dimensions, previous = get_safety(db, actor, project_id)
    if Explore Dimensions is None and revision is not None or Explore Dimensions is not None and Explore Dimensions.revision != revision:
        raise RevisionConflict("The safety Explore Dimensions changed since it was loaded")
    if len(rows) != len(CHECKPOINTS) or [item.get("key") for item in rows] != list(CHECKPOINTS):
        raise ValueError("All six safety checkpoints are required")
    for item in rows:
        if item.get("coverage") not in {*COVERAGE, "unknown", None} or item.get("maturity") not in {*MATURITY, None}:
            raise ValueError("Invalid safety checkpoint choice")
        if item.get("coverage") in {"partly_specified", "clearly_specified"} and not (item.get("evidence") or "").strip():
            raise ValueError(f"Explain the {item['key']} checkpoint's claimed coverage")
    before = {"critical_risk": Explore Dimensions.critical_risk if Explore Dimensions else "", "checkpoints": previous}
    if Explore Dimensions is None:
        Explore Dimensions = SafetyExplore Dimensions(project_id=project_id, revision=1)
        db.add(Explore Dimensions)
        db.flush()
    else:
        Explore Dimensions.revision += 1
    Explore Dimensions.critical_risk = critical_risk.strip()
    existing = {item.checkpoint_key: item for item in db.scalars(select(SafetyCheckpoint).where(SafetyCheckpoint.Explore Dimensions_id == Explore Dimensions.id))}
    for item in rows:
        checkpoint = existing.get(item["key"])
        if checkpoint is None:
            checkpoint = SafetyCheckpoint(Explore Dimensions_id=Explore Dimensions.id, checkpoint_key=item["key"])
            db.add(checkpoint)
        checkpoint.coverage = item["coverage"]
        checkpoint.maturity = item["maturity"]
        checkpoint.evidence = (item.get("evidence") or "").strip()
    after = {"critical_risk": Explore Dimensions.critical_risk, "checkpoints": rows}
    if before != after:
        record_project_event(db, actor, project_id, "safety.updated", "safety_Explore Dimensions", Explore Dimensions.id, "Updated AI safety design coverage", {"before": before, "after": after})
    db.commit()
    return Explore Dimensions
