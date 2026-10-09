import json
import re
import zlib

import pytest

from aipm_toolkit.auth import AuthorizationError, hash_password
from aipm_toolkit.export_services import (
    build_project_export,
    export_project_json,
    export_project_markdown,
    export_project_pdf,
)
from aipm_toolkit.hypothesis_services import create_hypothesis, create_note, set_placement
from aipm_toolkit.improvement_services import QUESTIONS, save_loop
from aipm_toolkit.models import Course, DimensionEstimate, Role, Team, User
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
    assert "Other questions and assumptions" in report
    pdf = export_project_pdf(db, user, project.id)
    assert pdf.startswith(b"%PDF")
    assert len(pdf) > 1000


def test_exports_enforce_project_authorization(db):
    _, project_a = user_project(db, "a")
    user_b, _ = user_project(db, "b")
    with pytest.raises(AuthorizationError):
        export_project_json(db, user_b, project_a.id)


def test_learning_report_preserves_comments_provenance_and_excludes_history(db):
    user, project = user_project(db, "learning-report")
    rationale = "Reasoning repeated for pagination. " * 300 + "FINAL ASSESSMENT COMMENT"
    db.add(DimensionEstimate(project_id=project.id, dimension_key="autonomy", scale_version=1, status="estimated", score=2.0, rationale=rationale))
    db.commit()
    assessment = create_note(db, user, project.id, "question", "Can users spot inaccurate suggestions?", ["autonomy"])
    safety = create_note(db, user, project.id, "assumption", "Users review edits before submitting.", origin_section="safety", origin_key="harms")
    create_note(db, user, project.id, "question", "Do summaries reveal recurring problems?", origin_section="self_improvement")
    hypothesis = create_hypothesis(db, user, project.id, "Showing original text improves error detection", note_id=assessment.id)
    set_placement(db, user, hypothesis.id, hypothesis.revision, 9, 2)
    save_loop(db, user, project.id, None, None, {
        "name": "Review rejected edits", "answers": {key: {"answer": "unknown", "explanation": "Capability explanation for " + key} for key in QUESTIONS},
        "status": "intended", "scopes": [], "recursion_scope": "product_behavior", "release_approval": "unspecified",
        "approval_boundary": "", "success_checks": "", "rollback": "",
    })
    report = export_project_markdown(db, user, project.id)
    for content in (rationale, assessment.text, safety.text, "Do summaries reveal recurring problems?", "Review rejected edits", "Capability explanation for observe", "H1", "Test first", "Risk and evidence"):
        assert content in report
    assert "Risk 5–10" not in report and "Priority 72/100" not in report
    assert "risk 9 × uncertainty" not in report
    assert "## Project History" not in report
    assert "Created product:" not in report
    payload = build_project_export(db, user, project.id)
    assert payload["hypothesis_sources"][0]["note_id"] == str(assessment.id)
    assert payload["project_history"]  # Archival JSON retains history.
    pdf = export_project_pdf(db, user, project.id)
    assert len(re.findall(rb"/Type /Page\b", pdf)) > 10
    streams = []
    for stream in re.findall(rb"stream\n(.*?)\nendstream", pdf, re.DOTALL):
        try:
            streams.append(zlib.decompress(stream))
        except zlib.error:
            continue
    # ASCII fallback and embedded Unicode fonts both retain all content streams.
    assert streams


def test_test_first_quadrant_has_exact_bounds():
    from aipm_toolkit.ui.callbacks import ranked_backlog_from_ui

    _, figure = ranked_backlog_from_ui("id", "A claim", 9, 2)
    quadrant = figure.layout.shapes[0]
    assert (quadrant.x0, quadrant.x1, quadrant.y0, quadrant.y1) == (0, 5, 5, 10)
    assert not any("Test first" in annotation.text for annotation in figure.layout.annotations)
    _, empty = ranked_backlog_from_ui()
    assert (empty.layout.shapes[0].x0, empty.layout.shapes[0].y0) == (0, 5)
