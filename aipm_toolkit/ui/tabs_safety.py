"""AI Safety: design coverage rather than a product safety rating."""

import gradio as gr

from ..safety_services import CHECKPOINTS
from .safety_callbacks import create_safety_hypothesis_ui, live_safety_card, save_safety_ui


def build_safety_tab(token, product_dropdown, status):
    with gr.Tab("AI Safety") as tab:
        gr.Markdown("Evaluate **safety design coverage**, not how safe the product is. 'Tested' is a team claim, not a certification.")
        inputs = []
        hypothesis_events = []
        for key, (title, prompt) in CHECKPOINTS.items():
            with gr.Accordion(title, open=(key == "scope")):
                gr.Markdown(prompt)
                coverage = gr.Radio(choices=[("Not addressed", "not_addressed"), ("Partly specified", "partly_specified"),
                                             ("Clearly specified", "clearly_specified"), ("Unknown", "unknown")], label="Coverage", value=None)
                maturity = gr.Radio(choices=[("Planned", "planned"), ("Implemented", "implemented"), ("Tested", "tested")], label="Maturity (team claim)", value=None)
                evidence = gr.Textbox(label="Justification or evidence", lines=3)
                with gr.Row():
                    hypothesis = gr.Textbox(label="Testable safety hypothesis", placeholder="If ..., then ...")
                    create_button = gr.Button("Create hypothesis")
                checkpoint = gr.State(key)
                hypothesis_events.append(create_button.click(create_safety_hypothesis_ui, [token, product_dropdown, checkpoint, hypothesis], [status, hypothesis]))
                inputs.extend([coverage, maturity, evidence])
        risk = gr.Textbox(label="Critical unresolved risk", placeholder="Describe a concrete unresolved risk, if known", lines=2)
        revision = gr.State(None)
        card = gr.Markdown()
        save = gr.Button("Save AI safety assessment", variant="primary")
        for component in [*inputs, risk]:
            component.change(live_safety_card, [*inputs, risk], card)
        save.click(save_safety_ui, [token, product_dropdown, revision, *inputs, risk], [status, revision, card])
    return {"tab": tab, "inputs": [*inputs, risk], "revision": revision, "card": card, "hypothesis_events": hypothesis_events}
