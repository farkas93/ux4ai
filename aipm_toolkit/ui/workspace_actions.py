"""Save current editor values before an export or native-window close."""

from ..dimensions import DEFAULT_DIMENSIONS
from .callbacks import MAX_BACKLOG_ROWS, PLACEMENT_SLOTS, save_pending_project_edits


def _clear_empty_initial_edits(values):
    """Gradio mounts can emit input events for default/empty controls.

    With no selected project these are not unsaved work. Preserve real text,
    changed assessment scores, or improvement answers instead of discarding it.
    """
    if not any(values[2:9]):
        values[0] = False
    assessment_end = 11 + len(DEFAULT_DIMENSIONS) * 2
    assessment = values[11:assessment_end]
    if all(score in (None, 2.5) and not text for score, text in zip(assessment[::2], assessment[1::2])):
        values[9] = False
    improvement = assessment_end
    fields = values[improvement + 2:improvement + 14]
    if not fields[0] and all(answer in (None, "unknown") and not text
                             for answer, text in zip(fields[1:11:2], fields[2:11:2])):
        values[improvement] = False
    priority = improvement + 14
    for index in range(PLACEMENT_SLOTS):
        start = priority + index * 5
        if not values[start + 1]:
            values[start] = False
    rows = priority + PLACEMENT_SLOTS * 5
    for index in range(MAX_BACKLOG_ROWS):
        start = rows + index * 8
        if not any(values[start + 2:start + 7]):
            values[start] = False
    notes = rows + MAX_BACKLOG_ROWS * 8
    for index in range(len(DEFAULT_DIMENSIONS)):
        start = notes + index * 5
        if not values[start + 3]:
            values[start] = False
    improvement_note = notes + len(DEFAULT_DIMENSIONS) * 5
    if not values[improvement_note + 2]:
        values[improvement_note] = False


def save_current_edits(token, project_id, request, draft):
    values = list(draft)
    if not project_id:
        _clear_empty_initial_edits(values)
    # Setup (dirty, revision, seven fields), assessments (dirty, revisions,
    # score/rationale pairs), and improvement (dirty, id, twelve fields).
    offset = 2 + 7 + 2 + len(DEFAULT_DIMENSIONS) * 2 + 2 + 12
    for index in range(PLACEMENT_SLOTS):
        start = offset + index * 5
        if values[start + 1] and values[start + 2] is not None:
            # The visible pair is authoritative for this explicit save action,
            # even if a prior asynchronous slider request cleared its dirty flag.
            values[start] = True
    return save_pending_project_edits(token, project_id, request, *values)
