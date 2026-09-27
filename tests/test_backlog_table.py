from uuid import UUID

from aipm_toolkit.auth import hash_password
from aipm_toolkit.experiment_services import create_experiment
from aipm_toolkit.models import (
    Course,
    Experiment,
    Hypothesis,
    HypothesisDimension,
    HypothesisSource,
    Note,
    NoteDimension,
    ProjectEvent,
    Role,
    Team,
    User,
)
from aipm_toolkit.services import create_project
from aipm_toolkit.ui.callbacks import (
    MAX_BACKLOG_ROWS,
    archive_backlog_row_from_ui,
    dimension_notes_from_ui,
    load_backlog_table_from_ui,
    project_history_from_ui,
    save_backlog_row_from_ui,
    show_next_row_from_ui,
)


def user_project(db, alias="table-team"):
    course = Course(name=f"Course {alias}")
    db.add(course)
    db.flush()
    team = Team(course_id=course.id, alias=alias)
    db.add(team)
    db.flush()
    user = User(username=alias, password_hash=hash_password("P" * 16), role=Role.TEAM.value, team_id=team.id)
    db.add(user)
    db.commit()
    return user, create_project(db, user, "Table Product")


def test_load_backlog_table_unpacks_correct_flat_count(db, monkeypatch):
    user, project = user_project(db)
    from aipm_toolkit.ui import callbacks as cb_mod
    monkeypatch.setattr(cb_mod, "SessionLocal", lambda: db)
    monkeypatch.setattr(cb_mod, "get_authenticated_user", lambda _db, _token: user)

    # 16 slots * 9 components + 1 extra (visible_count) = 145
    results = load_backlog_table_from_ui("token", str(project.id))
    assert len(results) == MAX_BACKLOG_ROWS * 9 + 1
    # Ensure outputs are flat
    assert not isinstance(results[0], (list, tuple))


def test_save_backlog_row_creates_notes_hypothesis_and_links(db, monkeypatch):
    user, project = user_project(db, "save-row")
    from aipm_toolkit.ui import callbacks as cb_mod
    monkeypatch.setattr(cb_mod, "SessionLocal", lambda: db)
    monkeypatch.setattr(cb_mod, "get_authenticated_user", lambda _db, _token: user)

    msg, note_id, hyp_id, hyp_rev = save_backlog_row_from_ui(
        token="token",
        project_id=str(project.id),
        dimension_key="autonomy",
        assumption_text="Users trust automated scheduling",
        question_text="Will users review schedule changes?",
        hypothesis_text="If we add undo, booking completion rises 15%",
        note_id=None,
        hyp_id=None,
        hyp_rev=None,
    )

    assert "saved" in msg.lower()
    assert note_id is not None
    assert hyp_id is not None
    assert hyp_rev == 1

    # Verify notes created
    notes = list(db.query(Note).filter_by(project_id=project.id).all())
    assert len(notes) >= 1
    assert any(n.text == "Users trust automated scheduling" for n in notes)

    # Verify hypothesis created and linked to autonomy dimension
    hypothesis = db.get(Hypothesis, UUID(hyp_id))
    assert hypothesis.statement == "If we add undo, booking completion rises 15%"
    assert hypothesis.kind == "supporting"

    dim_link = db.query(HypothesisDimension).filter_by(hypothesis_id=hypothesis.id).first()
    assert dim_link.dimension_key == "autonomy"

    # Verify provenance source link has UUID id, note_id, and null comparison_snapshot_id
    source_link = db.query(HypothesisSource).filter_by(hypothesis_id=hypothesis.id).first()
    assert source_link is not None
    assert source_link.id is not None
    assert source_link.note_id == UUID(note_id)
    assert source_link.comparison_snapshot_id is None

    # Verify edit in place updates without duplication
    edit_msg, _note_id2, hyp_id2, hyp_rev2 = save_backlog_row_from_ui(
        token="token",
        project_id=str(project.id),
        dimension_key="autonomy",
        assumption_text="Users fully trust automated scheduling",
        question_text="Will users review schedule changes?",
        hypothesis_text="If we add 1-click undo, booking completion rises 25%",
        note_id=note_id,
        hyp_id=hyp_id,
        hyp_rev=hyp_rev,
    )

    assert "saved" in edit_msg.lower()
    assert hyp_id2 == hyp_id
    assert hyp_rev2 == 2

    reloaded_hyp = db.get(Hypothesis, UUID(hyp_id))
    assert reloaded_hyp.statement == "If we add 1-click undo, booking completion rises 25%"
    assert reloaded_hyp.revision == 2


def test_show_next_row_increments():
    count, *updates = show_next_row_from_ui(2)
    assert count == 3
    assert len(updates) == MAX_BACKLOG_ROWS
    # slot index 2 (the 3rd row) should be visible
    assert updates[2]["visible"] is True
    # slot index 3 (the 4th row) should be hidden
    assert updates[3]["visible"] is False


def test_backlog_dimension_move_updates_assessment_and_history(db, monkeypatch):
    user, project = user_project(db, "move-entry")
    from aipm_toolkit.ui import callbacks as cb_mod
    monkeypatch.setattr(cb_mod, "SessionLocal", lambda: db)
    monkeypatch.setattr(cb_mod, "get_authenticated_user", lambda _db, _token: user)

    _, note_id, hyp_id, hyp_rev = save_backlog_row_from_ui(
        "token", str(project.id), "autonomy", "Users trust the schedule", "Can they undo?", "Undo increases trust", None, None, None
    )
    _, _note_id, _hyp_id, hyp_rev = save_backlog_row_from_ui(
        "token", str(project.id), "explainability", "Users trust the schedule", "Can they undo?", "Undo increases trust", note_id, hyp_id, hyp_rev
    )

    assert dimension_notes_from_ui("token", str(project.id), "autonomy") == "No questions or assumptions for this dimension yet."
    assert "Users trust the schedule" in dimension_notes_from_ui("token", str(project.id), "explainability")
    note_dims = list(db.query(NoteDimension).filter_by(note_id=UUID(note_id)).all())
    hyp_dims = list(db.query(HypothesisDimension).filter_by(hypothesis_id=UUID(hyp_id)).all())
    assert [item.dimension_key for item in note_dims] == ["explainability"]
    assert [item.dimension_key for item in hyp_dims] == ["explainability"]
    event = db.query(ProjectEvent).filter_by(event_type="backlog.entry_saved").order_by(ProjectEvent.created_at.desc()).first()
    assert '"before"' in event.details_json
    assert '"after"' in event.details_json
    assert "Moved backlog entry from autonomy to explainability" in project_history_from_ui("token", str(project.id))


def test_remove_archives_entry_preserving_experiment_and_history(db, monkeypatch):
    user, project = user_project(db, "archive-entry")
    from aipm_toolkit.ui import callbacks as cb_mod
    monkeypatch.setattr(cb_mod, "SessionLocal", lambda: db)
    monkeypatch.setattr(cb_mod, "get_authenticated_user", lambda _db, _token: user)

    _, note_id, hyp_id, _hyp_rev = save_backlog_row_from_ui(
        "token", str(project.id), "autonomy", "Users trust automation", "Can they intervene?", "Undo supports trust", None, None, None
    )
    experiment = create_experiment(db, user, project.id, UUID(hyp_id), "Test undo", "prototype_walkthrough")

    status = archive_backlog_row_from_ui("token", str(project.id), note_id, hyp_id)
    assert "preserved" in status.lower()
    assert db.get(Note, UUID(note_id)).archived_at is not None
    assert db.get(Hypothesis, UUID(hyp_id)).archived_at is not None
    assert db.get(Experiment, experiment.id).primary_hypothesis_id == UUID(hyp_id)

    loaded = load_backlog_table_from_ui("token", str(project.id))
    assert loaded[-1] == 2
    assert loaded[2] == ""
    assert loaded[3] == "Can they intervene?"
    assert loaded[5]["visible"] is True
    assert "Users trust automation" not in dimension_notes_from_ui("token", str(project.id), "autonomy")
    assert "Can they intervene?" in dimension_notes_from_ui("token", str(project.id), "autonomy")
    assert db.query(ProjectEvent).filter_by(event_type="backlog.entry_archived").count() == 1
