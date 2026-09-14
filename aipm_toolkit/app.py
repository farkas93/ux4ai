"""Minimal authenticated Gradio shell for the Phase 1 foundation."""

import gradio as gr

from .auth import AuthenticationError, authenticate, get_authenticated_user
from .db import SessionLocal
from .models import Role


def login(username: str, password: str):
    with SessionLocal() as db:
        try:
            token, user = authenticate(db, username, password)
        except AuthenticationError as exc:
            return gr.update(value=str(exc)), None, gr.update(visible=True), gr.update(visible=False)
    # The production FastAPI adapter will set this token as an HttpOnly cookie.
    # Keeping it in State here makes the shell usable while the adapter is wired.
    return gr.update(value=f"Signed in as {user.username}"), token, gr.update(visible=False), gr.update(visible=True)


def workspace(token: str):
    with SessionLocal() as db:
        try:
            user = get_authenticated_user(db, token)
        except AuthenticationError:
            return "Session expired. Please sign in again.", gr.update(visible=True), gr.update(visible=False)
    if user.role == Role.INSTRUCTOR.value:
        return "Instructor area: course progress, teams, and baselines.", gr.update(visible=False), gr.update(visible=True)
    return "Team workspace: Project Brief, Dimension Explorer, Notes, Hypothesis Backlog, Experiments, Summary & Export.", gr.update(visible=False), gr.update(visible=True)


def build_app():
    with gr.Blocks(title="AIPM Toolkit") as app:
        token = gr.State(None)
        status = gr.Markdown()
        with gr.Column(visible=True) as login_panel:
            username = gr.Textbox(label="Team alias or instructor username")
            password = gr.Textbox(label="Password", type="password")
            submit = gr.Button("Sign in", variant="primary")
        with gr.Column(visible=False) as workspace_panel:
            workspace_text = gr.Markdown()
        submit.click(login, [username, password], [status, token, login_panel, workspace_panel]).then(workspace, token, [workspace_text, login_panel, workspace_panel])
    return app


app = build_app()


if __name__ == "__main__":
    app.launch()
