import gradio as gr
import plotly.graph_objects as go
import numpy as np
import pandas as pd
import json
import os

# --- Language setup ---
LANG_DIR = "./lang"
DEFAULT_LANG = "en"

# CHANGED: Removed direct dictionary definitions (LANG_EN, LANG_DE)
# The dictionaries will now be loaded from JSON files.

def load_lang_file(lang_code):
    # CHANGED: Load language dictionary from the specified JSON files in LANG_DIR.
    file_path = os.path.join(LANG_DIR, f"{lang_code}.json")
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Warning: Language file not found for '{lang_code}'. Falling back to default.")
        # Fallback to English if the requested language file is not found
        default_file_path = os.path.join(LANG_DIR, f"{DEFAULT_LANG}.json")
        with open(default_file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from '{file_path}'. Falling back to default.")
        # Fallback to English if the JSON is malformed
        default_file_path = os.path.join(LANG_DIR, f"{DEFAULT_LANG}.json")
        with open(default_file_path, "r", encoding="utf-8") as f:
            return json.load(f)


# CHANGED: Initialized LANG by loading from the default English JSON file.
# This ensures LANG is populated from the file system at startup.
LANG = load_lang_file(DEFAULT_LANG)

# --- Product Data ---
# CHANGED: Renamed 'personalization' key to 'specialization' in all product default_scores.
PRODUCTS = {
    "DeepL": {"description": "A powerful neural machine translation service.", "url": "https://www.deepl.com/translator", "default_scores": {"conversational": 2.0, "specialization": 1.0, "autonomy": 3.0, "accessibility": 4.5, "explainability": 2.0}},
    "Google Search": {"description": "A web search engine that indexes and searches the World Wide Web.", "url": "https://www.google.com", "default_scores": {"conversational": 1.5, "specialization": 4.0, "autonomy": 3.5, "accessibility": 5.0, "explainability": 1.5}},
    "Perplexity": {"description": "An AI-powered conversational search engine that answers questions.", "url": "https://www.perplexity.ai/", "default_scores": {"conversational": 4.0, "specialization": 3.0, "autonomy": 4.0, "accessibility": 4.0, "explainability": 3.0}},
    "Gemini": {"description": "Google's advanced conversational AI model.", "url": "https://gemini.google.com/", "default_scores": {"conversational": 4.5, "specialization": 4.0, "autonomy": 4.5, "accessibility": 4.5, "explainability": 3.5}},
    "Claude": {"description": "An AI assistant from Anthropic focused on helpfulness, honesty, and harmlessness.", "url": "https://claude.ai/", "default_scores": {"conversational": 4.2, "specialization": 3.5, "autonomy": 4.2, "accessibility": 4.2, "explainability": 3.8}},
    "ChatGPT": {"description": "A versatile conversational AI model developed by OpenAI.", "url": "https://chat.openai.com/", "default_scores": {"conversational": 4.3, "specialization": 3.8, "autonomy": 4.3, "accessibility": 4.8, "explainability": 3.2}},
    "Copilot": {"description": "Microsoft's AI companion that helps with various tasks across different applications.", "url": "https://copilot.microsoft.com/", "default_scores": {"conversational": 4.0, "specialization": 4.2, "autonomy": 4.0, "accessibility": 4.7, "explainability": 3.0}},
    "Other": {"description": "Please specify the product name below.", "url": "", "default_scores": {}}
}

# --- Function to update product info and reset sliders ---
# CHANGED: Renamed 'personalization' parameter to 'specialization'.
def update_product_info(selected_product, current_lang_dict):
    if selected_product in PRODUCTS:
        product_data = PRODUCTS[selected_product]
        description = product_data["description"]
        url = product_data["url"]

        html_content = f"""
        <div style="border: none; background-color: transparent; padding: 0; margin: 0;">
            {current_lang_dict["product_description_prefix"]}{description}{current_lang_dict["product_description_suffix"].format(url=url)}
        </div>
        """
        return (
            html_content,
            gr.update(value=2.5), # Conversational
            gr.update(value=2.5), # Specialization # CHANGED: Updated comment
            gr.update(value=2.5), # Autonomy
            gr.update(value=2.5), # Accessibility
            gr.update(value=2.5), # Explainability
            gr.update(value=None), # AI Role Radio
            gr.update(value=2.5), # Risk level slider
            gr.update(value=""),  # Clear risk description textbox
            gr.update(value=2.5), # Continuous learning analytics type slider
            gr.update(value=""),  # Clear continuous learning aspects textbox
            gr.update(value=""),  # Clear continuous learning explanation textbox
            gr.update(visible=False)
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
# CHANGED: Renamed 'personalization' parameter to 'specialization'.
def create_spider_diagram_plotly(conversational, specialization, autonomy, accessibility, explainability, current_lang_dict):
    labels = [
        current_lang_dict['conversational_label'].split('(')[0].strip(),
        current_lang_dict['specialization_label'].split('(')[0].strip(), # CHANGED: Used specialization_label
        current_lang_dict['autonomy_label'].split('(')[0].strip(),
        current_lang_dict['accessibility_label'].split('(')[0].strip(),
        current_lang_dict['explainability_label'].split('(')[0].strip()
    ]
    values = [conversational, specialization, autonomy, accessibility, explainability] # CHANGED: Used specialization
    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(r=values, theta=labels, fill='toself', name=current_lang_dict['spider_diagram_label']))
    fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 5])), showlegend=True, title=current_lang_dict['spider_diagram_label'], height=600)
    return fig

# --- Function to capture all data and save it to file ---
# CHANGED: Renamed 'personalization' parameter to 'specialization'.
def capture_all_data(
    username_full,
    selected_product,
    other_product_name,
    ai_role,
    conversational, specialization, autonomy, accessibility, explainability, # CHANGED: Renamed
    risk_level,
    risk_assessment_description,
    continuous_learning_analytics_type,
    continuous_learning_aspects,
    continuous_learning_explanation,
    current_lang_dict
):
    # Username Validation and Formatting
    username_parts = username_full.strip().split()
    if len(username_parts) < 2 or not all(part.isalpha() for part in username_parts):
        return "", current_lang_dict["error_full_name"]
    
    formatted_username = username_parts[0][0].upper() + username_parts[-1].capitalize()

    # Product Name Logic
    product_name_to_save = ""
    if selected_product == "Other":
        if not other_product_name.strip():
            return "", current_lang_dict["error_specify_product"]
        product_name_to_save = other_product_name.strip()
    else:
        product_name_to_save = selected_product

    # Prepare the data payload
    analysis_data = {
        "username": formatted_username,
        "product_name": product_name_to_save,
        "ai_role": ai_role,
        "scores": {
            "conversational": conversational,
            "specialization": specialization, # CHANGED: Renamed
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
            
        success_message = f"{current_lang_dict['success_message_prefix']} {file_path}"
        return success_message, current_lang_dict["success_message_suffix"]
        
    except Exception as e:
        error_message = f"{current_lang_dict['error_saving_data_prefix']} {e}"
        return "", f"{current_lang_dict['error_submit_data_prefix']} {e}"

# --- Language Update Function ---
def update_ui_text(lang_code):
    new_lang_dict = load_lang_file(lang_code)

    return (
        gr.update(value=f"<h1 style='display: inline;'>{new_lang_dict['app_title']}</h1>"),
        gr.update(label=new_lang_dict["username_label"], info=new_lang_dict["username_info"], placeholder=new_lang_dict["username_placeholder"]),
        gr.update(label=new_lang_dict["product_dropdown_label"], info=new_lang_dict["product_dropdown_info"]),
        gr.update(label=new_lang_dict["other_product_name_label"], placeholder=new_lang_dict["other_product_name_placeholder"]),
        gr.update(value=new_lang_dict["load_product_button"]),
        gr.update(label=new_lang_dict["product_info_label"]),
        gr.update(label=new_lang_dict["ai_role_label"], info=new_lang_dict["ai_role_info"], choices=[new_lang_dict["ai_role_feature"], new_lang_dict["ai_role_product"]]),
        gr.update(value=f"### {new_lang_dict['ux4ai_dimensions_title']}"),
        gr.update(label=new_lang_dict["conversational_label"]),
        gr.update(label=new_lang_dict["specialization_label"]), # CHANGED: Updated label
        gr.update(label=new_lang_dict["autonomy_label"]),
        gr.update(label=new_lang_dict["accessibility_label"]),
        gr.update(label=new_lang_dict["explainability_label"]),
        gr.update(value="---"),
        gr.update(value=new_lang_dict['risk_section_title_from_user']),
        gr.update(label=new_lang_dict["risk_level_label"], info=new_lang_dict["risk_level_info"]),
        gr.update(label=new_lang_dict["risk_description_label"], info=new_lang_dict["risk_description_info"]),
        gr.update(value="---"),
        gr.update(value=new_lang_dict['continuous_learning_section_title_from_user']),
        gr.update(label=new_lang_dict["continuous_learning_aspects_label"], info=new_lang_dict["continuous_learning_aspects_info"]),
        gr.update(label=new_lang_dict["analytics_type_label"], info=new_lang_dict["analytics_type_info"]),
        gr.update(label=new_lang_dict["analytics_explanation_label"], info=new_lang_dict["analytics_explanation_info"]),
        gr.update(value=new_lang_dict["submit_button"]),
        gr.update(label=new_lang_dict["spider_diagram_label"]),
        gr.update(label=new_lang_dict["data_submitted_label"]),
        gr.update(label=new_lang_dict["status_label"]),
        new_lang_dict
    )


# --- Gradio Interface ---
with gr.Blocks(title="UX4AI Workshop") as app:
    current_lang_state = gr.State(LANG)

    with gr.Row(variant="panel"):
        app_title_html = gr.HTML(f"<h1 style='display: inline;'>{LANG['app_title']}</h1>")
        
        with gr.Column(scale=0, min_width=100):
            with gr.Row():
                en_button = gr.Button("🇬🇧 EN", elem_id="en_lang_button", size="sm")
                de_button = gr.Button("🇩🇪 DE", elem_id="de_lang_button", size="sm")

    with gr.Row():
        with gr.Column():
            username_input = gr.Textbox(
                label=LANG["username_label"],
                info=LANG["username_info"],
                placeholder=LANG["username_placeholder"]
            )

            product_dropdown = gr.Dropdown(
                choices=list(PRODUCTS.keys()),
                label=LANG["product_dropdown_label"],
                info=LANG["product_dropdown_info"]
            )
            
            other_product_name_input = gr.Textbox(
                label=LANG["other_product_name_label"],
                placeholder=LANG["other_product_name_placeholder"],
                visible=False,
                interactive=True
            )

            load_product_btn = gr.Button(LANG["load_product_button"], visible=False)

            product_info_html = gr.HTML(label=LANG["product_info_label"])

            ai_role_radio = gr.Radio(
                [LANG["ai_role_feature"], LANG["ai_role_product"]],
                label=LANG["ai_role_label"],
                info=LANG["ai_role_info"]
            )

            ux4ai_dimensions_markdown = gr.Markdown(f"### {LANG['ux4ai_dimensions_title']}")
            # Sliders for UX4AI Spider Diagram
            conversational = gr.Slider(minimum=0.0, maximum=5.0, step=0.1, label=LANG["conversational_label"], value=2.5)
            specialization = gr.Slider(minimum=0.0, maximum=5.0, step=0.1, label=LANG["specialization_label"], value=2.5) # CHANGED: Renamed from personalization
            autonomy = gr.Slider(minimum=0.0, maximum=5.0, step=0.1, label=LANG["autonomy_label"], value=2.5)
            accessibility = gr.Slider(minimum=0.0, maximum=5.0, step=0.1, label=LANG["accessibility_label"], value=2.5)
            explainability = gr.Slider(minimum=0.0, maximum=5.0, step=0.1, label=LANG["explainability_label"], value=2.5)

            separator_1_markdown = gr.Markdown("---")
            risk_section_title_markdown = gr.Markdown(LANG['risk_section_title_from_user'])

            # Risk of Adversarial Attacks Section
            risk_level_slider = gr.Slider(
                minimum=0.0, maximum=5.0, step=0.1,
                label=LANG["risk_level_label"],
                info=LANG["risk_level_info"],
                value=2.5
            )
            risk_assessment_description = gr.Textbox(
                label=LANG["risk_description_label"],
                info=LANG["risk_description_info"],
                lines=3
            )

            separator_2_markdown = gr.Markdown("---")
            continuous_learning_section_title_markdown = gr.Markdown(LANG['continuous_learning_section_title_from_user'])

            # Continuous Learning & Feedback Loops Section
            continuous_learning_aspects = gr.Textbox(
                label=LANG["continuous_learning_aspects_label"],
                info=LANG["continuous_learning_aspects_info"],
                lines=5
            )
            continuous_learning_analytics_type_slider = gr.Slider(
                minimum=0.0, maximum=5.0, step=0.1,
                label=LANG["analytics_type_label"],
                info=LANG["analytics_type_info"],
                value=2.5
            )
            continuous_learning_explanation = gr.Textbox(
                label=LANG["analytics_explanation_label"],
                info=LANG["analytics_explanation_info"],
                lines=3
            )

            capture_data_btn = gr.Button(LANG["submit_button"])

        with gr.Column():
            plotly_chart_output = gr.Plot(label=LANG["spider_diagram_label"])
            json_output_display = gr.Textbox(label=LANG["data_submitted_label"], lines=1, interactive=False)
            status_message = gr.Textbox(label=LANG["status_label"], interactive=False)


    # --- Event Handling ---
    product_dropdown.change(
        fn=handle_product_selection,
        inputs=[product_dropdown],
        outputs=[other_product_name_input, load_product_btn]
    )

    load_product_btn.click(
        fn=update_product_info,
        inputs=[product_dropdown, current_lang_state],
        outputs=[
            product_info_html,
            conversational, specialization, autonomy, accessibility, explainability, # CHANGED: Renamed
            ai_role_radio,
            risk_level_slider,
            risk_assessment_description,
            continuous_learning_analytics_type_slider,
            continuous_learning_aspects,
            continuous_learning_explanation,
            load_product_btn
        ]
    )

    # CHANGED: Renamed 'personalization' to 'specialization' in the sliders list.
    sliders = [conversational, specialization, autonomy, accessibility, explainability]
    for slider in sliders:
        slider.change(
            fn=create_spider_diagram_plotly,
            inputs=sliders + [current_lang_state],
            outputs=plotly_chart_output
        )

    capture_data_btn.click(
        fn=capture_all_data,
        inputs=[
            username_input,
            product_dropdown,
            other_product_name_input,
            ai_role_radio,
            conversational, specialization, autonomy, accessibility, explainability, # CHANGED: Renamed
            risk_level_slider,
            risk_assessment_description,
            continuous_learning_analytics_type_slider,
            continuous_learning_aspects,
            continuous_learning_explanation,
            current_lang_state
        ],
        outputs=[json_output_display, status_message]
    )

    all_components_to_update = [
        app_title_html,
        username_input,
        product_dropdown,
        other_product_name_input,
        load_product_btn,
        product_info_html,
        ai_role_radio,
        ux4ai_dimensions_markdown,
        conversational,
        specialization, # CHANGED: Renamed
        autonomy,
        accessibility,
        explainability,
        separator_1_markdown,
        risk_section_title_markdown,
        risk_level_slider,
        risk_assessment_description,
        separator_2_markdown,
        continuous_learning_section_title_markdown,
        continuous_learning_aspects,
        continuous_learning_analytics_type_slider,
        continuous_learning_explanation,
        capture_data_btn,
        plotly_chart_output,
        json_output_display,
        status_message
    ]

    en_button.click(
        fn=lambda: update_ui_text("en"),
        outputs=all_components_to_update + [current_lang_state]
    )
    de_button.click(
        fn=lambda: update_ui_text("de"),
        outputs=all_components_to_update + [current_lang_state]
    )

# --- Launching the Gradio App ---
if __name__ == "__main__":
    app.launch(share=True)