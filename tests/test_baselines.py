import json

import pytest
from sqlalchemy import select

from aipm_toolkit.auth import AuthorizationError, hash_password
from aipm_toolkit.baseline_services import (
    aggregate_dataset,
    import_legacy_reference_json,
    publish_all_reference_datasets,
    select_comparator,
)
from aipm_toolkit.models import BaselineDataset, Course, Role, Team, User
from aipm_toolkit.services import create_project


def team_user(db, alias="baseline-team"):
    course = Course(name=f"Course {alias}")
    db.add(course)
    db.flush()
    team = Team(course_id=course.id, alias=alias)
    db.add(team)
    db.flush()
    user = User(username=alias, password_hash=hash_password("P" * 16), role=Role.TEAM.value, team_id=team.id)
    db.add(user)
    db.commit()
    return user


def test_import_preserves_zero_excludes_identity_and_aggregates(db, tmp_path):
    source = tmp_path / "chatgpt.json"
    source.write_text(json.dumps({"username": "private-name", "product_name": "ChatGPT", "scores": {"conversational": 0, "specialization": 2.5, "autonomy": 3, "accessibility": 4, "explainability": 2}}), encoding="utf-8")
    report = import_legacy_reference_json(db, tmp_path)
    assert report["records"] == 1
    dataset = db.scalar(select(BaselineDataset))
    with pytest.raises(AuthorizationError):
        aggregate_dataset(db, dataset.id)
    publish_all_reference_datasets(db)
    aggregate = aggregate_dataset(db, dataset.id)
    assert aggregate["conversational"]["median"] == 0
    assert "private-name" not in str(aggregate)


def test_comparator_must_be_published_and_is_project_scoped(db, tmp_path):
    source = tmp_path / "one.json"
    source.write_text(json.dumps({"product_name": "Example", "scores": {key: 1 for key in ("conversational", "specialization", "autonomy", "accessibility", "explainability")}}), encoding="utf-8")
    user = team_user(db)
    project = create_project(db, user, "Prototype")
    import_legacy_reference_json(db, tmp_path)
    dataset = db.scalar(select(BaselineDataset))
    with pytest.raises(AuthorizationError):
        select_comparator(db, user, project.id, dataset.id, "task_comparator")
    publish_all_reference_datasets(db)
    snapshot = select_comparator(db, user, project.id, dataset.id, "task_comparator", "Same task")
    assert snapshot.project_id == project.id


def test_published_dataset_is_not_overwritten_on_reimport(db, tmp_path):
    source = tmp_path / "immutable.json"
    source.write_text(json.dumps({"product_name": "Immutable", "scores": {key: 1 for key in ("conversational", "specialization", "autonomy", "accessibility", "explainability")}}), encoding="utf-8")
    first = import_legacy_reference_json(db, tmp_path)
    assert first["records"] == 1
    publish_all_reference_datasets(db)
    source.write_text(json.dumps({"product_name": "Immutable", "scores": {key: 4 for key in ("conversational", "specialization", "autonomy", "accessibility", "explainability")}}), encoding="utf-8")
    second = import_legacy_reference_json(db, tmp_path)
    assert second["records"] == 0
    assert second["skipped_published"]
