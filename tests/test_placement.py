import pytest

from aipm_toolkit.auth import RevisionConflict, hash_password
from aipm_toolkit.hypothesis_services import create_hypothesis, create_note, set_placement
from aipm_toolkit.models import Course, Role, Team, User
from aipm_toolkit.services import create_project
from aipm_toolkit.ui.callbacks import (
    load_estimates_from_ui,
    load_experiment_edit_from_ui,
    load_placements_from_ui,
    load_project_from_ui,
    ranked_backlog_from_ui,
)


def user_project(db, alias="placement-team"):
    course = Course(name=f"Course {alias}")
    db.add(course)
    db.flush()
    team = Team(course_id=course.id, alias=alias)
    db.add(team)
    db.flush()
    user = User(username=alias, password_hash=hash_password("P" * 16), role=Role.TEAM.value, team_id=team.id)
    db.add(user)
    db.commit()
    return user, create_project(db, user, "Placement product")


def test_placement_validates_range_and_revision(db):
    user, project = user_project(db)
    hypothesis = create_hypothesis(db, user, project.id, "A claim")
    stale_revision = hypothesis.revision
    with pytest.raises(ValueError):
        set_placement(db, user, hypothesis.id, hypothesis.revision, risk=10.5, evidence=0)
    placed = set_placement(db, user, hypothesis.id, hypothesis.revision, risk=10, evidence=0)
    assert placed.priority_risk == 10
    assert placed.priority_evidence == 0
    with pytest.raises(RevisionConflict):
        set_placement(db, user, hypothesis.id, stale_revision, risk=0, evidence=10)


def test_ranking_puts_high_risk_low_evidence_first(db):
    user, project = user_project(db)
    first = create_hypothesis(db, user, project.id, "Urgent uncertain claim")
    set_placement(db, user, first.id, first.revision, risk=10, evidence=0)
    second = create_hypothesis(db, user, project.id, "Well-evidenced claim")
    set_placement(db, user, second.id, second.revision, risk=0, evidence=10)
    ids = [str(first.id), str(second.id)]
    statements = [first.statement, second.statement]
    risks = [first.priority_risk, second.priority_risk]
    evidences = [first.priority_evidence, second.priority_evidence]
    ranking, _ = ranked_backlog_from_ui(*(ids + statements + risks + evidences))
    assert ranking.index("H1 · Urgent uncertain claim") < ranking.index("H2 · Well-evidenced claim")
    assert "Risk if wrong: 10.0/10 · Evidence available: 0.0/10" in ranking
    assert "Risk if wrong: 0.0/10 · Evidence available: 10.0/10" in ranking
    assert "Priority 100" not in ranking


def test_matrix_ids_match_editors_and_ranking_shows_concise_reasons():
    ranking, figure = ranked_backlog_from_ui(
        "first", "second", "third",
        "Lower priority", "Urgent claim", "Equal priority",
        1, 9, 9,
        8, 1, 1,
        sources=["Question: Can users understand?", "Assumption: Retrieval is private", "Question: What fails?"],
    )
    assert list(figure.data[0].text) == ["H2", "H3", "H1"]
    assert ranking.index("H2 · Urgent claim") < ranking.index("H1 · Lower priority")
    assert ranking.count("TEST ORDER 1") == 2
    assert "Assumption: Retrieval is private" in ranking
    assert "Risk if wrong: 9.0/10 · Evidence available: 1.0/10" in ranking
    assert "Priority" not in ranking
    assert "TEST ORDER 1 · tied" not in ranking
    assert "Test first area" in ranking


def test_ranking_html_escapes_student_content():
    ranking, _ = ranked_backlog_from_ui("id", "<script>alert(1)</script>", 8, 2, sources=["<img src=x>"])
    assert "<script>" not in ranking
    assert "&lt;script&gt;" in ranking
    assert "&lt;img src=x&gt;" in ranking


def test_test_first_label_is_external_to_plot_and_headers_are_evenly_truncated():
    from aipm_toolkit.priority_rules import hypothesis_header
    from aipm_toolkit.ui.shell import build_app

    _ranking, figure = ranked_backlog_from_ui("id", "Long hypothesis claim", 9, 2)
    assert not any("Test first" in annotation.text or "Evidence 0" in annotation.text for annotation in figure.layout.annotations)
    components = build_app().get_config_file()["components"]
    plot_index = next(i for i, item in enumerate(components) if item["type"] == "plot" and item["props"].get("label") == "Risk versus evidence matrix")
    test_first_label = next(i for i, item in enumerate(components) if item["type"] == "markdown" and "Test first" in (item["props"].get("value") or ""))
    assert test_first_label < plot_index
    short = hypothesis_header(1, "Short")
    long = hypothesis_header(12, "A very long hypothesis " * 10)
    assert len(short) < len(long) <= 52
    assert long.startswith("H12 · ") and long.endswith("…")


def test_load_placements_and_estimates_unpack_proper_component_counts(db, monkeypatch):
    _user, project = user_project(db)
    from aipm_toolkit.ui import callbacks as cb_mod
    monkeypatch.setattr(cb_mod, "SessionLocal", lambda: db)

    # Seven components per slot, plus ranking and figure.
    placement_results = load_placements_from_ui("token", str(project.id))
    assert len(placement_results) == 72
    assert not isinstance(placement_results[0], list)

    # load_estimates_from_ui must return exactly 11 flat items: 10 for 5 dimensions (score, reasoning) + list of revisions
    estimates_results = load_estimates_from_ui("token", str(project.id))
    assert len(estimates_results) == 11
    assert not isinstance(estimates_results[0], list)

    # load_project_from_ui must return exactly 8 fields
    project_results = load_project_from_ui("token", str(project.id))
    assert len(project_results) == 8


def test_load_placements_with_populated_hypotheses_does_not_fail_on_str_float(db, monkeypatch):
    user, project = user_project(db, "placed-str-float")
    h1 = create_hypothesis(db, user, project.id, "First supporting claim with text statement")
    set_placement(db, user, h1.id, h1.revision, risk=8.5, evidence=2.0)
    h2 = create_hypothesis(db, user, project.id, "Second supporting claim")
    set_placement(db, user, h2.id, h2.revision, risk=3.0, evidence=7.5)

    from aipm_toolkit.ui import callbacks as cb_mod
    monkeypatch.setattr(cb_mod, "SessionLocal", lambda: db)
    monkeypatch.setattr(cb_mod, "get_authenticated_user", lambda _db, _token: user)

    # Must execute without TypeError: can only concatenate str (not "float") to str
    placement_results = load_placements_from_ui("token", str(project.id))
    assert len(placement_results) == 72
    ranking_text = placement_results[-2]
    assert "First supporting claim" in ranking_text


def test_load_experiment_edit_returns_exact_18_outputs(db, monkeypatch):
    user, _project = user_project(db, "exp-edit")
    from aipm_toolkit.ui import callbacks as cb_mod
    monkeypatch.setattr(cb_mod, "SessionLocal", lambda: db)
    monkeypatch.setattr(cb_mod, "get_authenticated_user", lambda _db, _token: user)

    # When experiment_id is None / empty, must return exactly 18 values (never 17!)
    empty_results = load_experiment_edit_from_ui("token", None)
    assert len(empty_results) == 18

    # When experiment_id does not exist / error, must return exactly 18 values
    error_results = load_experiment_edit_from_ui("token", "00000000-0000-0000-0000-000000000000")
    assert len(error_results) == 18


def test_placement_load_connects_source_question_to_ranked_hypothesis(db, monkeypatch):
    user, project = user_project(db, "priority-provenance")
    note = create_note(db, user, project.id, "question", "Will users understand the clarification?", ["conversational"])
    hypothesis = create_hypothesis(db, user, project.id, "Clarification reduces hand-offs", note_id=note.id)
    from aipm_toolkit.ui import callbacks as cb_mod
    monkeypatch.setattr(cb_mod, "SessionLocal", lambda: db)
    monkeypatch.setattr(cb_mod, "get_authenticated_user", lambda _db, _token: user)
    result = load_placements_from_ui("token", str(project.id))
    assert result[0]["label"].startswith("H1 · Clarification")
    assert result[6] == "Question: Will users understand the clarification?"
    assert "Will users understand the clarification?" in result[-2]
    assert list(result[-1].data[0].text) == ["H1"]
    assert hypothesis.statement in result[-2]
