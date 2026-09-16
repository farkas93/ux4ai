import json
import tempfile
from datetime import date, datetime
from pathlib import Path
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import (
    BaselineDataset,
    ComparisonSnapshot,
    DimensionEstimate,
    Experiment,
    Hypothesis,
    HypothesisDimension,
    HypothesisRelation,
    Note,
    NoteDimension,
    Product,
    Project,
    ProjectReflection,
    ScaleDefinition,
    User,
)
from .services import get_project

EXPORT_SCHEMA_VERSION = "1.0"
WARNING = "Prototype profiles represent intended or observed prototype behavior, not established production quality or business impact."


def _json_value(value):
    if isinstance(value, (UUID, datetime, date)):
        return str(value)
    return value


def _record(model, item):
    return {column.name: _json_value(getattr(item, column.name)) for column in model.__table__.columns}


def build_project_export(db: Session, actor: User, project_id: UUID) -> dict:
    project = get_project(db, actor, project_id)
    hypotheses = list(db.scalars(select(Hypothesis).where(Hypothesis.project_id == project_id).order_by(Hypothesis.created_at)))
    hypothesis_ids = [item.id for item in hypotheses]
    dimensions = {item.id: [] for item in hypotheses}
    for link in db.scalars(select(HypothesisDimension).where(HypothesisDimension.hypothesis_id.in_(hypothesis_ids))) if hypothesis_ids else []:
        dimensions[link.hypothesis_id].append(link.dimension_key)
    notes = list(db.scalars(select(Note).where(Note.project_id == project_id).order_by(Note.created_at)))
    note_dimensions = {}
    for link in db.scalars(select(NoteDimension).where(NoteDimension.note_id.in_([note.id for note in notes]))) if notes else []:
        note_dimensions.setdefault(link.note_id, []).append(link.dimension_key)
    snapshots = list(db.scalars(select(ComparisonSnapshot).where(ComparisonSnapshot.project_id == project_id).order_by(ComparisonSnapshot.created_at)))
    snapshot_data = []
    for snapshot in snapshots:
        product = db.get(Product, snapshot.product_id)
        dataset = db.get(BaselineDataset, snapshot.dataset_id)
        snapshot_data.append({**_record(ComparisonSnapshot, snapshot), "product": product.display_name if product else None, "dataset": {"cohort_label": dataset.cohort_label, "source_type": dataset.source_type, "scale_version": dataset.scale_version, "provenance_notes": dataset.provenance_notes} if dataset else None})
    estimates = list(db.scalars(select(DimensionEstimate).where(DimensionEstimate.project_id == project_id).order_by(DimensionEstimate.dimension_key)))
    scales = list(db.scalars(select(ScaleDefinition).where(ScaleDefinition.version == 1).order_by(ScaleDefinition.key)))
    experiments = list(db.scalars(select(Experiment).where(Experiment.project_id == project_id).order_by(Experiment.created_at)))
    reflections = list(db.scalars(select(ProjectReflection).where(ProjectReflection.project_id == project_id)))
    relations = list(db.scalars(select(HypothesisRelation).where(HypothesisRelation.project_id == project_id)))
    return {
        "schema_version": EXPORT_SCHEMA_VERSION,
        "warning": WARNING,
        "project": _record(Project, project),
        "scale_definitions": [_record(ScaleDefinition, item) for item in scales],
        "dimension_assessments": [_record(DimensionEstimate, item) for item in estimates],
        "comparison_snapshots": snapshot_data,
        "notes": [{**_record(Note, note), "dimensions": note_dimensions.get(note.id, [])} for note in notes],
        "hypotheses": [{**_record(Hypothesis, item), "dimensions": dimensions[item.id]} for item in hypotheses],
        "hypothesis_relationships": [_record(HypothesisRelation, item) for item in relations],
        "experiments": [_record(Experiment, item) for item in experiments],
        "reflections": [_record(ProjectReflection, item) for item in reflections],
    }


def export_project_json(db: Session, actor: User, project_id: UUID) -> str:
    return json.dumps(build_project_export(db, actor, project_id), ensure_ascii=False, indent=2)


def export_project_markdown(db: Session, actor: User, project_id: UUID) -> str:
    document = build_project_export(db, actor, project_id)
    project = document["project"]
    main = next((item for item in document["hypotheses"] if item["kind"] == "main"), None)
    lines = [f"# {project['product_name']}", "", f"> {WARNING}", "", "## Product and Value Hypothesis", f"- Short description: {project['short_description']}", f"- Target user: {project['target_user']}", f"- Job to be done: {project['job_to_be_done']}", f"- Current problem: {project['current_problem']}", f"- Main value hypothesis: {(main or {}).get('statement', '')}", "", "## Dimension Profile"]
    for assessment in document["dimension_assessments"]:
        lines.append(f"- {assessment['dimension_key']}: {assessment['status']}" + (f" ({assessment['score']}/5)" if assessment["score"] is not None else "") + f". {assessment['rationale']}")
    lines.extend(["", "## Comparator and Provenance"])
    if document["comparison_snapshots"]:
        for snapshot in document["comparison_snapshots"]:
            lines.append(f"- {snapshot['product']} ({snapshot['purpose']}): {snapshot['dataset']['provenance_notes']}")
    else:
        lines.append("- No comparator selected.")
    lines.extend(["", "## Main Observations"])
    for note in document["notes"]:
        lines.append(f"- **{note['note_type']}**: {note['text']}")
    lines.extend(["", "## Hypothesis Backlog"])
    for hypothesis in document["hypotheses"]:
        lines.append(f"- **{hypothesis['kind']}**: {hypothesis['statement']} (impact: {hypothesis['impact_if_wrong']}, evidence: {hypothesis['evidence_strength']})")
    lines.extend(["", "## Relationships"])
    for relation in document["hypothesis_relationships"]:
        lines.append(f"- {relation['relation_type']}: {relation['from_hypothesis_id']} -> {relation['to_hypothesis_id']}")
    lines.extend(["", "## Prioritized Experiment"])
    planned = [item for item in document["experiments"] if item["status"] == "planned"]
    for experiment in planned[:1]:
        lines.extend([f"- **{experiment['title']}** ({experiment['method']})", f"  - Metric: {experiment['metric']}", f"  - Success criterion: {experiment['success_criterion']}", f"  - Guardrail: {experiment['guardrail']}"])
    if not planned:
        lines.append("- No planned experiment.")
    lines.extend(["", "## Open Questions"])
    for note in document["notes"]:
        if note["note_type"] == "question":
            lines.append(f"- {note['text']}")
    return "\n".join(lines) + "\n"


def write_export_files(db: Session, actor: User, project_id: UUID) -> tuple[str, str]:
    get_project(db, actor, project_id)
    directory = Path(tempfile.gettempdir()) / "aipm-toolkit-exports"
    directory.mkdir(mode=0o700, exist_ok=True)
    json_path = directory / f"project-{project_id}.json"
    markdown_path = directory / f"project-{project_id}.md"
    json_path.write_text(export_project_json(db, actor, project_id), encoding="utf-8")
    markdown_path.write_text(export_project_markdown(db, actor, project_id), encoding="utf-8")
    return str(json_path), str(markdown_path)
