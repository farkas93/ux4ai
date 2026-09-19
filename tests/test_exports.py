import json

import pytest

from aipm_toolkit.auth import AuthorizationError, hash_password
from aipm_toolkit.export_services import (
    export_project_json,
    export_project_markdown,
    export_project_pdf,
)
from aipm_toolkit.hypothesis_services import create_note
from aipm_toolkit.models import Course, Role, Team, User
from aipm_toolkit.services import create_project, update_project


def user_project(db, alias="export-team"):
    course = Course(name=f"Course {alias}")
    db.add(course)
    db.flush()
    team = Team(course_id=course.id, alias=alias)
    db.add(team)
    db.flush()
    user = User(username=alias, password_hash=hash_password("P" * 16), role=Role.TEAM.value, team_id=team.id)
    db.add(user)
    db.commit()
    return user, create_project(db, user, "Éxample AI")


def test_exports_are_versioned_complete_and_unicode_safe(db):
    user, project = user_project(db)
    update_project(db, user, project.id, project.revision, short_description="Line one\nLine two", target_user="Teams")
    create_note(db, user, project.id, "question", "Welche Annahme müssen wir testen?\nNext line.")
    payload = json.loads(export_project_json(db, user, project.id))
    assert payload["schema_version"] == "1.0"
    assert "Éxample AI" in payload["project"]["product_name"]
    assert "Welche Annahme" in payload["notes"][0]["text"]
    assert "password_hash" not in export_project_json(db, user, project.id)
    assert "username" not in export_project_json(db, user, project.id)
    report = export_project_markdown(db, user, project.id)
    assert "Prototype profiles represent intended" in report
    assert "Open Questions" in report
    pdf = export_project_pdf(db, user, project.id)
    assert pdf.startswith(b"%PDF")
    assert len(pdf) > 1000


def test_exports_enforce_project_authorization(db):
    _, project_a = user_project(db, "a")
    user_b, _ = user_project(db, "b")
    with pytest.raises(AuthorizationError):
        export_project_json(db, user_b, project_a.id)
