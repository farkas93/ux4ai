"""Backlog creator tab (slice 1 layout: notes and hypotheses, three columns arrive in slice 4)."""

import gradio as gr

from ..dimensions import DEFAULT_DIMENSIONS
from .callbacks import (
    filter_hypotheses_from_ui,
    load_backlog_from_ui,
    load_hypothesis_edit_from_ui,
    load_note_edit_from_ui,
    save_hypothesis_edit_from_ui,
    save_hypothesis_from_ui,
    save_note_edit_from_ui,
    save_note_from_ui,
    save_relation_from_ui,
)

NOTE_TYPE_CHOICES = [
    ("Observation", "observation"),
    ("Assumption", "assumption"),
    ("Question", "question"),
    ("Design decision", "design_decision"),
]
IMPACT_CHOICES = ["unknown", "low", "medium", "high"]
EVIDENCE_CHOICES = ["unknown", "none", "limited", "moderate", "strong"]
RELATION_CHOICES = [
    ("Contributes to", "contributes_to"),
    ("Depends on", "depends_on"),
    ("Alternative to", "alternative_to"),
    ("In tension with", "in_tension_with"),
]


def build_backlog_tab(token, project_id, status):
    with gr.Tab("Backlog creator") as tab:
        gr.Markdown("Derive supporting hypotheses from the questions and assumptions you recorded in the Assessment tab.")
        with gr.Row():
            with gr.Column():
                gr.Markdown("### Assumptions and questions")
                note_type = gr.Dropdown(label="Note type", choices=NOTE_TYPE_CHOICES, value="question")
                note_text = gr.Textbox(label="Note", lines=3)
                note_dimensions = gr.CheckboxGroup(label="Linked dimensions", choices=[definition["title"] for definition in DEFAULT_DIMENSIONS])
                save_note_button = gr.Button("Save note")
                notes_display = gr.Textbox(label="Saved notes", interactive=False, lines=6)
                note_edit_selector = gr.Dropdown(label="Reopen note", choices=[])
                note_edit_type = gr.Dropdown(label="Edited note type", choices=NOTE_TYPE_CHOICES, value="question")
                note_edit_text = gr.Textbox(label="Edited note", lines=3)
                note_edit_revision = gr.State(None)
                update_note_button = gr.Button("Update note")
            with gr.Column():
                gr.Markdown("### Hypothesis")
                hypothesis_statement = gr.Textbox(label="Supporting hypothesis statement", lines=3)
                hypothesis_value_link = gr.Textbox(label="Why it matters / value link", lines=2)
                hypothesis_impact = gr.Dropdown(label="Impact if wrong", choices=IMPACT_CHOICES, value="unknown")
                hypothesis_evidence = gr.Dropdown(label="Evidence strength", choices=EVIDENCE_CHOICES, value="unknown")
                hypothesis_evidence_rationale = gr.Textbox(label="Evidence rationale", lines=2)
                hypothesis_note = gr.Dropdown(label="Originating note (optional)", choices=[])
                save_hypothesis_button = gr.Button("Create supporting hypothesis")
                hypotheses_display = gr.Textbox(label="Hypothesis backlog", interactive=False, lines=8)
                hypothesis_filter_dimension = gr.Dropdown(label="Filter dimension", choices=[("All dimensions", "all")] + [(definition["title"], definition["key"]) for definition in DEFAULT_DIMENSIONS], value="all")
                hypothesis_filter_status = gr.Dropdown(label="Filter workflow status", choices=[("All statuses", "all"), "draft", "ready_to_test", "testing", "reviewed", "archived"], value="all")
                hypothesis_filter_impact = gr.Dropdown(label="Filter impact", choices=[("All impact", "all")] + IMPACT_CHOICES, value="all")
                hypothesis_filter_evidence = gr.Dropdown(label="Filter evidence", choices=[("All evidence", "all")] + EVIDENCE_CHOICES, value="all")
                hypothesis_edit_selector = gr.Dropdown(label="Reopen hypothesis", choices=[])
                hypothesis_edit_statement = gr.Textbox(label="Edited hypothesis statement", lines=3)
                hypothesis_edit_value = gr.Textbox(label="Edited value link", lines=2)
                hypothesis_edit_impact = gr.Dropdown(label="Edited impact if wrong", choices=IMPACT_CHOICES, value="unknown")
                hypothesis_edit_evidence = gr.Dropdown(label="Edited evidence strength", choices=EVIDENCE_CHOICES, value="unknown")
                hypothesis_edit_rationale = gr.Textbox(label="Edited evidence rationale", lines=2)
                hypothesis_edit_revision = gr.State(None)
                update_hypothesis_button = gr.Button("Update hypothesis")
            with gr.Column():
                gr.Markdown("### Link hypotheses")
                relation_type = gr.Dropdown(label="Relationship", choices=RELATION_CHOICES, value="contributes_to")
                relation_source = gr.Dropdown(label="From hypothesis", choices=[])
                relation_target = gr.Dropdown(label="To hypothesis", choices=[])
                save_relation_button = gr.Button("Save relationship")

        save_note_button.click(save_note_from_ui, [token, project_id, note_type, note_text, note_dimensions], [status, notes_display])
        note_edit_selector.change(load_note_edit_from_ui, [token, note_edit_selector], [note_edit_type, note_edit_text, note_edit_revision])
        update_note_button.click(save_note_edit_from_ui, [token, note_edit_selector, note_edit_revision, note_edit_type, note_edit_text, note_dimensions], [status, note_edit_revision, notes_display]).then(load_backlog_from_ui, [token, project_id], [notes_display, hypotheses_display, hypothesis_note, relation_source, relation_target, note_edit_selector, hypothesis_edit_selector])
        save_hypothesis_button.click(save_hypothesis_from_ui, [token, project_id, hypothesis_statement, hypothesis_value_link, hypothesis_impact, hypothesis_evidence, hypothesis_evidence_rationale, hypothesis_note], [status, hypotheses_display, relation_source]).then(load_backlog_from_ui, [token, project_id], [notes_display, hypotheses_display, hypothesis_note, relation_source, relation_target, note_edit_selector, hypothesis_edit_selector])
        for hypothesis_filter in (hypothesis_filter_dimension, hypothesis_filter_status, hypothesis_filter_impact, hypothesis_filter_evidence):
            hypothesis_filter.change(filter_hypotheses_from_ui, [token, project_id, hypothesis_filter_dimension, hypothesis_filter_status, hypothesis_filter_impact, hypothesis_filter_evidence], [hypotheses_display, relation_source, relation_target])
        hypothesis_edit_selector.change(load_hypothesis_edit_from_ui, [token, hypothesis_edit_selector], [hypothesis_edit_statement, hypothesis_edit_value, hypothesis_edit_impact, hypothesis_edit_evidence, hypothesis_edit_rationale, hypothesis_edit_revision])
        update_hypothesis_button.click(save_hypothesis_edit_from_ui, [token, hypothesis_edit_selector, hypothesis_edit_revision, hypothesis_edit_statement, hypothesis_edit_value, hypothesis_edit_impact, hypothesis_edit_evidence, hypothesis_edit_rationale], [status, hypothesis_edit_revision, hypotheses_display]).then(load_backlog_from_ui, [token, project_id], [notes_display, hypotheses_display, hypothesis_note, relation_source, relation_target, note_edit_selector, hypothesis_edit_selector])
        save_relation_button.click(save_relation_from_ui, [token, project_id, relation_type, relation_source, relation_target], status)

    return {
        "tab": tab,
        "notes_display": notes_display,
        "note_edit_selector": note_edit_selector,
        "hypotheses_display": hypotheses_display,
        "hypothesis_note": hypothesis_note,
        "relation_source": relation_source,
        "relation_target": relation_target,
        "hypothesis_edit_selector": hypothesis_edit_selector,
    }
