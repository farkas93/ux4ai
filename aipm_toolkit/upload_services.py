import json
import shutil
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from .auth import AuthorizationError, require_role
from .baseline_services import (
    import_legacy_reference_json,
    preview_legacy_reference_json,
    publish_all_reference_datasets,
    validate_manifest,
)
from .models import ImportBatch, Role, User

MAX_FILE_BYTES = 2 * 1024 * 1024
MAX_TOTAL_BYTES = 20 * 1024 * 1024
BATCH_ROOT = Path(tempfile.gettempdir()) / "aipm-toolkit-import-batches"

def _files(values):
    if not values:
        return []
    return values if isinstance(values, list) else [values]

def preview_upload(db: Session, actor: User, uploaded_files, manifest_file) -> tuple[ImportBatch, dict]:
    require_role(actor, Role.INSTRUCTOR)
    files = _files(uploaded_files)
    if not files:
        raise ValueError("Upload at least one JSON file")
    manifest = {}
    if manifest_file:
        manifest_path = Path(manifest_file[0] if isinstance(manifest_file, list) else manifest_file)
        if manifest_path.stat().st_size > MAX_FILE_BYTES:
            raise ValueError("Manifest is too large")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest = validate_manifest(manifest)
    batch_id = uuid4()
    directory = BATCH_ROOT / str(batch_id)
    directory.mkdir(mode=0o700, parents=True, exist_ok=False)
    total = 0
    try:
        for index, value in enumerate(files):
            source = Path(value)
            if source.suffix.lower() != ".json":
                raise ValueError("Only JSON uploads are accepted")
            size = source.stat().st_size
            total += size
            if size > MAX_FILE_BYTES or total > MAX_TOTAL_BYTES:
                raise ValueError("Uploaded files exceed the size limit")
            shutil.copyfile(source, directory / f"source-{index}.json")
        report = preview_legacy_reference_json(directory, manifest)
    except Exception:
        shutil.rmtree(directory, ignore_errors=True)
        raise
    batch = ImportBatch(id=batch_id, created_by_user_id=actor.id, source_directory=str(directory), manifest_json=json.dumps(manifest), preview_report_json=json.dumps(report))
    db.add(batch)
    db.commit()
    return batch, report

def publish_upload(db: Session, actor: User, batch_id: UUID) -> dict:
    require_role(actor, Role.INSTRUCTOR)
    batch = db.get(ImportBatch, batch_id)
    if batch is None or batch.created_by_user_id != actor.id:
        raise AuthorizationError("Import batch not found")
    if batch.status != "preview":
        raise ValueError("Import batch has already been published or rejected")
    directory = Path(batch.source_directory)
    if not directory.is_dir():
        raise ValueError("Import batch files are no longer available")
    manifest = json.loads(batch.manifest_json)
    report = import_legacy_reference_json(db, directory, manifest=manifest)
    publish_all_reference_datasets(db, manifest["cohort_label"])
    batch.status = "published"
    batch.published_at = datetime.now(UTC)
    batch.revision += 1
    db.commit()
    return report
