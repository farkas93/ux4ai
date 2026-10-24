"""Immutable application resources and profile-owned writable locations."""

import json
import os
import tempfile
from pathlib import Path

from alembic.config import Config

from .config import get_settings


def resource_path(name: str) -> Path:
    bundled = Path(__file__).with_name("assets") / name
    if bundled.exists():
        return bundled
    # Editable/source checkouts keep migrations and reference sources at root.
    source = Path(__file__).resolve().parents[1] / name
    if source.exists():
        return source
    raise FileNotFoundError(f"Required application resource is missing: {name}")


def migration_config() -> Config:
    config = Config(str(resource_path("alembic.ini")))
    config.set_main_option("script_location", str(resource_path("alembic")))
    config.set_main_option("prepend_sys_path", "")
    return config


def profile_dir() -> Path | None:
    settings = get_settings()
    return settings.data_dir if settings.mode == "desktop" else None


def export_dir() -> Path:
    root = profile_dir()
    return root / "exports" if root else Path(tempfile.gettempdir()) / "aipm-toolkit-exports"


def import_dir() -> Path:
    root = profile_dir()
    return root / "imports" if root else Path(tempfile.gettempdir()) / "aipm-toolkit-import-batches"


def read_preferences() -> dict:
    root = profile_dir()
    if root is None:
        return {}
    try:
        value = json.loads((root / "preferences.json").read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError):
        return {}


def atomic_json(path: Path, document: dict) -> None:
    """Replace a small profile file without exposing a partially written JSON."""
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                         prefix=".pending-", delete=False) as file:
            temporary = Path(file.name)
            json.dump(document, file, ensure_ascii=False, indent=2)
            file.flush()
            os.fsync(file.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
