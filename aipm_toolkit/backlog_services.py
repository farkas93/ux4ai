"""Operations for active backlog entries."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from .auth import AuthorizationError
from .models import (
    Hypothesis,
    HypothesisDimension,
    HypothesisKind,
    HypothesisSource,
    Note,
    NoteDimension,
)
from .project_history_services import record_project_event
from .services import get_project


def _entry_snapshot(db: Session, note: Note | None, hypothesis: Hypothesis | None) -> dict:
    result = {}
    if note:
        result["note"] = {
            "id": str(note.id),
            "type": note.note_type,
            "text": note.text,
            "dimensions": list(db.scalars(select(NoteDimension.dimension_key).where(NoteDimension.note_id == note.id))),
        }
    if hypothesis:
        result["hypothesis"] = {
            "id": str(hypothesis.id),
            "statement": hypothesis.statement,
            "dimensions": list(db.scalars(select(HypothesisDimension.dimension_key).where(HypothesisDimension.hypothesis_id == hypothesis.id))),
        }
    return result


def archive_backlog_entry(
    db: Session,
    actor,
    project_id: UUID,
    note_id: UUID | None,
    hypothesis_id: UUID | None,
) -> dict:
    """Hide an entry from current workspaces while preserving its references and history."""
    get_project(db, actor, project_id)
    note = db.get(Note, note_id) if note_id else None
    hypothesis = db.get(Hypothesis, hypothesis_id) if hypothesis_id else None
    if note_id and (note is None or note.project_id != project_id or note.archived_at is not None):
        raise AuthorizationError("Backlog note not found")
    if hypothesis_id and (
        hypothesis is None
        or hypothesis.project_id != project_id
        or hypothesis.kind == HypothesisKind.MAIN.value
        or hypothesis.archived_at is not None
    ):
        raise AuthorizationError("Supporting hypothesis not found")
    if note is None and hypothesis is None:
        raise ValueError("Select a saved backlog entry to remove")
    if note and hypothesis:
        linked = db.scalar(
            select(HypothesisSource.id).where(
                HypothesisSource.hypothesis_id == hypothesis.id,
                HypothesisSource.note_id == note.id,
            )
        )
        if linked is None:
            raise ValueError("The selected note and hypothesis are not the same backlog entry")

    before = _entry_snapshot(db, note, hypothesis)
    archived_at = datetime.now(UTC)
    if note:
        note.archived_at = archived_at
        note.revision += 1

    archived_hypothesis = False
    if hypothesis:
        source_note_ids = list(
            db.scalars(select(HypothesisSource.note_id).where(HypothesisSource.hypothesis_id == hypothesis.id, HypothesisSource.note_id.is_not(None)))
        )
        active_source_ids = [
            source_id
            for source_id in source_note_ids
            if source_id != (note.id if note else None)
            and (source := db.get(Note, source_id)) is not None
            and source.archived_at is None
        ]
        if not active_source_ids:
            hypothesis.archived_at = archived_at
            hypothesis.revision += 1
            archived_hypothesis = True

    record_project_event(
        db,
        actor,
        project_id,
        "backlog.entry_archived",
        "backlog_entry",
        hypothesis.id if hypothesis else (note.id if note else None),
        "Removed backlog entry from current work",
        {
            "before": before,
            "archived_at": archived_at.isoformat(),
            "hypothesis_archived": archived_hypothesis,
            "hypothesis_kept_active_for_other_notes": bool(hypothesis and not archived_hypothesis),
        },
    )
    db.commit()
    return {"note_id": str(note.id) if note else None, "hypothesis_id": str(hypothesis.id) if hypothesis else None, "hypothesis_archived": archived_hypothesis}
