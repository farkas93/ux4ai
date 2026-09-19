import json
import math
import tempfile
from datetime import date, datetime
from pathlib import Path
from uuid import UUID

from fpdf import FPDF
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
FONT_PATH = Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")


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
        lines.append(f"- **{hypothesis['kind']}**: {hypothesis['statement']} (risk: {hypothesis['priority_risk']}/10, evidence: {hypothesis['priority_evidence']}/10)")
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


def _pdf_font(pdf: FPDF) -> str:
    if FONT_PATH.exists():
        pdf.add_font("DejaVu", fname=str(FONT_PATH))
        return "DejaVu"
    return "Helvetica"


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
        pdf.cell(24, 4, _pdf_text(label, font == "DejaVu"), align="C")
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
    pdf.set_draw_color(60, 60, 60)
    pdf.rect(x, y, width, height)
    pdf.set_font(font, size=8)
    pdf.set_xy(x, y + height + 1)
    pdf.cell(width, 4, "Evidence provided (0-10)", align="C")
    pdf.set_xy(x, y - 5)
    pdf.cell(width, 4, "Risk to product (0-10)", align="C")
    supporting = [item for item in document["hypotheses"] if item["kind"] == "supporting"]
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
    document = build_project_export(db, actor, project_id)
    project = document["project"]
    main = next((item for item in document["hypotheses"] if item["kind"] == "main"), None)
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=14)
    pdf.add_page()
    font = _pdf_font(pdf)
    unicode_font = font == "DejaVu"
    pdf.set_font(font, size=18)
    pdf.multi_cell(0, 9, _pdf_text(project["product_name"], unicode_font), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font(font, size=9)
    pdf.multi_cell(0, 5, _pdf_text(WARNING, unicode_font), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)
    pdf.set_font(font, size=12)
    pdf.cell(0, 7, "Product setup", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font(font, size=9)
    for label, value in (("Description", project["short_description"]), ("Target user", project["target_user"]), ("Job to be done", project["job_to_be_done"]), ("Current problem", project["current_problem"]), ("Main value hypothesis", (main or {}).get("statement", ""))):
        pdf.multi_cell(0, 5, _pdf_text(f"{label}: {value}", unicode_font), new_x="LMARGIN", new_y="NEXT")
    pdf.add_page()
    pdf.set_font(font, size=14)
    pdf.cell(0, 8, "Dimension profile", new_x="LMARGIN", new_y="NEXT")
    _draw_radar(pdf, document, 20, 30, 170, font)
    pdf.set_y(205)
    pdf.set_font(font, size=8)
    pdf.multi_cell(0, 4, "Blue: current product profile. Red: historical comparator median. Gaps mean unknown or incompatible.", new_x="LMARGIN", new_y="NEXT")
    pdf.add_page()
    pdf.set_font(font, size=14)
    pdf.cell(0, 8, "Risk and evidence matrix", new_x="LMARGIN", new_y="NEXT")
    _draw_priority_matrix(pdf, document, 25, 35, 155, 110, font)
    pdf.set_y(155)
    pdf.set_font(font, size=9)
    supporting = [item for item in document["hypotheses"] if item["kind"] == "supporting"]
    ranked = sorted(supporting, key=lambda item: (-(float(item.get("priority_risk", 0)) + (10 - float(item.get("priority_evidence", 0)))), item["created_at"]))
    for rank, hypothesis in enumerate(ranked, start=1):
        line = f"{rank}. H{supporting.index(hypothesis) + 1}: risk {hypothesis['priority_risk']}/10, evidence {hypothesis['priority_evidence']}/10 - {hypothesis['statement']}"
        pdf.multi_cell(0, 5, _pdf_text(line, unicode_font), new_x="LMARGIN", new_y="NEXT")
    pdf.add_page()
    pdf.set_font(font, size=14)
    pdf.cell(0, 8, "Questions, assumptions, and experiments", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font(font, size=9)
    for note in document["notes"]:
        pdf.multi_cell(0, 5, _pdf_text(f"[{note['note_type']}] {note['text']}", unicode_font), new_x="LMARGIN", new_y="NEXT")
    for experiment in document["experiments"]:
        pdf.multi_cell(0, 5, _pdf_text(f"[experiment: {experiment['status']}] {experiment['title']} - criterion: {experiment['success_criterion']}", unicode_font), new_x="LMARGIN", new_y="NEXT")
    return bytes(pdf.output())


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
