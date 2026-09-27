from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from .auth import AuthorizationError, RevisionConflict
from .dimensions import DIMENSION_KEYS
from .models import (
    Hypothesis,
    HypothesisDimension,
    HypothesisKind,
    HypothesisRelation,
    HypothesisSource,
    Note,
    NoteDimension,
    NoteType,
    RelationshipType,
    User,
)
from .project_history_services import record_project_event
from .services import get_project


def create_note(db: Session, actor: User, project_id: UUID, note_type: str, text: str, dimensions: list[str] | None = None, *, origin_section: str | None = None, origin_key: str | None = None) -> Note:
    get_project(db, actor, project_id)
    if note_type not in {item.value for item in NoteType} or not text.strip():
        raise ValueError("A note requires a valid type and text")
    dimensions = dimensions or []
    if len(set(dimensions)) > 1:
        raise ValueError("A backlog entry can be assigned to only one dimension")
    if not set(dimensions).issubset(DIMENSION_KEYS):
        raise ValueError("Unknown note dimension")
    if origin_section not in {None, "assessment", "backlog", "safety", "self_improvement"} or (origin_section == "safety" and origin_key not in {"scope", "harms", "controls", "evaluation", "response", "ownership"}) or (origin_section != "safety" and origin_key is not None):
        raise ValueError("Unknown learning area")
    note = Note(project_id=project_id, note_type=note_type, text=text.strip(), origin_section=origin_section, origin_key=origin_key)
    db.add(note)
    db.flush()
    for dimension in dimensions:
        db.add(NoteDimension(note_id=note.id, dimension_key=dimension))
    record_project_event(db, actor, project_id, "backlog.note_created", "note", note.id, f"Added {note_type}", {"text": note.text, "dimensions": dimensions, "origin_section": origin_section, "origin_key": origin_key})
    db.commit()
    return note


def list_notes(db: Session, actor: User, project_id: UUID) -> list[Note]:
    get_project(db, actor, project_id)
    return list(db.scalars(select(Note).where(Note.project_id == project_id, Note.archived_at.is_(None)).order_by(Note.created_at.desc())))


def update_note(db: Session, actor: User, note_id: UUID, revision: int, note_type: str, text: str, dimensions: list[str] | None = None) -> Note:
    note = db.get(Note, note_id)
    if note is None:
        raise AuthorizationError("Note not found")
    if note.archived_at is not None:
        raise AuthorizationError("Archived notes cannot be edited")
    get_project(db, actor, note.project_id)
    if note.revision != revision:
        raise RevisionConflict("The note changed since it was loaded")
    if note_type not in {item.value for item in NoteType} or not text.strip():
        raise ValueError("A note requires a valid type and text")
    dimensions = dimensions or []
    if len(set(dimensions)) > 1:
        raise ValueError("A backlog entry can be assigned to only one dimension")
    if not set(dimensions).issubset(DIMENSION_KEYS):
        raise ValueError("Unknown note dimension")
    before_dimensions = list(db.scalars(select(NoteDimension.dimension_key).where(NoteDimension.note_id == note_id)))
    before = {"note_type": note.note_type, "text": note.text, "dimensions": before_dimensions}
    note.note_type = note_type
    note.text = text.strip()
    db.execute(delete(NoteDimension).where(NoteDimension.note_id == note_id))
    for dimension in dimensions:
        db.add(NoteDimension(note_id=note_id, dimension_key=dimension))
    note.revision += 1
    record_project_event(
        db,
        actor,
        note.project_id,
        "backlog.note_updated",
        "note",
        note.id,
        f"Updated {note_type}",
        {"before": before, "after": {"note_type": note.note_type, "text": note.text, "dimensions": dimensions}},
    )
    db.commit()
    return note


def create_hypothesis(db: Session, actor: User, project_id: UUID, statement: str, *, kind: str = HypothesisKind.SUPPORTING.value, value_link: str = "", dimensions: list[str] | None = None, note_id: UUID | None = None) -> Hypothesis:
    get_project(db, actor, project_id)
    if not statement.strip() or kind not in {item.value for item in HypothesisKind}:
        raise ValueError("A hypothesis requires a valid statement and kind")
    if kind == HypothesisKind.MAIN.value:
        existing = db.scalar(select(Hypothesis).where(Hypothesis.project_id == project_id, Hypothesis.kind == HypothesisKind.MAIN.value))
        if existing:
            raise ValueError("A project can have only one main hypothesis")
    dimensions = dimensions or []
    if len(set(dimensions)) > 1:
        raise ValueError("A backlog entry can be assigned to only one dimension")
    if not set(dimensions).issubset(DIMENSION_KEYS):
        raise ValueError("Unknown hypothesis dimension")
    hypothesis = Hypothesis(project_id=project_id, kind=kind, statement=statement.strip(), value_link=value_link.strip())
    db.add(hypothesis)
    db.flush()
    for dimension in dimensions:
        db.add(HypothesisDimension(hypothesis_id=hypothesis.id, dimension_key=dimension))
    if note_id:
        note = db.get(Note, note_id)
        if note is None or note.project_id != project_id or note.archived_at is not None:
            raise AuthorizationError("Note does not belong to this project")
        db.add(HypothesisSource(hypothesis_id=hypothesis.id, note_id=note_id))
    record_project_event(
        db,
        actor,
        project_id,
        "backlog.hypothesis_created",
        "hypothesis",
        hypothesis.id,
        "Added supporting hypothesis" if kind == HypothesisKind.SUPPORTING.value else "Added main hypothesis",
        {"statement": hypothesis.statement, "dimensions": dimensions},
    )
    db.commit()
    return hypothesis


def update_hypothesis(db: Session, actor: User, hypothesis_id: UUID, revision: int, **fields) -> Hypothesis:
    hypothesis = db.get(Hypothesis, hypothesis_id)
    if hypothesis is None:
        raise AuthorizationError("Hypothesis not found")
    if hypothesis.archived_at is not None:
        raise AuthorizationError("Archived hypotheses cannot be edited")
    get_project(db, actor, hypothesis.project_id)
    allowed = {"statement", "value_link", "expected_tradeoff", "impact_if_wrong", "evidence_strength", "evidence_rationale", "workflow_status", "review_conclusion", "next_decision"}
    before = {key: getattr(hypothesis, key) for key in allowed}
    for key, value in fields.items():
        if key in allowed:
            setattr(hypothesis, key, value.strip() if isinstance(value, str) else value)
    if hypothesis.evidence_strength in {"moderate", "strong"} and not hypothesis.evidence_rationale.strip():
        raise ValueError("Moderate or strong evidence requires a rationale")
    if hypothesis.revision != revision:
        raise RevisionConflict("The hypothesis changed since it was loaded")
    hypothesis.revision += 1
    after = {key: getattr(hypothesis, key) for key in allowed}
    changed = {key: {"before": before[key], "after": after[key]} for key in allowed if before[key] != after[key]}
    if changed:
        record_project_event(db, actor, hypothesis.project_id, "hypothesis.updated", "hypothesis", hypothesis.id, "Updated hypothesis", changed)
    db.commit()
    return hypothesis


def set_placement(db: Session, actor: User, hypothesis_id: UUID, revision: int, risk: float, evidence: float) -> Hypothesis:
    hypothesis = db.get(Hypothesis, hypothesis_id)
    if hypothesis is None:
        raise AuthorizationError("Hypothesis not found")
    if hypothesis.archived_at is not None:
        raise AuthorizationError("Archived hypotheses cannot be edited")
    get_project(db, actor, hypothesis.project_id)
    if hypothesis.revision != revision:
        raise RevisionConflict("The hypothesis changed since it was loaded")
    for name, value in (("risk", risk), ("evidence", evidence)):
        if value is None or not 0 <= value <= 10:
            raise ValueError(f"Placement {name} must be between 0 and 10")
    hypothesis.priority_risk = float(risk)
    hypothesis.priority_evidence = float(evidence)
    hypothesis.revision += 1
    record_project_event(
        db,
        actor,
        hypothesis.project_id,
        "hypothesis.priority_updated",
        "hypothesis",
        hypothesis.id,
        "Updated hypothesis priority placement",
        {"risk": hypothesis.priority_risk, "evidence": hypothesis.priority_evidence},
    )
    db.commit()
    return hypothesis


def _relation_pair(relation_type: str, source: UUID, target: UUID) -> tuple[UUID, UUID]:
    if relation_type in {RelationshipType.ALTERNATIVE_TO.value, RelationshipType.IN_TENSION_WITH.value}:
        return tuple(sorted((source, target), key=str))
    return source, target


def add_relation(db: Session, actor: User, project_id: UUID, relation_type: str, source_id: UUID, target_id: UUID) -> HypothesisRelation:
    get_project(db, actor, project_id)
    if source_id == target_id or relation_type not in {item.value for item in RelationshipType}:
        raise ValueError("Invalid hypothesis relationship")
    source = db.get(Hypothesis, source_id)
    target = db.get(Hypothesis, target_id)
    if source is None or target is None or source.archived_at is not None or target.archived_at is not None or source.project_id != project_id or target.project_id != project_id:
        raise AuthorizationError("Hypotheses must belong to the same project")
    source_id, target_id = _relation_pair(relation_type, source_id, target_id)
    if relation_type == RelationshipType.DEPENDS_ON.value:
        edges = db.execute(select(HypothesisRelation.from_hypothesis_id, HypothesisRelation.to_hypothesis_id).where(HypothesisRelation.project_id == project_id, HypothesisRelation.relation_type == relation_type)).all()
        graph = {}
        for left, right in edges:
            graph.setdefault(left, set()).add(right)
        graph.setdefault(source_id, set()).add(target_id)
        stack = [target_id]
        seen = set()
        while stack:
            node = stack.pop()
            if node == source_id:
                raise ValueError("Dependency cycles are not allowed")
            if node not in seen:
                seen.add(node)
                stack.extend(graph.get(node, ()))
    relation = HypothesisRelation(project_id=project_id, relation_type=relation_type, from_hypothesis_id=source_id, to_hypothesis_id=target_id)
    db.add(relation)
    record_project_event(
        db,
        actor,
        project_id,
        "hypothesis.relation_added",
        "hypothesis_relation",
        relation.id,
        f"Linked hypotheses ({relation_type.replace('_', ' ')})",
        {"from_hypothesis_id": source_id, "to_hypothesis_id": target_id, "relation_type": relation_type},
    )
    db.commit()
    return relation
