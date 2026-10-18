import json
from pathlib import Path
from urllib.parse import urlparse

from sqlalchemy import select

from aipm_toolkit import import_baselines
from aipm_toolkit.baseline_services import (
    aggregate_dataset,
    import_legacy_reference_json,
    preview_legacy_reference_json,
    publish_all_reference_datasets,
    published_datasets,
    select_comparator,
    validate_manifest,
)
from aipm_toolkit.models import (
    BaselineAssessment,
    BaselineDataset,
    Course,
    Product,
    Role,
    Team,
    User,
)
from aipm_toolkit.services import create_project
from aipm_toolkit.upload_services import preview_upload, publish_upload

BASELINE = Path(__file__).resolve().parents[1] / "baseline"


def test_catalog_is_complete_scoped_and_current_rubric_compatible():
    manifest = validate_manifest(json.loads((BASELINE / "import_manifest.json").read_text()))
    paths = sorted((BASELINE / "products").glob("*.json"))
    assert {path.stem for path in paths} == {
        "chatgpt", "claude", "google_gemini", "microsoft_365_copilot", "perplexity",
        "gemini_notebook", "deepl_translator", "grammarly", "canva_ai", "adobe_firefly",
        "github_copilot", "otter", "cursor", "fin", "zapier_agents",
    }
    keys = set(manifest["scale_versions"])
    assert keys == {"conversational", "specialization", "autonomy", "accessibility", "explainability"}
    assert all(version == 1 for version in manifest["scale_versions"].values())
    names = set()
    for path in paths:
        payload = json.loads(path.read_text())
        assert payload["product_name"] not in names
        names.add(payload["product_name"])
        assert payload["assessment_date"] == "2026-10-18"
        assert payload["assessment_basis"] == "ai_assisted_documentation_review"
        assert payload["live_testing_performed"] is False
        assert payload["scope"]["experience"] and payload["scope"]["configuration"]
        assert set(payload["scores"]) == set(payload["dimensions"]) == keys
        assert all(isinstance(score, (int, float)) and not isinstance(score, bool) and 0 <= score <= 5 for score in payload["scores"].values())
        assert payload["scores"]["autonomy"] < 5
        source_ids = {source["id"] for source in payload["sources"]}
        for source in payload["sources"]:
            assert urlparse(source["url"]).scheme == "https"
            assert source["accessed_on"] == payload["assessment_date"]
        for dimension in payload["dimensions"].values():
            assert dimension["rationale"] and dimension["uncertainty"]
            assert dimension["confidence"] in {"low", "medium", "high"}
            assert dimension["evidence"] and set(dimension["evidence"]).issubset(source_ids)
        assert "no live" in payload["provenance_notes"].lower() or "no customer" in payload["provenance_notes"].lower()
        assert "username" not in payload and "password" not in payload
    preview = preview_legacy_reference_json(BASELINE / "products", manifest)
    assert preview["files"] == preview["records"] == 15
    assert preview["invalid_values"] == []


def test_catalog_upload_publishes_scores_and_preserves_provenance(db, tmp_path, monkeypatch):
    monkeypatch.setattr("aipm_toolkit.upload_services.BATCH_ROOT", tmp_path / "uploads")
    instructor = User(username="catalog-instructor", role=Role.INSTRUCTOR.value, password_hash="not-used")
    db.add(instructor)
    db.commit()
    manifest = json.loads((BASELINE / "import_manifest.json").read_text())
    # Existing published data is distinct from the new dated, scoped references.
    legacy = Product(display_name="ChatGPT")
    db.add(legacy)
    db.flush()
    original = BaselineDataset(product_id=legacy.id, source_type="instructor_reference", cohort_label="Legacy instructor reference", scale_version=1, published=True)
    db.add(original)
    db.commit()
    paths = sorted((BASELINE / "products").glob("*.json"))
    batch, preview = preview_upload(db, instructor, [str(path) for path in paths], str(BASELINE / "import_manifest.json"))
    assert preview["records"] == 15 and preview["invalid_values"] == []
    report = publish_upload(db, instructor, batch.id)
    assert report["records"] == 15 and report["invalid_values"] == []
    assert batch.status == "published"
    datasets = list(db.scalars(select(BaselineDataset).where(BaselineDataset.cohort_label == manifest["cohort_label"])))
    assert len(datasets) == 15 and all(dataset.published for dataset in datasets)
    assert len(published_datasets(db)) == 16
    assert original.cohort_label == "Legacy instructor reference" and original.published is True
    expected = {json.loads(path.read_text())["product_name"]: json.loads(path.read_text()) for path in paths}
    for dataset in datasets:
        name = db.get(Product, dataset.product_id).display_name
        payload = expected[name]
        assert dataset.provenance_notes == payload["provenance_notes"]
        assert json.loads(dataset.scale_versions) == manifest["scale_versions"]
        aggregate = aggregate_dataset(db, dataset.id)
        assert {key: value["median"] for key, value in aggregate.items()} == payload["scores"]
        assert all(value["count"] == 1 for value in aggregate.values())
        records = list(db.scalars(select(BaselineAssessment).where(BaselineAssessment.dataset_id == dataset.id)))
        assert len(records) == 5
        assert all(json.loads(record.raw_record) == payload for record in records)
    repeated = import_legacy_reference_json(db, BASELINE / "products", manifest=manifest)
    assert repeated["records"] == 0 and len(repeated["skipped_published"]) == 15


def test_cli_publish_uses_manifest_cohort_without_requiring_duplicate_flag(db, monkeypatch):
    monkeypatch.setattr(import_baselines, "engine", db.get_bind())
    monkeypatch.setattr(import_baselines, "SessionLocal", lambda: db)
    monkeypatch.setattr("sys.argv", [
        "import_baselines", str(BASELINE / "products"), "--manifest", str(BASELINE / "import_manifest.json"), "--publish",
    ])
    import_baselines.main()
    datasets = list(db.scalars(select(BaselineDataset)))
    assert len(datasets) == 15 and all(dataset.published for dataset in datasets)


def test_current_baseline_autonomy_is_visible_in_comparator(db):
    manifest = json.loads((BASELINE / "import_manifest.json").read_text())
    import_legacy_reference_json(db, BASELINE / "products", manifest=manifest)
    publish_all_reference_datasets(db, manifest["cohort_label"])
    course = Course(name="Catalog comparison course")
    db.add(course)
    db.flush()
    team = Team(course_id=course.id, alias="catalog-team")
    db.add(team)
    db.flush()
    actor = User(username="catalog-team", role=Role.TEAM.value, team_id=team.id, password_hash="not-used")
    db.add(actor)
    db.commit()
    project = create_project(db, actor, "Catalog comparison prototype")
    dataset = db.scalar(select(BaselineDataset).join(Product).where(Product.display_name == "Cursor · coding agent"))
    snapshot = select_comparator(db, actor, project.id, dataset.id, "design_contrast", "Compare scoped action autonomy")
    frozen = json.loads(snapshot.frozen_profile)
    assert frozen["autonomy"]["compatible"] is True
    assert frozen["autonomy"]["median"] == 3.5
