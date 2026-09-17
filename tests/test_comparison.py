import json

from sqlalchemy import select

from aipm_toolkit.auth import hash_password
from aipm_toolkit.baseline_services import (
    import_legacy_reference_json,
    publish_all_reference_datasets,
    select_comparator,
)
from aipm_toolkit.comparison_services import comparison_rows
from aipm_toolkit.models import BaselineDataset, Course, Role, Team, User
from aipm_toolkit.services import create_project


def test_comparison_snapshot_freezes_profile_and_preserves_unknown_gap(db, tmp_path):
    course = Course(name="Comparison course")
    db.add(course)
    db.flush()
    team = Team(course_id=course.id, alias="comparison-team")
    db.add(team)
    db.flush()
    user = User(username="comparison-team", password_hash=hash_password("P" * 16), role=Role.TEAM.value, team_id=team.id)
    db.add(user)
    db.commit()
    project = create_project(db, user, "Comparison product")
    source = tmp_path / "product.json"
    source.write_text(json.dumps({"product_name": "Historical", "scores": {key: 2 for key in ("conversational", "specialization", "autonomy", "accessibility", "explainability")}}), encoding="utf-8")
    import_legacy_reference_json(db, tmp_path)
    publish_all_reference_datasets(db)
    dataset = db.scalar(select(BaselineDataset))
    snapshot = select_comparator(db, user, project.id, dataset.id, "design_contrast")
    rows = comparison_rows(db, user, project.id, snapshot.id)
    assert rows[0]["baseline_median"] == 2
    assert rows[0]["our_score"] is None
    assert rows[0]["difference"] is None
    snapshot.frozen_profile = snapshot.frozen_profile.replace("2.0", "4.0")
    db.commit()
    assert comparison_rows(db, user, project.id, snapshot.id)[0]["baseline_median"] == 4
