"""Dirty-only setup autosave that retains edits newer than a submitted save."""

import gradio as gr

from .callbacks import autosave_project_from_ui, save_project_action


def track_setup_edits(*fields):
    return True, tuple(fields)


def autosave_timer_state(dirty, switching):
    return gr.update(active=bool(dirty and not switching))


def _keep_newer_edits(result, latest_draft, submitted):
    status, revision, dirty = result
    if latest_draft is not None and tuple(latest_draft) != submitted:
        if isinstance(status, str) and status.startswith("Product setup saved"):
            status = "Earlier changes saved; newer edits are still pending."
        dirty = True
    return status, revision, dirty


def save_setup(
    token, project_id, revision, latest_draft, product_type, description,
    target_user, job, problem, hypothesis, figma_url, request: gr.Request | None = None,
):
    fields = (product_type, description, target_user, job, problem, hypothesis, figma_url)
    result = save_project_action(token, project_id, revision, *fields, request=request)
    return _keep_newer_edits(result, latest_draft, fields)


def autosave_setup(
    token, project_id, revision, dirty, latest_draft, product_type, description,
    target_user, job, problem, hypothesis, figma_url, switching=False,
    request: gr.Request | None = None,
):
    fields = (product_type, description, target_user, job, problem, hypothesis, figma_url)
    result = autosave_project_from_ui(
        token, project_id, revision, dirty, *fields, switching, request=request,
    )
    if not dirty or switching:
        return result
    return _keep_newer_edits(result, latest_draft, fields)
