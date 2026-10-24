import json
import os
import sqlite3
import subprocess
import sys
import time
from collections import deque

import httpx


class LocalProcess:
    def __init__(self, profile, cwd):
        self.profile = profile
        environment = os.environ.copy()
        environment.update({"AIPM_DATABASE_URL": "postgresql://invalid.invalid/not-the-desktop-db",
                            "AIPM_COOKIE_SECURE": "true", "AIPM_COOKIE_NAME": "wrong-env-cookie"})
        command = [environment["AIPM_TEST_EXECUTABLE"]] if environment.get("AIPM_TEST_EXECUTABLE") else [sys.executable, "-B", "-m", "aipm_toolkit.desktop"]
        self.process = subprocess.Popen(
            [*command, "--headless", "--data-dir", str(profile)],
            cwd=cwd, env=environment, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
        deadline = time.monotonic() + 45
        while time.monotonic() < deadline:
            if self.process.poll() is not None:
                stdout, stderr = self.process.communicate()
                raise AssertionError((stdout + stderr).decode())
            try:
                self.metadata = json.loads((profile / "instance.json").read_text())
                break
            except (OSError, ValueError):
                time.sleep(0.05)
        else:
            self.process.kill()
            raise AssertionError("Desktop runtime did not start")
        self.client = httpx.Client(base_url=self.metadata["origin"], trust_env=False, timeout=15)

    def sign_in(self):
        response = self.client.get(self.metadata["bootstrap_url"], follow_redirects=False)
        assert response.status_code == 303, response.text

    def stop(self):
        if self.process.poll() is None:
            self.client.post("/desktop/quit", headers={"Authorization": "Bearer " + self.metadata["control_token"]})
            self.process.wait(timeout=25)
        self.client.close()
        stdout, stderr = self.process.communicate()
        assert self.process.returncode == 0, (stdout + stderr).decode()


class BrowserAPI:
    """Run the existing browser-shaped Gradio workflow over a real local server."""

    def __init__(self, client):
        self.client = client
        self.config = client.get("/app/config").json()
        self.components = {item["id"]: item for item in self.config["components"]}
        self.values = {key: item["props"].get("value") for key, item in self.components.items()}
        self.dependencies = self.config["dependencies"]
        self.session_hash = "desktop-process-test"

    def named(self, name):
        return next(fn for fn in self.dependencies if fn["api_name"] == name)

    def run(self, fn):
        pending = deque([fn])
        while pending:
            current = pending.popleft()
            data = [None if self.components[key]["type"] == "state" else self.values[key] for key in current["inputs"]]
            response = self.client.post("/app/gradio_api/run/" + current["api_name"],
                                        json={"fn_index": current["id"], "session_hash": self.session_hash, "data": data})
            assert response.status_code == 200, response.text
            output = response.json()
            for key, value in zip(current["outputs"], output["data"], strict=True):
                if self.components[key]["type"] == "state":
                    continue
                if isinstance(value, dict) and value.get("__type__") == "update":
                    if "value" in value:
                        self.values[key] = value["value"]
                else:
                    self.values[key] = value
            pending.extend(child for child in self.dependencies if child.get("trigger_after") == current["id"])
        return output

    def set_label(self, label, value):
        key = next(key for key, item in self.components.items() if item["props"].get("label") == label)
        self.values[key] = value


def test_desktop_cold_start_save_export_and_restart(tmp_path):
    profile = tmp_path / "private-profile"
    (tmp_path / ".env").write_text("AIPM_DATABASE_URL=postgresql://wrong.invalid/wrong\n")
    local = LocalProcess(profile, tmp_path)
    try:
        assert local.client.get("/app/config", follow_redirects=False).status_code == 303
        local.sign_in()
        browser = BrowserAPI(local.client)
        assert not any("Open public link" == item["props"].get("value") for item in browser.components.values())
        browser.run(browser.named("auto_login"))
        browser.set_label("New product name", "Offline project")
        browser.run(browser.named("create_project_from_ui"))
        browser.set_label("Short description", "Locally saved ÄÖÜ content")
        browser.set_label("Target user", "Local student")
        browser.run(browser.named("save_setup"))
        backlog = browser.named("save_backlog_row_from_ui")
        browser.values[backlog["inputs"][2]] = "autonomy"
        browser.values[backlog["inputs"][5]] = "Offline supporting hypothesis"
        browser.run(backlog)
        # Export must flush current values even before a slider save is sent.
        browser.set_label("Risk if wrong", 6.5)
        browser.set_label("Evidence available", 3.5)
        exported = browser.run(browser.named("prepare_downloads"))
        file_values = [value for value in exported["data"] if isinstance(value, dict) and value.get("url", "").endswith(".json")]
        assert len(file_values) == 1, exported
        document = local.client.get(file_values[0]["url"]).json()
        assert document["project"]["short_description"] == "Locally saved ÄÖÜ content"
        assert document["project"]["target_user"] == "Local student"
        supporting = next(item for item in document["hypotheses"] if item["kind"] == "supporting")
        assert supporting["priority_risk"] == 6.5
        assert supporting["priority_evidence"] == 3.5
        old_cookie = local.client.cookies.get("aipm_session")
    finally:
        local.stop()
    assert not (profile / "instance.json").exists()
    with sqlite3.connect(profile / "workspace.sqlite3") as db:
        project_id, text = db.execute("SELECT id, short_description FROM projects").fetchone()
        assert text == "Locally saved ÄÖÜ content"
        assert db.execute("SELECT count(*) FROM sessions").fetchone()[0] == 0
        assert db.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
        assert db.execute("SELECT count(*) FROM baseline_datasets WHERE published=1").fetchone()[0] == 16
    restarted = LocalProcess(profile, tmp_path)
    try:
        restarted.client.cookies.set("aipm_session", old_cookie)
        assert restarted.client.get("/app/config", follow_redirects=False).status_code == 303
        restarted.sign_in()
        with sqlite3.connect(profile / "workspace.sqlite3") as db:
            assert db.execute("SELECT id FROM projects").fetchone()[0] == project_id
            assert db.execute("SELECT count(*) FROM baseline_datasets").fetchone()[0] == 16
    finally:
        restarted.stop()


def test_failed_native_close_keeps_runtime_and_dirty_edits_available(tmp_path):
    local = LocalProcess(tmp_path / "close-profile", tmp_path)
    try:
        local.sign_in()
        browser = BrowserAPI(local.client)
        browser.run(browser.named("auto_login"))
        browser.set_label("New product name", "Close test")
        browser.run(browser.named("create_project_from_ui"))
        browser.set_label("Figma prototype URL (optional)", "javascript:invalid")
        browser.run(browser.named("track_setup_edits"))
        browser.run(browser.named("save_and_close"))
        state = local.client.get("/desktop/state", headers={"Authorization": "Bearer " + local.metadata["control_token"]}).json()
        assert state["saved"] is False
        assert "HTTP or HTTPS" in state["error"]
        assert local.process.poll() is None
        browser.set_label("Figma prototype URL (optional)", "")
        browser.run(browser.named("track_setup_edits"))
        browser.run(browser.named("save_and_close"))
        local.process.wait(timeout=25)
        assert local.process.returncode == 0
    finally:
        local.stop()


def test_blank_workspace_close_ignores_empty_mount_time_inputs(tmp_path):
    local = LocalProcess(tmp_path / "blank-profile", tmp_path)
    try:
        local.sign_in()
        browser = BrowserAPI(local.client)
        browser.run(browser.named("auto_login"))
        # Initial component mounts can mark default controls dirty. They do
        # not represent work and must not prevent closing an empty workspace.
        browser.run(browser.named("track_setup_edits"))
        browser.run(browser.named("save_and_close"))
        local.process.wait(timeout=25)
        assert local.process.returncode == 0
    finally:
        local.stop()


def test_second_launch_focuses_existing_instance_without_opening_database_again(tmp_path):
    profile = tmp_path / "single-profile"
    local = LocalProcess(profile, tmp_path)
    try:
        command = [os.environ["AIPM_TEST_EXECUTABLE"]] if os.environ.get("AIPM_TEST_EXECUTABLE") else [sys.executable, "-B", "-m", "aipm_toolkit.desktop"]
        result = subprocess.run([*command, "--headless", "--data-dir", str(profile)],
                                cwd=tmp_path, capture_output=True, timeout=10, check=False)
        assert result.returncode == 0, (result.stdout + result.stderr).decode()
        # Windows venv redirectors and frozen launchers can own a different PID
        # from the runtime. A focus-only launch must preserve the live identity.
        assert json.loads((profile / "instance.json").read_text(encoding="utf-8")) == local.metadata
        assert local.process.poll() is None
    finally:
        local.stop()
