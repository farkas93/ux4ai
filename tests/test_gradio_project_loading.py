import json
from collections import deque

import gradio as gr
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker

from aipm_toolkit.auth import hash_password
from aipm_toolkit.dimensions import DEFAULT_DIMENSIONS
from aipm_toolkit.hypothesis_services import create_hypothesis, create_note, set_placement
from aipm_toolkit.improvement_services import QUESTIONS, save_loop
from aipm_toolkit.models import Course, DimensionEstimate, Hypothesis, Role, Team, User
from aipm_toolkit.services import create_project, update_project
from aipm_toolkit.ui import callbacks, safety_callbacks, shell
from aipm_toolkit.ui.shell import build_app
from aipm_toolkit.web import create_auth_app


def layout_ids(node):
    return {node["id"]} | {component_id for child in node.get("children", []) for component_id in layout_ids(child)}


class GradioBrowserSession:
    """Send browser-shaped requests, retaining client values and Gradio server state."""

    def __init__(self, blocks, client):
        self.blocks = blocks
        self.client = client
        self.session_hash = "project-loading-regression"
        self.config = blocks.get_config_file()
        self.properties = {component["id"]: component["props"].copy() for component in self.config["components"]}
        self.values = {
            component["id"]: component["props"].get("value")
            for component in self.config["components"]
        }
        self.queued = False
        self.automatic_changes = False
        self.calls = []
        self.responses = []

    def run(self, fn):
        pending = deque([fn])
        calls = 0
        while pending:
            current = pending.popleft()
            if current in pending:
                continue
            calls += 1
            self.calls.append(current)
            assert calls < 300, "Automatic events must settle without a refresh loop"
            payload = {
                "fn_index": current._id,
                "session_hash": self.session_hash,
                "data": [None if block.stateful else self.values[block._id] for block in current.inputs],
            }
            if self.queued:
                response = self.client.post("/app/gradio_api/queue/join", json=payload)
                assert response.status_code == 200, response.text
                event_id = response.json()["event_id"]
                stream = self.client.get("/app/gradio_api/queue/data", params={"session_hash": self.session_hash})
                messages = [json.loads(line[6:]) for line in stream.text.splitlines() if line.startswith("data: ")]
                completed = next(message for message in messages if message.get("event_id") == event_id and message["msg"] == "process_completed")
                assert completed["success"], completed
                output = completed["output"]
            else:
                response = self.client.post(f"/app/gradio_api/run/{current.api_name}", json=payload)
                assert response.status_code == 200, response.text
                output = response.json()
            self.responses.append((current, output))
            changed_ids = set(output.get("changed_state_ids", []))
            for block, value in zip(current.outputs, output["data"], strict=True):
                if block.stateful:
                    continue
                previous = self.values[block._id]
                if isinstance(value, dict) and value.get("__type__") == "update":
                    self.properties[block._id].update(value)
                    if "value" in value:
                        self.values[block._id] = value["value"]
                else:
                    self.values[block._id] = value
                if self.values[block._id] != previous:
                    changed_ids.add(block._id)
            if self.automatic_changes:
                pending.extend(
                    child for child in self.blocks.fns.values()
                    if any((changed_id, "change") in child.targets for changed_id in changed_ids)
                )
            # The browser submits each chained event separately, with the same session.
            pending.extend(child for child in self.blocks.fns.values() if child.trigger_after == current._id)

    def page_ids(self, elem_id):
        page_id = self.component(elem_id=elem_id)._id

        def find(node):
            if node["id"] == page_id:
                return node
            for child in node.get("children", []):
                result = find(child)
                if result:
                    return result
            return None

        return layout_ids(find(self.config["layout"]))

    def page_values(self, elem_id):
        return [self.values[component_id] for component_id in self.page_ids(elem_id)]

    def component(self, *, label=None, elem_id=None, button=None):
        matches = [
            block for block in self.blocks.blocks.values()
            if (label is not None and getattr(block, "label", None) == label)
            or (elem_id is not None and block.elem_id == elem_id)
            or (button is not None and isinstance(block, gr.Button) and block.value == button)
        ]
        if button == "Cancel":
            return next(block for block in matches if (block._id, "click") in next(
                fn.targets for fn in self.blocks.fns.values() if fn.fn and fn.fn.__name__ == "_cancel_project_switch"
            ))
        return matches[0]

    def event(self, block, event):
        return next(fn for fn in self.blocks.fns.values() if (block._id, event) in fn.targets)

    def edit(self, block, value):
        self.values[block._id] = value
        for fn in self.blocks.fns.values():
            if (block._id, "input") in fn.targets or (block._id, "change") in fn.targets:
                self.run(fn)

    def click(self, button):
        self.run(self.event(self.component(button=button), "click"))

    def select_project(self, project_id):
        self.edit(self.component(elem_id="toolkit-product"), str(project_id))


@pytest.fixture
def workspace_browser(db, monkeypatch):
    course = Course(name="Browser regression course")
    db.add(course)
    db.flush()
    team = Team(course_id=course.id, alias="browser-team")
    db.add(team)
    db.flush()
    user = User(username="browser-team", password_hash=hash_password("P" * 16), role=Role.TEAM.value, team_id=team.id)
    db.add(user)
    db.commit()
    projects = [create_project(db, user, f"Project {name}") for name in ("Alpha", "Beta")]
    for index, project in enumerate(projects):
        update_project(db, user, project.id, project.revision, short_description=f"{project.product_name} saved description")
        for definition in DEFAULT_DIMENSIONS:
            db.add(DimensionEstimate(
                project_id=project.id, dimension_key=definition["key"], scale_version=1,
                status="estimated", score=index + 1.0, rationale=f"{project.product_name} reasoning",
            ))
        create_note(db, user, project.id, "question", f"{project.product_name} question", ["autonomy"], origin_section="assessment")
        hypothesis = create_hypothesis(db, user, project.id, f"{project.product_name} supporting hypothesis")
        set_placement(db, user, hypothesis.id, hypothesis.revision, risk=8.0 + index, evidence=2.0 + index)
        save_loop(db, user, project.id, None, None, {
            "name": f"{project.product_name} improvement loop",
            "answers": {key: {"answer": "unknown", "explanation": f"{project.product_name} explanation"} for key in QUESTIONS},
            "status": "intended", "scopes": [], "recursion_scope": "product_behavior",
            "release_approval": "unspecified", "approval_boundary": "", "success_checks": "", "rollback": "",
        })
    factory = sessionmaker(bind=db.get_bind(), expire_on_commit=False)
    monkeypatch.setattr(callbacks, "SessionLocal", factory)
    monkeypatch.setattr(safety_callbacks, "SessionLocal", factory)
    blocks = build_app()
    application = gr.mount_gradio_app(create_auth_app(factory), blocks, path="/app")
    with TestClient(application) as client:
        login = client.post("/auth/login", data={"username": user.username, "password": "P" * 16}, follow_redirects=False)
        assert login.status_code == 303
        browser = GradioBrowserSession(blocks, client)
        browser.run(next(fn for fn in blocks.fns.values() if fn.fn is callbacks.auto_login))
        yield browser, projects, factory


def assert_loaded_project(browser, project):
    assert browser.values[browser.component(label="Short description")._id] == f"{project.product_name} saved description"
    assert browser.values[browser.component(label="Reasoning / Notes")._id] == f"{project.product_name} reasoning"
    assert browser.values[browser.component(label="Your improvement loop")._id] == f"{project.product_name} improvement loop"
    assert f"{project.product_name} question" in browser.page_values("page-backlog-creator")
    assert f"{project.product_name} supporting hypothesis" in browser.page_values("page-prioritization")
    assert any(f"# {project.product_name} · Product learning report" in str(value) for value in browser.page_values("page-summary-export"))
    assert browser.properties[browser.component(elem_id="toolkit-product")._id]["interactive"] is True
    assert browser.properties[browser.component(elem_id="toolkit-project-switch-backdrop")._id]["visible"] is False


def test_cookie_login_and_switching_load_saved_content_on_every_page(workspace_browser):
    browser, projects, _factory = workspace_browser
    selected_id = browser.values[browser.component(elem_id="toolkit-product")._id]
    selected_project = next(project for project in projects if str(project.id) == selected_id)
    # Cookie login intentionally leaves the client token state empty.
    workspace_fn = next(fn for fn in browser.blocks.fns.values() if fn.fn is callbacks.workspace)
    assert browser.blocks.state_holder[browser.session_hash][workspace_fn.inputs[0]._id] is None
    assert_loaded_project(browser, selected_project)
    for section in ("Value Hypothesis", "Explore Dimensions", "Explore Backlog", "Explore Priority", "Build Self-Improvement", "Summary & Export"):
        browser.edit(browser.component(elem_id="toolkit-desktop-section"), section)
        for project in projects:
            browser.select_project(project.id)
            assert_loaded_project(browser, project)
            assert browser.values[browser.component(elem_id="toolkit-current-section")._id] == section


def assert_save_and_switch_uses_cookie_and_saves_only_the_project_being_left(workspace_browser):
    browser, projects, factory = workspace_browser
    alpha, beta = projects
    browser.select_project(alpha.id)
    browser.edit(browser.component(elem_id="toolkit-desktop-section"), "Explore Dimensions")
    browser.edit(browser.component(label="Reasoning / Notes"), "Alpha unsaved reasoning")
    browser.select_project(beta.id)
    assert browser.values[browser.component(elem_id="toolkit-product")._id] == str(alpha.id)
    assert browser.properties[browser.component(elem_id="toolkit-project-switch-backdrop")._id]["visible"] is True
    assert "Project Alpha" in browser.values[browser.component(elem_id="toolkit-project-switch-message")._id]
    browser.click("Save & Switch")
    assert_loaded_project(browser, beta)
    with factory() as session:
        alpha_estimate = session.query(DimensionEstimate).filter_by(project_id=alpha.id, dimension_key=DEFAULT_DIMENSIONS[0]["key"]).one()
        beta_estimate = session.query(DimensionEstimate).filter_by(project_id=beta.id, dimension_key=DEFAULT_DIMENSIONS[0]["key"]).one()
        assert alpha_estimate.rationale == "Alpha unsaved reasoning"
        assert beta_estimate.rationale == "Project Beta reasoning"


def assert_cancel_preserves_drafts_and_discard_switches_without_saving(workspace_browser):
    browser, projects, factory = workspace_browser
    alpha, beta = projects
    browser.select_project(alpha.id)
    reasoning = browser.component(label="Reasoning / Notes")
    browser.edit(reasoning, "Draft that must remain unsaved")
    browser.select_project(beta.id)
    browser.click("Cancel")
    assert browser.values[browser.component(elem_id="toolkit-product")._id] == str(alpha.id)
    assert browser.values[reasoning._id] == "Draft that must remain unsaved"
    assert browser.properties[browser.component(elem_id="toolkit-project-switch-backdrop")._id]["visible"] is False
    browser.select_project(beta.id)
    browser.click("Discard & Switch")
    assert_loaded_project(browser, beta)
    with factory() as session:
        assert session.query(DimensionEstimate).filter_by(project_id=alpha.id, dimension_key=DEFAULT_DIMENSIONS[0]["key"]).one().rationale == "Project Alpha reasoning"


def assert_failed_save_keeps_project_and_draft_visible(workspace_browser):
    browser, projects, factory = workspace_browser
    alpha, beta = projects
    browser.select_project(alpha.id)
    prototype = browser.component(label="Figma prototype URL (optional)")
    browser.edit(prototype, "javascript:invalid")
    browser.select_project(beta.id)
    browser.click("Save & Switch")
    assert browser.values[browser.component(elem_id="toolkit-product")._id] == str(alpha.id)
    assert browser.values[prototype._id] == "javascript:invalid"
    assert browser.properties[browser.component(elem_id="toolkit-project-switch-backdrop")._id]["visible"] is True
    assert "Figma URL must use HTTP or HTTPS" in browser.values[browser.component(elem_id="toolkit-project-switch-message")._id]
    with factory() as session:
        assert session.get(type(alpha), alpha.id).figma_url is None
        assert session.get(type(beta), beta.id).short_description == "Project Beta saved description"
    browser.click("Discard & Switch")
    assert_loaded_project(browser, beta)


def assert_creating_blank_project_clears_previous_content_from_all_pages(workspace_browser):
    browser, _projects, _factory = workspace_browser
    browser.click("+ New")
    name = browser.component(label="New product name")
    browser.values[name._id] = "Blank project"
    browser.click("Create")
    assert browser.values[browser.component(label="Short description")._id] == ""
    assert browser.values[browser.component(label="Reasoning / Notes")._id] == ""
    assert browser.values[browser.component(label="Your improvement loop")._id] == ""
    assert not any("Project Alpha" in str(value) or "Project Beta" in str(value) for value in browser.page_values("page-backlog-creator"))
    assert not any("Project Alpha" in str(value) or "Project Beta" in str(value) for value in browser.page_values("page-prioritization"))
    assert any("# Blank project · Product learning report" in str(value) for value in browser.page_values("page-summary-export"))
    assert browser.properties[browser.component(elem_id="toolkit-product")._id]["interactive"] is True


def test_cookie_authenticated_switch_confirmation_and_creation_journey(workspace_browser):
    # Exercise the decisions in one browser session, including switching again
    # after cancelling, discarding, saving, and recovering from a failed save.
    assert_cancel_preserves_drafts_and_discard_switches_without_saving(workspace_browser)
    assert_save_and_switch_uses_cookie_and_saves_only_the_project_being_left(workspace_browser)
    assert_failed_save_keeps_project_and_draft_visible(workspace_browser)
    assert_creating_blank_project_clears_previous_content_from_all_pages(workspace_browser)


def test_queued_loading_with_automatic_change_events(workspace_browser):
    browser, projects, factory = workspace_browser
    with factory() as session:
        original_revisions = {hypothesis.id: hypothesis.revision for hypothesis in session.query(Hypothesis).all()}
    browser = GradioBrowserSession(browser.blocks, browser.client)
    browser.session_hash = "queued-project-loading-regression"
    browser.queued = True
    browser.automatic_changes = True
    browser.run(next(fn for fn in browser.blocks.fns.values() if fn.fn is callbacks.auto_login))
    selected_id = browser.values[browser.component(elem_id="toolkit-product")._id]
    assert_loaded_project(browser, next(project for project in projects if str(project.id) == selected_id))
    for project in reversed(projects):
        browser.select_project(project.id)
        assert_loaded_project(browser, project)
    with factory() as session:
        assert {hypothesis.id: hypothesis.revision for hypothesis in session.query(Hypothesis).all()} == original_revisions
    # The same loaded slider still persists deliberate user changes.
    risk = browser.component(label="Risk if wrong")
    browser.edit(risk, 6.5)
    browser.select_project(projects[1].id)
    assert_loaded_project(browser, projects[1])
    browser.select_project(projects[0].id)
    assert browser.values[risk._id] == 6.5


def test_project_snapshot_has_no_intermediate_section_updates(workspace_browser):
    browser, projects, _factory = workspace_browser
    browser.select_project(projects[0].id)
    start = len(browser.calls)
    browser.select_project(projects[1].id)
    assert [fn.fn.__name__ for fn in browser.calls[start:]] == ["route_project_selection", "load_project_snapshot"]
    snapshot_fn, output = browser.responses[-1]
    changed_outputs = {block._id for block, value in zip(snapshot_fn.outputs, output["data"], strict=True) if value != {"__type__": "update"}}
    assert browser.component(label="Short description")._id in changed_outputs
    assert browser.component(label="Your improvement loop")._id in changed_outputs
    assert any(component_id in changed_outputs for component_id in browser.page_ids("page-backlog-creator"))
    assert any(component_id in changed_outputs for component_id in browser.page_ids("page-prioritization"))
    assert_loaded_project(browser, projects[1])


def test_auxiliary_fetch_failure_does_not_block_project_editors(workspace_browser, monkeypatch):
    browser, projects, _factory = workspace_browser

    def fail():
        raise OperationalError("SELECT baseline_datasets", {}, Exception("baseline unavailable"))

    monkeypatch.setattr(shell, "load_comparator_choices", fail)
    browser.select_project(projects[0].id)
    browser.select_project(projects[1].id)
    assert_loaded_project(browser, projects[1])
    assert "Historical comparison could not be loaded" in browser.values[browser.component(elem_id="aipm-status-banner")._id]
    def fail_summary(*_args, **_kwargs):
        raise ValueError("summary unavailable")

    monkeypatch.setattr(shell, "summary_preview_from_ui", fail_summary)
    browser.select_project(projects[0].id)
    assert browser.values[browser.component(label="Your improvement loop")._id] == "Project Alpha improvement loop"
    assert "Project Alpha question" in browser.page_values("page-backlog-creator")
    assert "Project Alpha supporting hypothesis" in browser.page_values("page-prioritization")
    assert any("Summary could not be loaded: summary unavailable" in str(value) for value in browser.page_values("page-summary-export"))


def test_failed_core_fetch_retains_previous_project_and_unlocks_picker(workspace_browser, monkeypatch):
    browser, projects, _factory = workspace_browser
    browser.select_project(projects[0].id)
    snapshot = {component_id: browser.values[component_id] for component_id in browser.page_ids("page-backlog-creator")}

    def fail(*_args, **_kwargs):
        raise OperationalError("SELECT notes", {}, Exception("database unavailable"))

    monkeypatch.setattr(shell, "load_backlog_table_from_ui", fail)
    browser.select_project(projects[1].id)
    assert browser.values[browser.component(elem_id="toolkit-product")._id] == str(projects[0].id)
    assert browser.values[browser.component(label="Your improvement loop")._id] == "Project Alpha improvement loop"
    assert {component_id: browser.values[component_id] for component_id in snapshot} == snapshot
    assert browser.properties[browser.component(elem_id="toolkit-product")._id]["interactive"] is True
    assert "Product load failed" in browser.values[browser.component(elem_id="aipm-status-banner")._id]
