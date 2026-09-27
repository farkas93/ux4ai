"""AI Safety: design coverage rather than a product safety rating."""

import gradio as gr

from ..safety_services import CHECKPOINTS
from .safety_callbacks import add_learning_note_ui, live_safety_card, save_safety_ui


def build_safety_tab(token, product_dropdown, status):
    with gr.Tab("AI Safety") as tab:
        gr.Markdown("Discuss where the idea might cause harm or need safeguards. Add questions and assumptions here, then turn them into hypotheses in **Backlog Creator**.")
        inputs = []
        note_events = []
        note_lists = []
        checkpoint_states = []
        section = gr.State("safety")
        for key, (title, prompt) in CHECKPOINTS.items():
            with gr.Accordion(title, open=(key == "scope")):
                gr.Markdown(prompt)
                notes_list = gr.Textbox(label="Current questions and assumptions", interactive=False, lines=3)
                note_lists.append(notes_list)
                with gr.Row():
                    note_type = gr.Radio(choices=["Question", "Assumption"], value="Question", label="Add")
                    text = gr.Textbox(label="What needs exploring?", scale=3)
                    add_button = gr.Button("Add", scale=1)
                checkpoint = gr.State(key)
                checkpoint_states.append(checkpoint)
                note_events.append(add_button.click(add_learning_note_ui, [token, product_dropdown, section, checkpoint, note_type, text], [status, notes_list, text]))
                with gr.Accordion("Optional: assess design coverage", open=False):
                    coverage = gr.Radio(choices=[("Not addressed", "not_addressed"), ("Partly specified", "partly_specified"),
                                                 ("Clearly specified", "clearly_specified"), ("Unknown", "unknown")], label="Coverage", value=None)
                    maturity = gr.Radio(choices=[("Planned", "planned"), ("Implemented", "implemented"), ("Tested", "tested")], label="Maturity (team claim)", value=None)
                    evidence = gr.Textbox(label="Justification or evidence", lines=2)
                inputs.extend([coverage, maturity, evidence])
        with gr.Accordion("Optional: safety design coverage summary", open=False):
            gr.Markdown("Coverage describes what the team has specified; it does not rate how safe the product is. 'Tested' is a team claim.")
            risk = gr.Textbox(label="Critical unresolved risk", placeholder="Describe an unresolved risk, if known", lines=2)
            revision = gr.State(None)
            card = gr.Markdown()
            save = gr.Button("Save design coverage", variant="primary")
            for component in [*inputs, risk]:
                component.change(live_safety_card, [*inputs, risk], card)
            save.click(save_safety_ui, [token, product_dropdown, revision, *inputs, risk], [status, revision, card])
    return {"tab": tab, "inputs": [*inputs, risk], "revision": revision, "card": card, "note_events": note_events, "note_lists": note_lists, "note_section": section, "checkpoint_states": checkpoint_states}
