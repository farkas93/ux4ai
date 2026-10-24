from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from aipm_toolkit.desktop_runtime import DesktopRuntime
from aipm_toolkit.desktop_window import copy_download
from aipm_toolkit.models import Role, User
from aipm_toolkit.web import create_auth_app


@pytest.fixture
def local_api(db, tmp_path):
    user = User(username="local-owner", role=Role.TEAM.value, password_hash="!local-session")
    db.add(user)
    db.commit()
    runtime = DesktopRuntime(tmp_path, 43127, user.id)
    factory = sessionmaker(bind=db.get_bind(), expire_on_commit=False)
    app = create_auth_app(factory, desktop_runtime=runtime)
    with TestClient(app, base_url=runtime.origin, client=("127.0.0.1", 1234)) as client:
        yield client, runtime


def test_local_launch_uses_single_use_token_and_cookie_session(local_api):
    client, runtime = local_api
    assert client.get("/app", follow_redirects=False).status_code == 303
    assert client.get("/desktop/start", params={"token": "wrong"}).status_code == 401
    response = client.get(runtime.bootstrap_url, follow_redirects=False)
    assert response.status_code == 303
    assert "HttpOnly" in response.headers["set-cookie"]
    assert "SameSite=strict" in response.headers["set-cookie"]
    assert client.get("/app", follow_redirects=False).status_code == 404  # Auth passed; no mounted UI in this fixture.
    assert client.get(runtime.bootstrap_url).status_code == 401
    assert client.post("/auth/login", data={"username": "local-owner", "password": "anything"}).status_code == 404


def test_local_api_rejects_foreign_hosts_and_origins(local_api):
    client, runtime = local_api
    assert client.get("/healthz", headers={"Host": "attacker.invalid"}).status_code == 403
    assert client.get("/healthz", headers={"Origin": "https://attacker.invalid"}).status_code == 403
    assert client.get("/healthz", headers={"Origin": runtime.origin}).status_code == 200


def test_local_instance_control_requires_private_capability(local_api):
    client, runtime = local_api
    assert client.post("/desktop/focus").status_code == 401
    headers = {"Authorization": f"Bearer {runtime.control_token}"}
    assert client.post("/desktop/focus", headers=headers).status_code == 200
    assert runtime.commands.get_nowait()[0] == "focus"
    assert client.get("/desktop/state", headers=headers).json() == {"saved": None, "error": ""}
    runtime.complete_close(False, "Save failed")
    assert client.get("/desktop/state", headers=headers).json() == {"saved": False, "error": "Save failed"}


def test_downloads_require_authentication_and_generated_file_scope(local_api, tmp_path):
    client, runtime = local_api
    export = tmp_path / "exports" / "project.json"
    export.parent.mkdir()
    export.write_text('{"saved": true}', encoding="utf-8")
    url = runtime.origin + "/app/gradio_api/file=" + str(export)
    headers = {"X-AIPM-Desktop": "1"}
    assert client.post("/desktop/download", headers=headers, json={"url": url}).status_code == 401
    client.get(runtime.bootstrap_url, follow_redirects=False)
    assert client.post("/desktop/download", headers=headers, json={"url": url}).status_code == 202
    assert runtime.commands.get_nowait() == ("download", export)
    secret = tmp_path / "workspace.sqlite3"
    secret.write_bytes(b"private")
    forbidden = runtime.origin + "/app/gradio_api/file=" + str(secret)
    assert client.post("/desktop/download", headers=headers, json={"url": forbidden}).status_code == 400
    assert client.post("/desktop/download", headers=headers, json={"url": "https://attacker.invalid/file"}).status_code == 400


def test_preferences_and_export_copy_are_local_and_atomic(tmp_path):
    runtime = DesktopRuntime(tmp_path, 41000, uuid4())
    runtime.save_preference("language", "de")
    assert '"de"' in (tmp_path / "preferences.json").read_text()
    original = tmp_path / "original.pdf"
    target = tmp_path / "chosen.pdf"
    original.write_bytes(b"%PDF-new")
    target.write_bytes(b"old")
    copy_download(original, target)
    assert target.read_bytes() == b"%PDF-new"
    assert not list(tmp_path.glob(".aipm-export-*"))


def test_hosted_mode_has_no_local_bootstrap_or_control_api():
    client = TestClient(create_auth_app())
    assert client.get("/desktop/start?token=anything").status_code == 404
    assert client.post("/desktop/quit").status_code == 404
