from uuid import UUID

from aipm_toolkit.auth import hash_password
from aipm_toolkit.models import (
    Course,
    Hypothesis,
    HypothesisDimension,
    HypothesisSource,
    Note,
    Role,
    Team,
    User,
)
from aipm_toolkit.services import create_project
from aipm_toolkit.ui.callbacks import (
    MAX_BACKLOG_ROWS,
    load_backlog_table_from_ui,
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

    # 16 slots * 8 components + 1 extra (visible_count) = 129
    results = load_backlog_table_from_ui("token", str(project.id))
    assert len(results) == MAX_BACKLOG_ROWS * 8 + 1
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
