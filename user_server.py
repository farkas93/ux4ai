import gradio as gr
import plotly.graph_objects as go
import numpy as np
import pandas as pd
import json
import os

# --- Product Data ---
PRODUCTS = {
    "DeepL": {"description": "A powerful neural machine translation service.", "url": "https://www.deepl.com/translator", "default_scores": {"conversational": 2.0, "personalization": 1.0, "autonomy": 3.0, "accessibility": 4.5, "explainability": 2.0}},
    "Google Search": {"description": "A web search engine that indexes and searches the World Wide Web.", "url": "https://www.google.com", "default_scores": {"conversational": 1.5, "personalization": 4.0, "autonomy": 3.5, "accessibility": 5.0, "explainability": 1.5}},
    "Perplexity": {"description": "An AI-powered conversational search engine that answers questions.", "url": "https://www.perplexity.ai/", "default_scores": {"conversational": 4.0, "personalization": 3.0, "autonomy": 4.0, "accessibility": 4.0, "explainability": 3.0}},
    "Gemini": {"description": "Google's advanced conversational AI model.", "url": "https://gemini.google.com/", "default_scores": {"conversational": 4.5, "personalization": 4.0, "autonomy": 4.5, "accessibility": 4.5, "explainability": 3.5}},
    "Claude": {"description": "An AI assistant from Anthropic focused on helpfulness, honesty, and harmlessness.", "url": "https://claude.ai/", "default_scores": {"conversational": 4.2, "personalization": 3.5, "autonomy": 4.2, "accessibility": 4.2, "explainability": 3.8}},
    "ChatGPT": {"description": "A versatile conversational AI model developed by OpenAI.", "url": "https://chat.openai.com/", "default_scores": {"conversational": 4.3, "personalization": 3.8, "autonomy": 4.3, "accessibility": 4.8, "explainability": 3.2}},
    "Copilot": {"description": "Microsoft's AI companion that helps with various tasks across different applications.", "url": "https://copilot.microsoft.com/", "default_scores": {"conversational": 4.0, "personalization": 4.2, "autonomy": 4.0, "accessibility": 4.7, "explainability": 3.0}},
    "Other": {"description": "Please specify the product name below.", "url": "", "default_scores": {}}
}

# --- Function to update product info and reset sliders ---
def update_product_info(selected_product):
    if selected_product in PRODUCTS:
        product_data = PRODUCTS[selected_product]
        description = product_data["description"]
        url = product_data["url"]

        html_content = f"""
        <div style="border: none; background-color: transparent; padding: 0; margin: 0;">
            <p style="margin: 0 0 5px 0;">{description}</p>
            <a href="{url}" target="_blank" style="color: #1E88E5; text-decoration: none;">{url}</a>
        </div>
        """
        return (
            html_content,
            gr.update(value=2.5), # Conversational
            gr.update(value=2.5), # Personalization
            gr.update(value=2.5), # Autonomy
            gr.update(value=2.5), # Accessibility
            gr.update(value=2.5), # Explainability
            gr.update(value=None), # AI Role Radio
            gr.update(value=2.5), # Risk level slider
            gr.update(value=""),  # Clear risk description textbox
            gr.update(value=2.5), # Continuous learning analytics type slider
            gr.update(value=""),  # Clear continuous learning aspects textbox
            gr.update(value=""),  # Clear continuous learning explanation textbox
            gr.update(visible=False) # Hide the "Load Product" button after it's clicked
        )
    return (
        "", gr.update(value=2.5), gr.update(value=2.5), gr.update(value=2.5),
        gr.update(value=2.5), gr.update(value=2.5), gr.update(value=None),
        gr.update(value=2.5), gr.update(value=""), gr.update(value=2.5),
        gr.update(value=""), gr.update(value=""), gr.update(visible=False)
    )

# --- Function to handle dropdown selection ---
def handle_product_selection(selected_product):
    if selected_product == "Other":
        return gr.update(visible=True), gr.update(visible=True)
    elif selected_product:
        return gr.update(visible=False), gr.update(visible=True)
    return gr.update(visible=False), gr.update(visible=False)

# --- Function to generate the spider diagram using Plotly ---
def create_spider_diagram_plotly(conversational, personalization, autonomy, accessibility, explainability):
    labels = ['Conversational', 'Personalization', 'Autonomy', 'Accessibility', 'Explainability']
    values = [conversational, personalization, autonomy, accessibility, explainability]
    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(r=values, theta=labels, fill='toself', name='Product Analysis'))
    fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 5])), showlegend=True, title="UX4AI Product Analysis", height=600)
    return fig

# --- Function to capture all data and save it to file ---
def capture_all_data(
    username_full,
    selected_product,
    other_product_name,
    ai_role, # ADDED: New parameter for the radio button value.
    conversational, personalization, autonomy, accessibility, explainability,
    risk_level,
    risk_assessment_description,
    continuous_learning_analytics_type,
    continuous_learning_aspects,
    continuous_learning_explanation
):
    # Username Validation and Formatting
    username_parts = username_full.strip().split()
    if len(username_parts) < 2 or not all(part.isalpha() for part in username_parts):
        return "", "Error: Please enter your full name (e.g., 'Peter Mueller')."
    
    formatted_username = username_parts[0][0].upper() + username_parts[-1].capitalize()

    # Product Name Logic
    product_name_to_save = ""
    if selected_product == "Other":
        if not other_product_name.strip():
            return "", "Error: Please specify the product name when 'Other' is selected."
        product_name_to_save = other_product_name.strip()
    else:
        product_name_to_save = selected_product

    # Prepare the data payload
    analysis_data = {
        "username": formatted_username,
        "product_name": product_name_to_save,
        "ai_role": ai_role, # ADDED: Save the value from the new radio buttons.
        "scores": {
            "conversational": conversational,
            "personalization": personalization,
            "autonomy": autonomy,
            "accessibility": accessibility,
            "explainability": explainability
        },
        "risk_of_adversarial_attacks": {
            "level": risk_level,
            "description": risk_assessment_description
        },
        "continuous_learning_feedback_loops": {
            "aspects": continuous_learning_aspects,
            "analytics_type_level": continuous_learning_analytics_type,
            "analytics_type_explanation": continuous_learning_explanation
        }
    }

    # Convert the data to a JSON string
    json_output_string = json.dumps(analysis_data, indent=4)

    # --- File Saving Logic ---
    try:
        safe_product_name = product_name_to_save.lower().replace(" ", "_").replace("/", "_")
        base_data_dir = "./data"
        user_data_dir = os.path.join(base_data_dir, formatted_username)
        os.makedirs(user_data_dir, exist_ok=True)
        file_path = os.path.join(user_data_dir, f"{safe_product_name}.json")
        
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(json_output_string)
            
        success_message = f"Analysis submitted and saved to: {file_path}"
        return success_message, "Data successfully submitted!"
        
    except Exception as e:
        error_message = f"Error saving data: {e}"
        return "", f"Failed to submit data: {e}"

# --- Gradio Interface ---
with gr.Blocks() as demo:
    gr.Markdown("# UX4AI Product Analysis Workshop")

    with gr.Row():
        with gr.Column():
            username_input = gr.Textbox(
                label="Your Full Name",
                info="Enter your first and last name (e.g., 'Peter Mueller'). Will be formatted as 'PMueller'.",
                placeholder="e.g., Peter Mueller"
            )

            product_dropdown = gr.Dropdown(
                choices=list(PRODUCTS.keys()),
                label="Select AI Product",
                info="Choose a product or select 'Other' to specify your own."
            )
            
            other_product_name_input = gr.Textbox(
                label="Specify Product Name",
                placeholder="Enter the name of the product",
                visible=False,
                interactive=True
            )

            load_product_btn = gr.Button("Load Product and Reset Form", visible=False)

            product_info_html = gr.HTML(label="Product Details")

            # ADDED: Radio buttons to classify the AI's role in the product.
            ai_role_radio = gr.Radio(
                ["AI is a Feature", "AI is the Product"],
                label="AI's Role in the Product",
                info="Is the AI a core component (feature) or the entire product itself?"
            )

            gr.Markdown("### UX4AI Dimensions")
            # Sliders for UX4AI Spider Diagram
            conversational = gr.Slider(minimum=0.0, maximum=5.0, step=0.1, label="Conversational (0: Guided, 5: Free)", value=2.5)
            personalization = gr.Slider(minimum=0.0, maximum=5.0, step=0.1, label="Personalization (0: General, 5: Personalized)", value=2.5)
            autonomy = gr.Slider(minimum=0.0, maximum=5.0, step=0.1, label="Autonomy (0: Procedural, 5: Full Agentic)", value=2.5)
            accessibility = gr.Slider(minimum=0.0, maximum=5.0, step=0.1, label="Accessibility (0: Niche, 5: Everyone)", value=2.5)
            explainability = gr.Slider(minimum=0.0, maximum=5.0, step=0.1, label="Explainability (0: Blackbox, 5: Fully Transparent)", value=2.5)

            gr.Markdown("---") # Separator for clarity

            # Risk of Adversarial Attacks Section
            risk_level_slider = gr.Slider(
                minimum=0.0, maximum=5.0, step=0.1,
                label="Risk of Adversarial Attacks (0: No Risk, 5: High Risk)",
                info="Indicate on the scale where you estimate the risk of the tool being exposed to adversarial attacks.",
                value=2.5
            )
            risk_assessment_description = gr.Textbox(
                label="Worst-case damage description",
                info="Describe in a few sentences the worst-case damage an adversarial attack could have.",
                lines=3
            )

            gr.Markdown("---") # Separator for clarity

            # Continuous Learning & Feedback Loops Section
            continuous_learning_aspects = gr.Textbox(
                label="Continuous Learning & Feedback Loops Aspects",
                info="For what aspects of the Product could you imagine to implement 'Continuous Learning & Feedback Loops'? Name a few bullet points and explain with max 2 sentences.",
                lines=5
            )
            continuous_learning_analytics_type_slider = gr.Slider(
                minimum=0.0, maximum=5.0, step=0.1,
                label="Analytics Type (0: Manual Analytics, 5: AI-driven Analytics)",
                info="Indicate if those points can be implemented via manual or AI driven analytics on the slider.",
                value=2.5
            )
            continuous_learning_explanation = gr.Textbox(
                label="Explain your Analytics Type Pick",
                info="Explain your pick on the scale in a few sentences.",
                lines=3
            )

            capture_data_btn = gr.Button("Submit My Analysis")

        with gr.Column():
            plotly_chart_output = gr.Plot(label="UX4AI Spider Diagram")
            json_output_display = gr.Textbox(label="Data Submitted To", lines=1, interactive=False)
            status_message = gr.Textbox(label="Status", interactive=False)


    # --- Event Handling ---
    product_dropdown.change(
        fn=handle_product_selection,
        inputs=[product_dropdown],
        outputs=[other_product_name_input, load_product_btn]
    )

    load_product_btn.click(
        fn=update_product_info,
        inputs=[product_dropdown],
        outputs=[
            product_info_html,
            conversational, personalization, autonomy, accessibility, explainability,
            ai_role_radio, # ADDED: Ensure the radio button is reset when loading a product.
            risk_level_slider,
            risk_assessment_description,
            continuous_learning_analytics_type_slider,
            continuous_learning_aspects,
            continuous_learning_explanation,
            load_product_btn
        ]
    )

    sliders = [conversational, personalization, autonomy, accessibility, explainability]
    for slider in sliders:
        slider.change(
            fn=create_spider_diagram_plotly,
            inputs=sliders,
            outputs=plotly_chart_output
        )

    capture_data_btn.click(
        fn=capture_all_data,
        inputs=[
            username_input,
            product_dropdown,
            other_product_name_input,
            ai_role_radio, # ADDED: Pass the new radio button component as an input.
            conversational, personalization, autonomy, accessibility, explainability,
            risk_level_slider,
            risk_assessment_description,
            continuous_learning_analytics_type_slider,
            continuous_learning_aspects,
            continuous_learning_explanation
        ],
        outputs=[json_output_display, status_message]
    )

# --- Launching the Gradio App ---
if __name__ == "__main__":
    demo.launch(share=True)