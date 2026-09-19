import json
import math
from pathlib import Path
from statistics import median
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .auth import AuthorizationError
from .dimensions import DIMENSION_KEYS
from .models import BaselineAssessment, BaselineDataset, ComparisonSnapshot, Product, Role, User
from .services import get_project


def validate_manifest(manifest: dict | None) -> dict:
    manifest = manifest or {}
    source_type = manifest.get("source_type", "instructor_reference")
    cohort_label = manifest.get("cohort_label", "Legacy instructor reference")
    aliases = manifest.get("aliases", {})
    scale_versions = manifest.get("scale_versions", {key: (0 if key == "autonomy" else 1) for key in DIMENSION_KEYS})
    if not isinstance(source_type, str) or not source_type.strip() or not isinstance(cohort_label, str) or not cohort_label.strip():
        raise ValueError("Manifest source_type and cohort_label are required")
    if not isinstance(aliases, dict) or not all(isinstance(key, str) and isinstance(value, str) for key, value in aliases.items()):
        raise ValueError("Manifest aliases must be a string-to-string map")
    if not isinstance(scale_versions, dict) or set(scale_versions) - set(DIMENSION_KEYS) or not all(isinstance(value, int) for value in scale_versions.values()):
        raise ValueError("Manifest scale_versions must use recognized dimensions and integer versions")
    return {"source_type": source_type.strip(), "cohort_label": cohort_label.strip(), "aliases": aliases, "scale_versions": scale_versions}


def _valid_score(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and 0 <= value <= 5


def _percentile(values: list[float], fraction: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    position = (len(ordered) - 1) * fraction
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def import_legacy_reference_json(db: Session, directory: str | Path, cohort_label: str = "Legacy instructor reference", manifest: dict | None = None) -> dict:
    directory = Path(directory)
    metadata = validate_manifest(manifest)
    if manifest is None:
        metadata["cohort_label"] = cohort_label
    report = {"files": 0, "records": 0, "invalid_values": [], "products": [], "skipped_published": []}
    for path in sorted(directory.glob("*.json")):
        report["files"] += 1
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            report["invalid_values"].append({"file": path.name, "error": str(exc)})
            continue
        source_product_name = str(payload.get("product_name", "")).strip()
        product_name = metadata["aliases"].get(source_product_name, source_product_name)
        scores = payload.get("scores")
        if not product_name or not isinstance(scores, dict):
            report["invalid_values"].append({"file": path.name, "error": "Missing product_name or scores"})
            continue
        product = db.scalar(select(Product).where(Product.display_name == product_name))
        if product is None:
            product = Product(display_name=product_name, aliases=product_name)
            db.add(product)
            db.flush()
        dataset = db.scalar(select(BaselineDataset).where(BaselineDataset.product_id == product.id, BaselineDataset.source_type == metadata["source_type"], BaselineDataset.cohort_label == metadata["cohort_label"]))
        if dataset is None:
            dataset = BaselineDataset(product_id=product.id, source_type=metadata["source_type"], cohort_label=metadata["cohort_label"], scale_version=1, scale_versions=json.dumps(metadata["scale_versions"]), provenance_notes="Imported through a manifest; scope and date are not inferred from file metadata.")
            db.add(dataset)
            db.flush()
        elif dataset.published:
            report["skipped_published"].append({"file": path.name, "product": product_name, "reason": "Published datasets are immutable; import as a replacement version."})
            continue
        source_id = path.name
        raw_record = json.dumps(payload, ensure_ascii=False, sort_keys=True)
        for key in DIMENSION_KEYS:
            raw_value = scores.get(key)
            score = float(raw_value) if _valid_score(raw_value) else None
            if raw_value is not None and score is None:
                report["invalid_values"].append({"file": path.name, "dimension": key, "value": str(raw_value)})
            existing = db.scalar(select(BaselineAssessment).where(BaselineAssessment.dataset_id == dataset.id, BaselineAssessment.source_record_id == source_id, BaselineAssessment.dimension_key == key))
            if existing is None:
                db.add(BaselineAssessment(dataset_id=dataset.id, source_record_id=source_id, dimension_key=key, score=score, original_value=None if raw_value is None else str(raw_value), raw_record=raw_record))
            else:
                existing.score = score
                existing.original_value = None if raw_value is None else str(raw_value)
                existing.raw_record = raw_record
        report["records"] += 1
        report["products"].append(product_name)
    db.commit()
    return report


def preview_legacy_reference_json(directory: str | Path, manifest: dict | None = None) -> dict:
    directory = Path(directory)
    metadata = validate_manifest(manifest)
    report = {"files": 0, "records": 0, "invalid_values": [], "products": [], "source_type": metadata["source_type"], "cohort_label": metadata["cohort_label"]}
    for path in sorted(directory.glob("*.json")):
        report["files"] += 1
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            report["invalid_values"].append({"file": path.name, "error": str(exc)})
            continue
        source_name = str(payload.get("product_name", "")).strip()
        scores = payload.get("scores")
        if not source_name or not isinstance(scores, dict):
            report["invalid_values"].append({"file": path.name, "error": "Missing product_name or scores"})
            continue
        name = metadata["aliases"].get(source_name, source_name)
        report["records"] += 1
        report["products"].append(name)
        for key in DIMENSION_KEYS:
            value = scores.get(key)
            if value is not None and not _valid_score(value):
                report["invalid_values"].append({"file": path.name, "dimension": key, "value": str(value)})
    return report


def published_products(db: Session) -> list[Product]:
    return list(db.scalars(select(Product).join(BaselineDataset).where(BaselineDataset.published.is_(True)).distinct().order_by(Product.display_name)))


def published_datasets(db: Session) -> list[tuple[str, UUID]]:
    rows = db.execute(select(Product.display_name, BaselineDataset.id).join(BaselineDataset).where(BaselineDataset.published.is_(True)).order_by(Product.display_name)).all()
    return [(name, dataset_id) for name, dataset_id in rows]


def publish_all_reference_datasets(db: Session, cohort_label: str = "Legacy instructor reference") -> None:
    datasets = db.scalars(select(BaselineDataset).where(BaselineDataset.cohort_label == cohort_label)).all()
    for dataset in datasets:
        dataset.published = True
    db.commit()


def create_replacement_dataset(db: Session, actor: User, dataset_id: UUID, reason: str) -> BaselineDataset:
    from .auth import require_role
    require_role(actor, Role.INSTRUCTOR)
    original = db.get(BaselineDataset, dataset_id)
    if original is None or not original.published:
        raise ValueError("Only a published dataset can be replaced")
    latest = db.scalar(select(func.max(BaselineDataset.version)).where(BaselineDataset.product_id == original.product_id, BaselineDataset.source_type == original.source_type, BaselineDataset.cohort_label == original.cohort_label)) or original.version
    replacement = BaselineDataset(product_id=original.product_id, source_type=original.source_type, cohort_label=original.cohort_label, scale_version=original.scale_version, scale_versions=original.scale_versions, version=latest + 1, replacement_reason=reason.strip(), provenance_notes=f"Replacement of dataset version {original.version}: {reason.strip()}")
    db.add(replacement)
    db.commit()
    return replacement


def aggregate_dataset(db: Session, dataset_id: UUID) -> dict:
    dataset = db.get(BaselineDataset, dataset_id)
    if dataset is None or not dataset.published:
        raise AuthorizationError("Baseline dataset is not published")
    output = {}
    for key in DIMENSION_KEYS:
        values = list(db.scalars(select(BaselineAssessment.score).where(BaselineAssessment.dataset_id == dataset_id, BaselineAssessment.dimension_key == key)))
        valid = [value for value in values if value is not None and _valid_score(value)]
        output[key] = {"count": len(valid), "mean": sum(valid) / len(valid) if valid else None, "median": median(valid) if valid else None, "minimum": min(valid) if valid else None, "maximum": max(valid) if valid else None, "p25": _percentile(valid, 0.25), "p75": _percentile(valid, 0.75)}
    return output


def select_comparator(db: Session, actor: User, project_id: UUID, dataset_id: UUID, purpose: str, scope_explanation: str = "") -> ComparisonSnapshot:
    get_project(db, actor, project_id)
    dataset = db.get(BaselineDataset, dataset_id)
    if dataset is None or not dataset.published:
        raise AuthorizationError("Baseline dataset is not available")
    if purpose not in {"task_comparator", "design_contrast"}:
        raise ValueError("Invalid comparison purpose")
    aggregates = aggregate_dataset(db, dataset.id)
    scale_versions = json.loads(dataset.scale_versions or "{}")
    frozen_profile = {key: {"median": values["median"], "p25": values["p25"], "p75": values["p75"], "count": values["count"], "compatible": scale_versions.get(key, 1) == 1} for key, values in aggregates.items()}
    snapshot = ComparisonSnapshot(project_id=project_id, product_id=dataset.product_id, dataset_id=dataset.id, purpose=purpose, scope_explanation=scope_explanation, frozen_profile=json.dumps(frozen_profile, sort_keys=True))
    db.add(snapshot)
    db.commit()
    return snapshot
