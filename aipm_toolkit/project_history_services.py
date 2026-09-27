"""Append-only project activity history."""

import json
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import ProjectEvent, User
from .services import get_project


def record_project_event(
    db: Session,
    actor: User | None,
    project_id: UUID,
    event_type: str,
    entity_type: str,
    entity_id: UUID | str | None,
    summary: str,
    details: dict | None = None,
) -> ProjectEvent:
    event = ProjectEvent(
        project_id=project_id,
        actor_user_id=actor.id if actor else None,
        event_type=event_type,
        entity_type=entity_type,
        entity_id=str(entity_id) if entity_id is not None else None,
        summary=summary,
        details_json=json.dumps(details or {}, ensure_ascii=False, default=str),
    )
    db.add(event)
    return event


def list_project_events(db: Session, actor: User, project_id: UUID, limit: int = 200) -> list[tuple[ProjectEvent, str | None]]:
    get_project(db, actor, project_id)
    rows = db.execute(
        select(ProjectEvent, User.username)
        .outerjoin(User, User.id == ProjectEvent.actor_user_id)
        .where(ProjectEvent.project_id == project_id)
        .order_by(ProjectEvent.created_at.desc(), ProjectEvent.id.desc())
        .limit(limit)
    ).all()
    return [(event, username) for event, username in rows]
