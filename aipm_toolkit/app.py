"""Minimal authenticated Gradio shell for the Phase 1 foundation."""

from uuid import UUID

import gradio as gr

from .auth import AuthenticationError, RevisionConflict, authenticate, get_authenticated_user
from .db import SessionLocal
from .models import Role
from .services import (
    create_project,
    get_project,
    list_projects,
    update_main_hypothesis,
    update_project,
    validate_figma_url,
)


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
        return "Instructor area: course progress, teams, and baselines.", gr.update(visible=False), gr.update(visible=True), gr.update(visible=False), gr.update()
    with SessionLocal() as db:
        projects = list_projects(db, user)
    choices = [(project.product_name, str(project.id)) for project in projects]
    return "Select an existing project or create a new draft.", gr.update(visible=False), gr.update(visible=False), gr.update(visible=True), gr.update(choices=choices, value=choices[0][1] if choices else None)


def create_project_from_ui(token: str, product_name: str):
    with SessionLocal() as db:
        try:
            user = get_authenticated_user(db, token)
            project = create_project(db, user, product_name)
            choices = [(item.product_name, str(item.id)) for item in list_projects(db, user)]
        except (AuthenticationError, ValueError) as exc:
            return str(exc), gr.update(), gr.update(), gr.update()
    return "Draft created. Your project brief is ready.", gr.update(choices=choices, value=str(project.id)), gr.update(value=project.product_name), gr.update(value=project.revision)


def load_project_from_ui(token: str, project_id: str | None):
    if not project_id:
        return "", "", "", "", "", "", "", "", "", None, None
    with SessionLocal() as db:
        try:
            user = get_authenticated_user(db, token)
            project = get_project(db, user, UUID(project_id))
            hypothesis = next(iter(project.hypotheses), None)
        except (AuthenticationError, ValueError, LookupError):
            return "Unable to load that project.", "", "", "", "", "", "", "", "", None, None
    return (
        "Project Brief",
        project.product_name,
        project.short_description,
        project.target_user,
        project.job_to_be_done,
        project.current_problem,
        hypothesis.statement if hypothesis else "",
        project.product_type,
        project.figma_url,
        str(project.id),
        project.revision,
    )


def save_project_from_ui(token: str, project_id: str | None, revision: int | None, product_name: str, product_type: str | None, description: str, target_user: str, job: str, problem: str, hypothesis: str, figma_url: str):
    if not project_id or revision is None:
        return "Select a project first.", revision
    with SessionLocal() as db:
        try:
            user = get_authenticated_user(db, token)
            updated_url = validate_figma_url(figma_url)
            project = update_project(db, user, UUID(project_id), revision, product_name=product_name.strip(), product_type=product_type, short_description=description, target_user=target_user, job_to_be_done=job, current_problem=problem, figma_url=updated_url)
            main = next(iter(project.hypotheses), None)
            if main:
                update_main_hypothesis(db, user, project.id, main.revision, hypothesis)
        except (AuthenticationError, RevisionConflict, ValueError) as exc:
            return str(exc), revision
    return "Saved.", project.revision


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
        with gr.Column(visible=False) as instructor_panel:
            gr.Markdown("## Instructor area\nCourse progress, teams, baseline imports, and catalog administration will appear here.")
        with gr.Column(visible=False) as team_panel:
            gr.Markdown("## Project Brief")
            with gr.Row():
                project_dropdown = gr.Dropdown(label="Your projects", choices=[], interactive=True)
                new_project_name = gr.Textbox(label="New product name", placeholder="Only the product name is required")
                create_button = gr.Button("Create draft")
            project_title = gr.Markdown()
            with gr.Row():
                product_name = gr.Textbox(label="Product name")
                product_type = gr.Dropdown(label="AI product type", choices=["Feature", "Plugin", "Native", "Mixed/Undecided"], value=None)
            description = gr.Textbox(label="Short description", lines=3)
            target_user = gr.Textbox(label="Target user")
            job = gr.Textbox(label="Job to be done", lines=3)
            problem = gr.Textbox(label="Current problem or workflow", lines=3)
            hypothesis = gr.Textbox(label="Main value hypothesis", lines=4, placeholder="If we help [user] accomplish [job] through [capability], we expect [outcome] to improve while maintaining [constraint].")
            figma_url = gr.Textbox(label="Figma prototype URL (optional)")
            save_button = gr.Button("Save brief", variant="primary")
            project_id = gr.State(None)
            project_revision = gr.State(None)
        submit.click(login, [username, password], [status, token, login_panel, workspace_panel]).then(workspace, token, [workspace_text, login_panel, instructor_panel, team_panel, project_dropdown])
        create_button.click(create_project_from_ui, [token, new_project_name], [status, project_dropdown, product_name, project_revision])
        project_dropdown.change(load_project_from_ui, [token, project_dropdown], [project_title, product_name, description, target_user, job, problem, hypothesis, product_type, figma_url, project_id, project_revision])
        save_button.click(save_project_from_ui, [token, project_id, project_revision, product_name, product_type, description, target_user, job, problem, hypothesis, figma_url], [status, project_revision])
    return app


app = build_app()


if __name__ == "__main__":
    app.launch()
