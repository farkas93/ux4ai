import json
import math
import tempfile
from datetime import date, datetime
from pathlib import Path
from uuid import UUID

from fpdf import FPDF
from sqlalchemy import select
from sqlalchemy.orm import Session

from .improvement_services import classify_loop
from .learning_report import markdown_report, pdf_report
from .models import (
    BaselineDataset,
    ComparisonSnapshot,
    DimensionEstimate,
    Experiment,
    Hypothesis,
    HypothesisDimension,
    HypothesisRelation,
    HypothesisSource,
    ImprovementLoop,
    Note,
    NoteDimension,
    Product,
    Project,
    ProjectEvent,
    ProjectReflection,
    SafetyAssessment,
    SafetyCheckpoint,
    SafetyHypothesisLink,
    ScaleDefinition,
    User,
)
from .safety_services import safety_result
from .services import get_project

EXPORT_SCHEMA_VERSION = "1.0"
WARNING = "Prototype profiles represent intended or observed prototype behavior, not established production quality or business impact."
FONT_PATH = Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")


def _json_value(value):
    if isinstance(value, (UUID, datetime, date)):
        return str(value)
    return value


def _record(model, item):
    return {column.name: _json_value(getattr(item, column.name)) for column in model.__table__.columns}


def build_project_export(db: Session, actor: User, project_id: UUID) -> dict:
    project = get_project(db, actor, project_id)
    hypotheses = list(db.scalars(select(Hypothesis).where(Hypothesis.project_id == project_id).order_by(Hypothesis.created_at, Hypothesis.id)))
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
    safety = db.scalar(select(SafetyAssessment).where(SafetyAssessment.project_id == project_id))
    safety_checkpoints = list(db.scalars(select(SafetyCheckpoint).where(SafetyCheckpoint.assessment_id == safety.id))) if safety else []
    loops = list(db.scalars(select(ImprovementLoop).where(ImprovementLoop.project_id == project_id).order_by(ImprovementLoop.created_at, ImprovementLoop.id)))
    sources = list(db.scalars(select(HypothesisSource).where(HypothesisSource.hypothesis_id.in_(hypothesis_ids)))) if hypothesis_ids else []
    safety_links = list(db.scalars(select(SafetyHypothesisLink).where(SafetyHypothesisLink.hypothesis_id.in_(hypothesis_ids)))) if hypothesis_ids else []
    relations = list(db.scalars(select(HypothesisRelation).where(HypothesisRelation.project_id == project_id)))
    history = db.execute(
        select(ProjectEvent, User.username)
        .outerjoin(User, User.id == ProjectEvent.actor_user_id)
        .where(ProjectEvent.project_id == project_id)
        .order_by(ProjectEvent.created_at)
    ).all()
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
        "hypothesis_sources": [_record(HypothesisSource, item) for item in sources],
        "experiments": [_record(Experiment, item) for item in experiments],
        "reflections": [_record(ProjectReflection, item) for item in reflections],
        "safety_assessment": {**_record(SafetyAssessment, safety), "checkpoints": [_record(SafetyCheckpoint, item) for item in safety_checkpoints], "coverage_summary": safety_result([{"key": item.checkpoint_key, "coverage": item.coverage, "maturity": item.maturity} for item in safety_checkpoints], safety.critical_risk)} if safety else None,
        "safety_hypothesis_links": [_record(SafetyHypothesisLink, item) for item in safety_links],
        "improvement_loops": [{**_record(ImprovementLoop, item), "learning_loop": index == 0, "capabilities": json.loads(item.capabilities_json), "change_scopes": json.loads(item.change_scopes_json), "classification": classify_loop({key: answer["answer"] for key, answer in json.loads(item.capabilities_json).items()}, item.release_approval, item.success_checks, item.rollback, item.approval_boundary)} for index, item in enumerate(loops)],
        "project_history": [
            {
                "id": str(event.id),
                "actor": username or ("Former user" if event.actor_user_id else "System"),
                "event_type": event.event_type,
                "entity_type": event.entity_type,
                "entity_id": event.entity_id,
                "summary": event.summary,
                "details": json.loads(event.details_json or "{}"),
                "created_at": _json_value(event.created_at),
            }
            for event, username in history
        ],
    }


def export_project_json(db: Session, actor: User, project_id: UUID) -> str:
    return json.dumps(build_project_export(db, actor, project_id), ensure_ascii=False, indent=2)


def export_project_markdown(db: Session, actor: User, project_id: UUID) -> str:
    return markdown_report(build_project_export(db, actor, project_id))


def _pdf_text(value: object, unicode_font: bool) -> str:
    text = str(value or "")
    return text if unicode_font else text.encode("latin-1", "replace").decode("latin-1")


def _draw_radar(pdf: FPDF, document: dict, x: float, y: float, size: float, font: str) -> None:
    labels = ["conversational", "specialization", "autonomy", "accessibility", "explainability"]
    scores = {item["dimension_key"]: item["score"] for item in document["dimension_assessments"] if item["status"] == "estimated"}
    baseline = {}
    if document["comparison_snapshots"]:
        raw = document["comparison_snapshots"][-1].get("frozen_profile") or "{}"
        try:
            frozen = json.loads(raw) if isinstance(raw, str) else raw
            baseline = {key: None if not frozen.get(key, {}).get("compatible", True) else frozen.get(key, {}).get("median") for key in labels}
        except (TypeError, json.JSONDecodeError):
            baseline = {}
    cx, cy, radius = x + size / 2, y + size / 2, size * 0.38
    points = []
    baseline_points = []
    pdf.set_draw_color(180, 180, 180)
    for index, label in enumerate(labels):
        angle = -math.pi / 2 + index * 2 * math.pi / len(labels)
        ax, ay = cx + radius * math.cos(angle), cy + radius * math.sin(angle)
        pdf.line(cx, cy, ax, ay)
        value = scores.get(label)
        points.append(None if value is None else (cx + radius * value / 5 * math.cos(angle), cy + radius * value / 5 * math.sin(angle)))
        base = baseline.get(label)
        baseline_points.append(None if base is None else (cx + radius * base / 5 * math.cos(angle), cy + radius * base / 5 * math.sin(angle)))
        pdf.set_xy(ax - 12, ay - 3)
        pdf.set_font(font, size=7)
        pdf.cell(24, 4, _pdf_text(label.title(), font == "Report"), align="C")
    for ring in range(1, 6):
        ring_points = []
        for index in range(len(labels)):
            angle = -math.pi / 2 + index * 2 * math.pi / len(labels)
            ring_points.append((cx + radius * ring / 5 * math.cos(angle), cy + radius * ring / 5 * math.sin(angle)))
        for index in range(len(ring_points)):
            pdf.line(*ring_points[index], *ring_points[(index + 1) % len(ring_points)])
    for plot_points, color in ((points, (31, 119, 180)), (baseline_points, (214, 39, 40))):
        pdf.set_draw_color(*color)
        for index in range(len(plot_points)):
            start, end = plot_points[index], plot_points[(index + 1) % len(plot_points)]
            if start is not None and end is not None:
                pdf.line(*start, *end)


def _draw_priority_matrix(pdf: FPDF, document: dict, x: float, y: float, width: float, height: float, font: str) -> None:
    pdf.set_fill_color(234, 244, 241)
    pdf.rect(x, y, width / 2, height / 2, style="F")
    pdf.set_draw_color(60, 60, 60)
    pdf.rect(x, y, width, height)
    pdf.set_draw_color(200, 215, 219)
    pdf.line(x + width / 2, y, x + width / 2, y + height)
    pdf.line(x, y + height / 2, x + width, y + height / 2)
    pdf.set_font(font, size=8)
    pdf.set_text_color(25, 44, 57)
    pdf.set_xy(x, y + height + 1)
    pdf.cell(width, 4, "Evidence provided (0-10)", align="C")
    pdf.set_xy(x, y - 5)
    pdf.cell(width, 4, "Risk to product (0-10)", align="C")
    supporting = [item for item in document["hypotheses"] if item["kind"] == "supporting" and item["archived_at"] is None]
    for value in (0, 5, 10):
        pdf.set_xy(x + value / 10 * width - 3, y + height + 5)
        pdf.cell(6, 4, str(value), align="C")
        pdf.set_xy(x - 9, y + height - value / 10 * height - 2)
        pdf.cell(7, 4, str(value), align="R")
    for index, hypothesis in enumerate(supporting, start=1):
        evidence = min(10, max(0, float(hypothesis.get("priority_evidence", 0))))
        risk = min(10, max(0, float(hypothesis.get("priority_risk", 0))))
        px = x + evidence / 10 * width
        py = y + height - risk / 10 * height
        pdf.set_fill_color(31, 119, 180)
        pdf.ellipse(px - 2, py - 2, 4, 4, style="F")
        pdf.set_xy(px + 2, py - 3)
        pdf.cell(10, 4, f"H{index}")


def export_project_pdf(db: Session, actor: User, project_id: UUID) -> bytes:
    return pdf_report(build_project_export(db, actor, project_id), _draw_radar, _draw_priority_matrix)


def write_export_files(db: Session, actor: User, project_id: UUID) -> tuple[str, str, str]:
    get_project(db, actor, project_id)
    directory = Path(tempfile.gettempdir()) / "aipm-toolkit-exports"
    directory.mkdir(mode=0o700, exist_ok=True)
    json_path = directory / f"project-{project_id}.json"
    markdown_path = directory / f"project-{project_id}.md"
    pdf_path = directory / f"product-{project_id}.pdf"
    json_path.write_text(export_project_json(db, actor, project_id), encoding="utf-8")
    markdown_path.write_text(export_project_markdown(db, actor, project_id), encoding="utf-8")
    pdf_path.write_bytes(export_project_pdf(db, actor, project_id))
    return str(json_path), str(markdown_path), str(pdf_path)
