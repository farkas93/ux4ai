import json
from functools import lru_cache
from pathlib import Path

LOCALE_DIR = Path(__file__).with_name("locales")
SUPPORTED_LANGUAGES = ("en", "de")
REQUIRED_KEYS = {"language_name", "sections", "sections.Project Setup", "sections.Assessment", "sections.Backlog creator", "sections.Prioritization", "sections.Summary & Export", "labels"}


@lru_cache
def load_catalog(language: str) -> dict:
    if language not in SUPPORTED_LANGUAGES:
        language = "en"
    path = LOCALE_DIR / f"{language}.json"
    try:
        catalog = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        if language == "en":
            raise RuntimeError(f"Default language resource is unavailable: {path}") from exc
        return load_catalog("en")
    sections = catalog.get("sections")
    labels = catalog.get("labels")
    if not isinstance(sections, dict) or not isinstance(labels, dict) or not catalog.get("language_name"):
        raise RuntimeError(f"Invalid language resource: {path}")
    missing = {key.split(".", 1)[1] for key in REQUIRED_KEYS if key.startswith("sections.")} - set(sections)
    if missing:
        raise RuntimeError(f"Missing translations in {path}: {sorted(missing)}")
    return catalog
