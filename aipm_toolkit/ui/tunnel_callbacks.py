"""Instructor-only controls for the optional public Gradio link."""

import os

import gradio as gr

from ..auth import (
    AuthenticationError,
    AuthorizationError,
    Role,
    get_authenticated_user,
    require_role,
)
from ..db import SessionLocal
from ..tunnel_services import close_public_access, open_public_access, public_access_status
from .callbacks import _resolve_token


def public_access_status_from_ui(token: str | None, request: gr.Request | None = None):
    try:
        with SessionLocal() as db:
            actor = get_authenticated_user(db, _resolve_token(token, request))
            require_role(actor, Role.INSTRUCTOR)
        status = public_access_status()
    except (AuthenticationError, AuthorizationError) as exc:
        return str(exc), ""
    if status["enabled"]:
        return "Public Gradio link is open. Sign-in is still required.", status["url"] or ""
    return "Public Gradio link is closed. LAN access remains available.", ""


def open_public_access_from_ui(token: str | None, request: gr.Request | None = None):
    try:
        with SessionLocal() as db:
            actor = get_authenticated_user(db, _resolve_token(token, request))
            require_role(actor, Role.INSTRUCTOR)
        url = open_public_access(int(os.getenv("AIPM_PORT", "7860")))
        return "Public Gradio link is open. Sign-in is still required.", url
    except (AuthenticationError, AuthorizationError) as exc:
        return str(exc), ""
    except Exception as exc:  # noqa: BLE001 - tunnel setup raises Gradio/FRP-specific exceptions
        return f"Unable to open the public Gradio link: {exc}", ""


def close_public_access_from_ui(token: str | None, request: gr.Request | None = None):
    try:
        with SessionLocal() as db:
            actor = get_authenticated_user(db, _resolve_token(token, request))
            require_role(actor, Role.INSTRUCTOR)
        close_public_access()
        return "Public Gradio link is closed. LAN access remains available.", ""
    except (AuthenticationError, AuthorizationError) as exc:
        return str(exc), ""
