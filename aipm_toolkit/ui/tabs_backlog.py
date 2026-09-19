"""Backlog creator tab: assumptions | questions | hypothesis columns with derivation."""

import gradio as gr

from ..dimensions import DEFAULT_DIMENSIONS
from .callbacks import (
    backlog_columns_from_ui,
    derive_hypothesis_from_note,
    filter_hypotheses_from_ui,
    load_backlog_from_ui,
    load_hypothesis_edit_from_ui,
    load_note_edit_from_ui,
    save_hypothesis_edit_from_ui,
    save_hypothesis_from_ui,
    save_note_edit_from_ui,
    save_relation_from_ui,
)

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
        gr.Markdown("Derive one supporting hypothesis from each question or assumption you recorded in the Assessment tab. Numbered items come from your dimension notes.")
        with gr.Row():
            with gr.Column():
                gr.Markdown("### 1. Assumptions")
                assumptions_display = gr.Textbox(label="Assumptions from Assessment", interactive=False, lines=6)
                assumption_selector = gr.Dropdown(label="Select assumption to derive from", choices=[])
                derive_from_assumption = gr.Button("Derive hypothesis from assumption")
            with gr.Column():
                gr.Markdown("### 2. Questions")
                questions_display = gr.Textbox(label="Questions from Assessment", interactive=False, lines=6)
                question_selector = gr.Dropdown(label="Select question to derive from", choices=[])
                derive_from_question = gr.Button("Derive hypothesis from question")
            with gr.Column():
                gr.Markdown("### 3. Hypothesis")
                hypothesis_statement = gr.Textbox(label="Supporting hypothesis statement", lines=3, placeholder="Complete or confirm the hypothesis statement here.")
                hypothesis_value_link = gr.Textbox(label="Why it matters / value link", lines=2)
                hypothesis_impact = gr.Dropdown(label="Impact if wrong", choices=IMPACT_CHOICES, value="unknown")
                hypothesis_evidence = gr.Dropdown(label="Evidence strength", choices=EVIDENCE_CHOICES, value="unknown")
                hypothesis_evidence_rationale = gr.Textbox(label="Evidence rationale", lines=2)
                hypothesis_note = gr.Dropdown(label="Originating note (provenance)", choices=[])
                save_hypothesis_button = gr.Button("Create supporting hypothesis", variant="primary")

        gr.Markdown("## Hypothesis backlog")
        hypotheses_display = gr.Textbox(label="Hypothesis backlog", interactive=False, lines=8)
        hypothesis_filter_dimension = gr.Dropdown(label="Filter dimension", choices=[("All dimensions", "all")] + [(definition["title"], definition["key"]) for definition in DEFAULT_DIMENSIONS], value="all")
        hypothesis_filter_status = gr.Dropdown(label="Filter workflow status", choices=[("All statuses", "all"), "draft", "ready_to_test", "testing", "reviewed", "archived"], value="all")
        hypothesis_filter_impact = gr.Dropdown(label="Filter impact", choices=[("All impact", "all")] + IMPACT_CHOICES, value="all")
        hypothesis_filter_evidence = gr.Dropdown(label="Filter evidence", choices=[("All evidence", "all")] + EVIDENCE_CHOICES, value="all")
        with gr.Row():
            with gr.Column():
                gr.Markdown("### Edit hypothesis")
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
            with gr.Column():
                gr.Markdown("### Edit note (optional)")
                note_edit_selector = gr.Dropdown(label="Reopen note", choices=[])
                note_edit_type = gr.Dropdown(label="Edited note type", choices=[("Observation", "observation"), ("Assumption", "assumption"), ("Question", "question"), ("Design decision", "design_decision")], value="question")
                note_edit_text = gr.Textbox(label="Edited note", lines=3)
                note_edit_dimensions = gr.CheckboxGroup(label="Edited linked dimensions", choices=[definition["title"] for definition in DEFAULT_DIMENSIONS])
                note_edit_revision = gr.State(None)
                update_note_button = gr.Button("Update note")
        notes_display = gr.Textbox(label="All notes", interactive=False, lines=5)

        derive_from_assumption.click(derive_hypothesis_from_note, [token, assumption_selector], [hypothesis_statement, hypothesis_note])
        derive_from_question.click(derive_hypothesis_from_note, [token, question_selector], [hypothesis_statement, hypothesis_note])
        save_hypothesis_button.click(save_hypothesis_from_ui, [token, project_id, hypothesis_statement, hypothesis_value_link, hypothesis_impact, hypothesis_evidence, hypothesis_evidence_rationale, hypothesis_note], [status, hypotheses_display, relation_source]).then(load_backlog_from_ui, [token, project_id], [notes_display, hypotheses_display, hypothesis_note, relation_source, relation_target, note_edit_selector, hypothesis_edit_selector]).then(backlog_columns_from_ui, [token, project_id], [assumption_selector, question_selector, assumptions_display, questions_display])
        for hypothesis_filter in (hypothesis_filter_dimension, hypothesis_filter_status, hypothesis_filter_impact, hypothesis_filter_evidence):
            hypothesis_filter.change(filter_hypotheses_from_ui, [token, project_id, hypothesis_filter_dimension, hypothesis_filter_status, hypothesis_filter_impact, hypothesis_filter_evidence], [hypotheses_display, relation_source, relation_target])
        hypothesis_edit_selector.change(load_hypothesis_edit_from_ui, [token, hypothesis_edit_selector], [hypothesis_edit_statement, hypothesis_edit_value, hypothesis_edit_impact, hypothesis_edit_evidence, hypothesis_edit_rationale, hypothesis_edit_revision])
        update_hypothesis_button.click(save_hypothesis_edit_from_ui, [token, hypothesis_edit_selector, hypothesis_edit_revision, hypothesis_edit_statement, hypothesis_edit_value, hypothesis_edit_impact, hypothesis_edit_evidence, hypothesis_edit_rationale], [status, hypothesis_edit_revision, hypotheses_display]).then(load_backlog_from_ui, [token, project_id], [notes_display, hypotheses_display, hypothesis_note, relation_source, relation_target, note_edit_selector, hypothesis_edit_selector])
        save_relation_button.click(save_relation_from_ui, [token, project_id, relation_type, relation_source, relation_target], status)
        note_edit_selector.change(load_note_edit_from_ui, [token, note_edit_selector], [note_edit_type, note_edit_text, note_edit_revision, note_edit_dimensions])
        update_note_button.click(save_note_edit_from_ui, [token, note_edit_selector, note_edit_revision, note_edit_type, note_edit_text, note_edit_dimensions], [status, note_edit_revision, notes_display]).then(load_backlog_from_ui, [token, project_id], [notes_display, hypotheses_display, hypothesis_note, relation_source, relation_target, note_edit_selector, hypothesis_edit_selector]).then(backlog_columns_from_ui, [token, project_id], [assumption_selector, question_selector, assumptions_display, questions_display])

    return {
        "tab": tab,
        "notes_display": notes_display,
        "note_edit_selector": note_edit_selector,
        "hypotheses_display": hypotheses_display,
        "hypothesis_note": hypothesis_note,
        "relation_source": relation_source,
        "relation_target": relation_target,
        "hypothesis_edit_selector": hypothesis_edit_selector,
        "assumption_selector": assumption_selector,
        "question_selector": question_selector,
        "assumptions_display": assumptions_display,
        "questions_display": questions_display,
    }
