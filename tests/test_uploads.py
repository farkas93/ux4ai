import json

import pytest

from aipm_toolkit.auth import AuthorizationError, hash_password
from aipm_toolkit.models import Role, User
from aipm_toolkit.upload_services import preview_upload, publish_upload


def test_instructor_upload_preview_and_publish(db, tmp_path):
    instructor = User(username="upload-instructor", password_hash=hash_password("P" * 16), role=Role.INSTRUCTOR.value)
    db.add(instructor)
    db.commit()
    source = tmp_path / "source.json"
    source.write_text(json.dumps({"product_name": "Uploaded", "scores": {key: 1 for key in ("conversational", "specialization", "autonomy", "accessibility", "explainability")}}), encoding="utf-8")
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"source_type": "instructor_reference", "cohort_label": "Uploaded cohort", "aliases": {}, "scale_versions": {key: 1 for key in ("conversational", "specialization", "autonomy", "accessibility", "explainability")}}), encoding="utf-8")
    batch, report = preview_upload(db, instructor, [str(source)], str(manifest))
    assert batch.status == "preview"
    assert report["records"] == 1
    published = publish_upload(db, instructor, batch.id)
    assert published["records"] == 1
    assert batch.status == "published"


def test_team_cannot_preview_upload(db, tmp_path):
    team = User(username="upload-team", password_hash=hash_password("P" * 16), role=Role.TEAM.value)
    db.add(team)
    db.commit()
    source = tmp_path / "source.json"
    source.write_text("{}", encoding="utf-8")
    with pytest.raises(AuthorizationError):
        preview_upload(db, team, [str(source)], None)
