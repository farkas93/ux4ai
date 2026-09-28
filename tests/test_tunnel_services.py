
import gradio.tunneling

from aipm_toolkit.auth import hash_password
from aipm_toolkit.models import Course, Role, Team, User
from aipm_toolkit.tunnel_services import (
    close_public_access,
    open_public_access,
    public_access_status,
)
from aipm_toolkit.ui import tunnel_callbacks


class FakeProcess:
    def __init__(self):
        self.returncode = None

    def poll(self):
        return self.returncode

    def terminate(self):
        self.returncode = 0


class FakeTunnel:
    def __init__(self):
        self.proc = FakeProcess()

    def kill(self):
        self.proc.terminate()


def test_public_gradio_tunnel_opens_idempotently_and_closes(monkeypatch):
    close_public_access()
    started = []

    def start_tunnel(**kwargs):
        assert kwargs["local_host"] == "127.0.0.1"
        assert kwargs["local_port"] == 7860
        tunnel = FakeTunnel()
        gradio.tunneling.CURRENT_TUNNELS.append(tunnel)
        started.append(tunnel)
        return "temporary.gradio.live"

    monkeypatch.setattr(tunnel_callbacks, "open_public_access", open_public_access)
    import aipm_toolkit.tunnel_services as service
    monkeypatch.setattr(service.networking, "setup_tunnel", start_tunnel)

    assert open_public_access() == "https://temporary.gradio.live"
    assert open_public_access() == "https://temporary.gradio.live"
    assert len(started) == 1
    assert public_access_status() == {"enabled": True, "url": "https://temporary.gradio.live"}
    close_public_access()
    assert started[0].proc.returncode == 0
    assert public_access_status() == {"enabled": False, "url": None}


def test_public_tunnel_controls_require_instructor(db, monkeypatch):
    course = Course(name="Tunnel course")
    db.add(course)
    db.flush()
    team = Team(course_id=course.id, alias="tunnel-team")
    db.add(team)
    db.flush()
    instructor = User(username="tunnel-instructor", password_hash=hash_password("I" * 16), role=Role.INSTRUCTOR.value)
    student = User(username="tunnel-team", password_hash=hash_password("T" * 16), role=Role.TEAM.value, team_id=team.id)
    db.add_all([instructor, student])
    db.commit()
    monkeypatch.setattr(tunnel_callbacks, "SessionLocal", lambda: db)
    monkeypatch.setattr(tunnel_callbacks, "get_authenticated_user", lambda _db, token: instructor if token == "instructor" else student)
    monkeypatch.setattr(tunnel_callbacks, "open_public_access", lambda _port: "https://workshop.gradio.live")

    status, url = tunnel_callbacks.open_public_access_from_ui("instructor")
    assert "sign-in is still required" in status.lower()
    assert url == "https://workshop.gradio.live"
    status, url = tunnel_callbacks.open_public_access_from_ui("student")
    assert "different role" in status.lower()
    assert not url
