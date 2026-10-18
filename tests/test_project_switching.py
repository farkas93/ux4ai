from sqlalchemy import select

from aipm_toolkit.auth import hash_password
from aipm_toolkit.dimensions import DEFAULT_DIMENSIONS
from aipm_toolkit.hypothesis_services import create_hypothesis, create_note
from aipm_toolkit.improvement_services import QUESTIONS, save_loop
from aipm_toolkit.models import Course, DimensionEstimate, Note, Role, Team, User
from aipm_toolkit.services import create_project, update_project
from aipm_toolkit.ui import callbacks as cb
from aipm_toolkit.ui import safety_callbacks, shell


def make_user_and_projects(db):
    course = Course(name="Switching course")
    db.add(course)
    db.flush()
    team = Team(course_id=course.id, alias="switch-team")
    db.add(team)
    db.flush()
    user = User(username="switch-team", password_hash=hash_password("P" * 16), role=Role.TEAM.value, team_id=team.id)
    db.add(user)
    db.commit()
    return user, create_project(db, user, "Project Alpha"), create_project(db, user, "Project Beta")


def test_switch_decision_prompts_only_for_a_different_project_with_dirty_data():
    assert cb.decide_project_switch("alpha", "alpha", [True]) == "none"
    assert cb.decide_project_switch("alpha", None, [True]) == "none"
    assert cb.decide_project_switch("alpha", "beta", [False, False]) == "load"
    assert cb.decide_project_switch("alpha", "beta", [False, True]) == "confirm"


def test_workspace_product_loaders_return_data_for_the_requested_project(db, monkeypatch):
    user, alpha, beta = make_user_and_projects(db)
    update_project(db, user, alpha.id, alpha.revision, short_description="Alpha description")
    alpha = db.get(type(alpha), alpha.id)
    update_project(db, user, beta.id, beta.revision, short_description="Beta description")
    db.add(DimensionEstimate(
        project_id=beta.id,
        dimension_key=DEFAULT_DIMENSIONS[0]["key"],
        scale_version=1,
        status="estimated",
        score=4.5,
        rationale="Beta-only assessment",
    ))
    create_note(db, user, beta.id, "question", "Beta-only backlog question", origin_section="backlog")
    create_hypothesis(db, user, beta.id, "Beta-only supporting hypothesis")
    answers = {key: {"answer": "yes", "explanation": f"Beta explanation for {key}"} for key in QUESTIONS}
    save_loop(db, user, beta.id, None, None, {
        "name": "Beta learning loop",
        "answers": answers,
        "status": "intended",
        "scopes": [],
        "recursion_scope": "product_behavior",
        "release_approval": "unspecified",
        "approval_boundary": "",
        "success_checks": "",
        "rollback": "",
    })
    db.commit()

    monkeypatch.setattr(cb, "SessionLocal", lambda: db)
    monkeypatch.setattr(cb, "get_authenticated_user", lambda _db, _token: user)
    monkeypatch.setattr(safety_callbacks, "SessionLocal", lambda: db)
    monkeypatch.setattr(safety_callbacks, "get_authenticated_user", lambda _db, _token: user)

    assert cb.load_project_from_ui("token", str(beta.id))[1] == ""  # target user is project-specific too
    assert cb.load_project_from_ui("token", str(beta.id))[0] == "Beta description"
    estimates = cb.load_estimates_from_ui("token", str(beta.id))
    assert estimates[0] == 4.5
    assert estimates[1] == "Beta-only assessment"
    backlog = cb.load_backlog_table_from_ui("token", str(beta.id))
    assert "Beta-only backlog question" in backlog[4]
    placement = cb.load_placements_from_ui("token", str(beta.id))
    assert "Beta-only supporting hypothesis" in placement[-2]
    improvement = safety_callbacks.load_primary_loop_ui("token", str(beta.id))
    assert improvement[1] == "Beta learning loop"
    report = cb.summary_preview_from_ui("token", str(beta.id))
    assert "Project Beta" in report
    assert "Project Alpha" not in report
    assert db.scalar(select(Note.text).where(Note.project_id == alpha.id)) is None


def test_save_before_switch_persists_all_dirty_edits_to_the_old_project(db, monkeypatch):
    user, alpha, beta = make_user_and_projects(db)
    priority_hypothesis = create_hypothesis(db, user, alpha.id, "Alpha priority claim")
    monkeypatch.setattr(cb, "SessionLocal", lambda: db)
    monkeypatch.setattr(cb, "get_authenticated_user", lambda _db, _token: user)
    monkeypatch.setattr(safety_callbacks, "SessionLocal", lambda: db)
    monkeypatch.setattr(safety_callbacks, "get_authenticated_user", lambda _db, _token: user)

    assessment_fields = []
    for index in range(len(DEFAULT_DIMENSIONS)):
        assessment_fields.extend([4.0 + index / 10, f"Alpha assessment {index}"])
    loop_fields = ["Alpha learning loop"]
    for key in list(QUESTIONS)[:5]:
        loop_fields.extend(["yes", f"Alpha explanation {key}"])
    backlog_rows = [[True, "autonomy", "Alpha assumption", "", "If we explain the control, users can intervene", None, None, None]]
    backlog_rows.extend([[False, None, "", "", "", None, None, None] for _ in range(cb.MAX_BACKLOG_ROWS - 1)])
    assessment_note_drafts = [[True, DEFAULT_DIMENSIONS[0]["key"], "Question", "Alpha assessment note draft", ""]]
    assessment_note_drafts.extend([[False, None, "Question", "", ""] for _ in range(len(DEFAULT_DIMENSIONS) - 1)])
    draft = [
        True,
        alpha.revision,
        None,
        "Alpha edited description",
        "Alpha users",
        "Alpha job",
        "Alpha problem",
        "Alpha value hypothesis",
        "",
        True,
        [],
        *assessment_fields,
        True,
        None,
        *loop_fields,
        None,
        True,
        str(priority_hypothesis.id),
        priority_hypothesis.revision,
        9.0,
        2.0,
        *[value for _ in range(cb.PLACEMENT_SLOTS - 1) for value in [False, None, None, 0.0, 0.0]],
        *[value for row in backlog_rows for value in row],
        *[value for note in assessment_note_drafts for value in note],
        True,
        "Assumption",
        "Alpha improvement note draft",
        "",
    ]

    result = cb.save_pending_project_edits("token", str(alpha.id), None, *draft)
    assert result[0] == "Changes saved to the current project."
    assert result[-1] is True
    assert result[2] is False and result[4] is False and result[7] is False
    row_start = 8 + cb.PLACEMENT_SLOTS * 2
    assert result[row_start] is False and result[row_start + 1] and result[row_start + 2]
    note_start = row_start + cb.MAX_BACKLOG_ROWS * 4
    assert result[note_start] is False and result[note_start + 1] == ""
    improvement_note_start = note_start + len(DEFAULT_DIMENSIONS) * 3
    assert result[improvement_note_start] is False and result[improvement_note_start + 1] == ""

    assert db.get(type(alpha), alpha.id).short_description == "Alpha edited description"
    assert db.get(type(beta), beta.id).short_description == ""
    assert db.scalar(select(DimensionEstimate.score).where(DimensionEstimate.project_id == alpha.id, DimensionEstimate.dimension_key == DEFAULT_DIMENSIONS[0]["key"])) == 4.0
    assert db.scalar(select(DimensionEstimate.id).where(DimensionEstimate.project_id == beta.id)) is None
    assert db.get(type(priority_hypothesis), priority_hypothesis.id).priority_risk == 9.0
    assert db.get(type(priority_hypothesis), priority_hypothesis.id).priority_evidence == 2.0
    assert any(note.project_id == alpha.id and note.text == "Alpha assumption" for note in db.scalars(select(Note)))
    assert any(note.project_id == alpha.id and note.text == "Alpha assessment note draft" for note in db.scalars(select(Note)))
    assert any(note.project_id == alpha.id and note.text == "Alpha improvement note draft" for note in db.scalars(select(Note)))
    assert not any(note.project_id == beta.id for note in db.scalars(select(Note)))
    assert safety_callbacks.load_primary_loop_ui("token", str(alpha.id))[1] == "Alpha learning loop"
    assert safety_callbacks.load_primary_loop_ui("token", str(beta.id))[1] == ""


def test_failed_save_keeps_switch_blocked_and_preserves_dirty_project_setup(db, monkeypatch):
    user, alpha, beta = make_user_and_projects(db)
    monkeypatch.setattr(cb, "SessionLocal", lambda: db)
    monkeypatch.setattr(cb, "get_authenticated_user", lambda _db, _token: user)
    setup_fields = [None, "Unsaved Alpha description", "", "", "", "", "javascript:alert(1)"]
    draft = [True, alpha.revision, *setup_fields, False, [], *([2.5, ""] * len(DEFAULT_DIMENSIONS)), False, None]
    draft.extend(["", *(["unknown", ""] * 5), None])
    draft.extend(value for _ in range(cb.PLACEMENT_SLOTS) for value in [False, None, None, 0.0, 0.0])
    draft.extend(value for _ in range(cb.MAX_BACKLOG_ROWS) for value in [False, None, "", "", "", None, None, None])
    draft.extend(value for _ in DEFAULT_DIMENSIONS for value in [False, None, "Question", "", ""])
    draft.extend([False, "Question", "", ""])

    result = cb.save_pending_project_edits("token", str(alpha.id), None, *draft)
    assert result[-1] is False
    assert result[2] is True
    assert result[1] == alpha.revision
    assert "Project Setup:" in result[0]
    assert db.get(type(alpha), alpha.id).figma_url is None
    assert db.get(type(beta), beta.id).short_description == ""


def test_product_switch_popup_offers_save_discard_and_cancel(monkeypatch):
    app = shell.build_app()
    components = app.get_config_file()["components"]
    assert any(item["props"].get("elem_id") == "toolkit-project-switch-backdrop" for item in components)
    assert {item["props"].get("value") for item in components if item["type"] == "button"} >= {
        "Save & Switch",
        "Discard & Switch",
        "Cancel",
    }
    monkeypatch.setattr(shell, "project_switch_prompt_text", lambda *_args, **_kwargs: "Save changes in Alpha before opening Beta?")
    route = next(fn.fn for fn in app.fns.values() if fn.fn and fn.fn.__name__ == "route_project_selection")
    dirty_count = 3 + cb.PLACEMENT_SLOTS + cb.MAX_BACKLOG_ROWS + len(DEFAULT_DIMENSIONS) + 1
    clean = route("token", "beta", "alpha", False, None, *([False] * dirty_count))
    assert clean[0:3] == ("beta", None, "load")
    assert clean[-1] is True
    dirty = route("token", "beta", "alpha", False, None, *([True] + [False] * (dirty_count - 1)))
    assert dirty[0:3] == ("alpha", "beta", "none")
    assert dirty[3]["visible"] is True
    assert dirty[4] == "Save changes in Alpha before opening Beta?"
    assert dirty[5]["value"] == "alpha"
    assert dirty[6] is True
