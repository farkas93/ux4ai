from uuid import UUID

from sqlalchemy import select
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
from .services import get_project


def create_note(db: Session, actor: User, project_id: UUID, note_type: str, text: str, dimensions: list[str] | None = None) -> Note:
    get_project(db, actor, project_id)
    if note_type not in {item.value for item in NoteType} or not text.strip():
        raise ValueError("A note requires a valid type and text")
    dimensions = dimensions or []
    if not set(dimensions).issubset(DIMENSION_KEYS):
        raise ValueError("Unknown note dimension")
    note = Note(project_id=project_id, note_type=note_type, text=text.strip())
    db.add(note)
    db.flush()
    for dimension in dimensions:
        db.add(NoteDimension(note_id=note.id, dimension_key=dimension))
    db.commit()
    return note


def list_notes(db: Session, actor: User, project_id: UUID) -> list[Note]:
    get_project(db, actor, project_id)
    return list(db.scalars(select(Note).where(Note.project_id == project_id).order_by(Note.created_at.desc())))


def create_hypothesis(db: Session, actor: User, project_id: UUID, statement: str, *, kind: str = HypothesisKind.SUPPORTING.value, value_link: str = "", dimensions: list[str] | None = None, note_id: UUID | None = None) -> Hypothesis:
    get_project(db, actor, project_id)
    if not statement.strip() or kind not in {item.value for item in HypothesisKind}:
        raise ValueError("A hypothesis requires a valid statement and kind")
    if kind == HypothesisKind.MAIN.value:
        existing = db.scalar(select(Hypothesis).where(Hypothesis.project_id == project_id, Hypothesis.kind == HypothesisKind.MAIN.value))
        if existing:
            raise ValueError("A project can have only one main hypothesis")
    dimensions = dimensions or []
    if not set(dimensions).issubset(DIMENSION_KEYS):
        raise ValueError("Unknown hypothesis dimension")
    hypothesis = Hypothesis(project_id=project_id, kind=kind, statement=statement.strip(), value_link=value_link.strip())
    db.add(hypothesis)
    db.flush()
    for dimension in dimensions:
        db.add(HypothesisDimension(hypothesis_id=hypothesis.id, dimension_key=dimension))
    if note_id:
        note = db.get(Note, note_id)
        if note is None or note.project_id != project_id:
            raise AuthorizationError("Note does not belong to this project")
        db.add(HypothesisSource(hypothesis_id=hypothesis.id, note_id=note_id))
    db.commit()
    return hypothesis


def update_hypothesis(db: Session, actor: User, hypothesis_id: UUID, revision: int, **fields) -> Hypothesis:
    hypothesis = db.get(Hypothesis, hypothesis_id)
    if hypothesis is None:
        raise AuthorizationError("Hypothesis not found")
    get_project(db, actor, hypothesis.project_id)
    allowed = {"statement", "value_link", "expected_tradeoff", "impact_if_wrong", "evidence_strength", "evidence_rationale", "workflow_status", "review_conclusion", "next_decision"}
    for key, value in fields.items():
        if key in allowed:
            setattr(hypothesis, key, value.strip() if isinstance(value, str) else value)
    if hypothesis.evidence_strength in {"moderate", "strong"} and not hypothesis.evidence_rationale.strip():
        raise ValueError("Moderate or strong evidence requires a rationale")
    if hypothesis.revision != revision:
        raise RevisionConflict("The hypothesis changed since it was loaded")
    hypothesis.revision += 1
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
    if source is None or target is None or source.project_id != project_id or target.project_id != project_id:
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
    db.commit()
    return relation
