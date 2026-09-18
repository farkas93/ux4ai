from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from aipm_toolkit.app import _resolve_token
from aipm_toolkit.auth import hash_password
from aipm_toolkit.db import Base
from aipm_toolkit.models import Role, User
from aipm_toolkit.web import create_auth_app


def test_cookie_session_protects_app_and_supports_logout(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'web.db'}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory.begin() as db:
        db.add(User(username="web-user", password_hash=hash_password("P" * 16), role=Role.INSTRUCTOR.value))
    client = TestClient(create_auth_app(factory))

    protected = client.get("/app", follow_redirects=False)
    assert protected.status_code == 303
    assert protected.headers["location"].startswith("/auth/login")

    invalid = client.post("/auth/login", data={"username": "web-user", "password": "wrong", "next": "/app"}, follow_redirects=False)
    assert invalid.status_code == 401
    login = client.post("/auth/login", data={"username": "web-user", "password": "P" * 16, "next": "/app"}, follow_redirects=False)
    assert login.status_code == 303
    assert "aipm_session" in login.headers["set-cookie"]
    assert "HttpOnly" in login.headers["set-cookie"]
    assert client.get("/app", follow_redirects=False).status_code != 303

    logout = client.get("/auth/logout", follow_redirects=False)
    assert logout.status_code == 303
    assert client.get("/app", follow_redirects=False).status_code == 303


def test_gradio_callback_identity_prefers_request_cookie():
    class Request:
        class Inner:
            def __init__(self):
                self.cookies = {"aipm_session": "cookie-session"}

        request = Inner()

    assert _resolve_token("client-state-token", Request()) == "cookie-session"
