"""Course-specific classifications for individual AI-assisted improvement loops."""

import json
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from .auth import AuthorizationError, RevisionConflict
from .models import ImprovementLoop, User
from .project_history_services import record_project_event
from .services import get_project

QUESTIONS = {
    "observe": "Does AI label or summarize operational evidence?",
    "diagnose": "Does AI diagnose specific problems?",
    "propose": "Does AI propose concrete changes?",
    "evaluate": "Does AI evaluate candidates against a baseline?",
    "apply_monitor": "Can accepted changes be applied and monitored over repeated cycles?",
    "automated_experiments": "Are experiments run automatically before release?",
    "bounded_application": "Can accepted changes be applied automatically within explicit bounds?",
}
LEVEL_NAMES = (
    "Human-led improvement", "AI-assisted observation", "AI-assisted diagnosis",
    "AI-generated candidate changes", "Automated experimentation with human release approval",
    "Bounded automatic application and monitoring over repeated cycles",
)
SCOPES = {"content", "retrieval", "prompts", "workflow", "code", "model_parameters"}
ANSWERS = {"yes", "partly", "no", "unknown"}


def classify_loop(answers: dict, release_approval: str, success_checks: str, rollback: str, approval_boundary: str = "") -> dict:
    """Return highest fully met level and potential level gated only by unknowns."""
    requirements = [
        (), ("observe",), ("observe", "diagnose"), ("observe", "diagnose", "propose"),
        ("observe", "diagnose", "propose", "evaluate", "automated_experiments"),
        ("observe", "diagnose", "propose", "evaluate", "automated_experiments", "apply_monitor", "bounded_application"),
    ]

    def qualifies(level: int, possible: bool) -> bool:
        accepted = {"yes", "unknown"} if possible else {"yes"}
        if any(answers.get(key, "unknown") not in accepted for key in requirements[level]):
            return False
        if level >= 4 and not success_checks.strip():
            return False
        if level == 4 and release_approval not in ({"human", "unspecified"} if possible else {"human"}):
            return False
        return not (level == 5 and (release_approval not in ({"bounded_automatic", "unspecified"} if possible else {"bounded_automatic"}) or not rollback.strip() or not approval_boundary.strip()))

    confirmed = max(level for level in range(6) if qualifies(level, False))
    possible = max(level for level in range(6) if qualifies(level, True))
    return {"level": confirmed, "possible_level": possible, "provisional": possible > confirmed, "name": LEVEL_NAMES[confirmed]}


def list_loops(db: Session, actor: User, project_id: UUID) -> list[ImprovementLoop]:
    get_project(db, actor, project_id)
    return list(db.scalars(select(ImprovementLoop).where(ImprovementLoop.project_id == project_id).order_by(ImprovementLoop.created_at, ImprovementLoop.id)))


def save_loop(db: Session, actor: User, project_id: UUID, loop_id: UUID | None, revision: int | None, data: dict) -> ImprovementLoop:
    get_project(db, actor, project_id)
    loop = db.get(ImprovementLoop, loop_id) if loop_id else None
    if loop_id and (loop is None or loop.project_id != project_id):
        raise AuthorizationError("Improvement loop not found")
    if (loop is None and revision is not None) or (loop is not None and loop.revision != revision):
        raise RevisionConflict("The improvement loop changed since it was loaded")
    answers = data["answers"]
    if set(answers) != set(QUESTIONS) or any(value.get("answer") not in ANSWERS | {None} for value in answers.values()):
        raise ValueError("Complete the improvement capability questions with valid choices")
    if any(value.get("answer") in {"yes", "partly", "no"} and not (value.get("explanation") or "").strip() for value in answers.values()):
        raise ValueError("Explain each answered improvement capability")
    if not data["name"].strip():
        raise ValueError("Name a specific improvement loop")
    if not set(data["scopes"]).issubset(SCOPES) or data["status"] not in {"intended", "implemented", "demonstrated"} or data["recursion_scope"] not in {"product_behavior", "improvement_process"} or data["release_approval"] not in {"human", "bounded_automatic", "unspecified"}:
        raise ValueError("Invalid improvement loop scope or status")
    before = None if loop is None else {
        "name": loop.name, "answers": json.loads(loop.capabilities_json), "status": loop.status,
        "scopes": json.loads(loop.change_scopes_json), "recursion_scope": loop.recursion_scope,
        "release_approval": loop.release_approval, "approval_boundary": loop.approval_boundary,
        "success_checks": loop.success_checks, "rollback": loop.rollback,
    }
    if loop is None:
        loop = ImprovementLoop(project_id=project_id, revision=1)
        db.add(loop)
    else:
        loop.revision += 1
    loop.name = data["name"].strip()
    loop.capabilities_json = json.dumps({key: {"answer": (value.get("answer") or "unknown"), "explanation": (value.get("explanation") or "").strip()} for key, value in answers.items()})
    loop.status = data["status"]
    loop.change_scopes_json = json.dumps(sorted(set(data["scopes"])))
    loop.recursion_scope = data["recursion_scope"]
    loop.release_approval = data["release_approval"]
    loop.approval_boundary = data["approval_boundary"].strip()
    loop.success_checks = data["success_checks"].strip()
    loop.rollback = data["rollback"].strip()
    db.flush()
    after = {"name": loop.name, "answers": json.loads(loop.capabilities_json), "status": loop.status,
             "scopes": json.loads(loop.change_scopes_json), "recursion_scope": loop.recursion_scope,
             "release_approval": loop.release_approval, "approval_boundary": loop.approval_boundary,
             "success_checks": loop.success_checks, "rollback": loop.rollback}
    if before != after:
        record_project_event(db, actor, project_id, "improvement_loop.saved", "improvement_loop", loop.id,
                             f"{'Created' if before is None else 'Updated'} improvement loop: {loop.name}", {"before": before, "after": after})
    db.commit()
    return loop
