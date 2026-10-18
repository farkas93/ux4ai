"""Course-specific safety design coverage, separate from product quality."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from .auth import RevisionConflict
from .models import SafetyAssessment, SafetyCheckpoint, User
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


def get_safety(db: Session, actor: User, project_id: UUID) -> tuple[SafetyAssessment | None, list[dict]]:
    get_project(db, actor, project_id)
    assessment = db.scalar(select(SafetyAssessment).where(SafetyAssessment.project_id == project_id))
    existing = {} if assessment is None else {
        item.checkpoint_key: item
        for item in db.scalars(select(SafetyCheckpoint).where(SafetyCheckpoint.assessment_id == assessment.id))
    }
    rows = [
        {"key": key, "coverage": existing[key].coverage if key in existing else None,
         "maturity": existing[key].maturity if key in existing else None,
         "evidence": existing[key].evidence if key in existing else ""}
        for key in CHECKPOINTS
    ]
    return assessment, rows


def save_safety(db: Session, actor: User, project_id: UUID, revision: int | None, rows: list[dict], critical_risk: str) -> SafetyAssessment:
    assessment, previous = get_safety(db, actor, project_id)
    if assessment is None and revision is not None or assessment is not None and assessment.revision != revision:
        raise RevisionConflict("The safety assessment changed since it was loaded")
    if len(rows) != len(CHECKPOINTS) or [item.get("key") for item in rows] != list(CHECKPOINTS):
        raise ValueError("All six safety checkpoints are required")
    for item in rows:
        if item.get("coverage") not in {*COVERAGE, "unknown", None} or item.get("maturity") not in {*MATURITY, None}:
            raise ValueError("Invalid safety checkpoint choice")
        if item.get("coverage") in {"partly_specified", "clearly_specified"} and not (item.get("evidence") or "").strip():
            raise ValueError(f"Explain the {item['key']} checkpoint's claimed coverage")
    before = {"critical_risk": assessment.critical_risk if assessment else "", "checkpoints": previous}
    if assessment is None:
        assessment = SafetyAssessment(project_id=project_id, revision=1)
        db.add(assessment)
        db.flush()
    else:
        assessment.revision += 1
    assessment.critical_risk = critical_risk.strip()
    existing = {item.checkpoint_key: item for item in db.scalars(select(SafetyCheckpoint).where(SafetyCheckpoint.assessment_id == assessment.id))}
    for item in rows:
        checkpoint = existing.get(item["key"])
        if checkpoint is None:
            checkpoint = SafetyCheckpoint(assessment_id=assessment.id, checkpoint_key=item["key"])
            db.add(checkpoint)
        checkpoint.coverage = item["coverage"]
        checkpoint.maturity = item["maturity"]
        checkpoint.evidence = (item.get("evidence") or "").strip()
    after = {"critical_risk": assessment.critical_risk, "checkpoints": rows}
    if before != after:
        record_project_event(db, actor, project_id, "safety.updated", "safety_assessment", assessment.id, "Updated AI safety design coverage", {"before": before, "after": after})
    db.commit()
    return assessment
