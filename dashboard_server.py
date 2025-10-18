import gradio as gr
import plotly.graph_objects as go
import numpy as np
import pandas as pd
import json
import os
from collections import defaultdict

DATA_DIR = "./data"
SOLUTION_DIR = "./solutions" # ADDED: Directory for solution files

def load_and_process_data():
    """
    Scans the data directory, aggregates all scores and stats for each product,
    and calculates the averages.
    """
    if not os.path.exists(DATA_DIR):
        print(f"Warning: Data directory '{DATA_DIR}' not found.")
        return {}

    # MODIFIED: Expanded defaultdict to hold all required aggregations
    aggregated_data = defaultdict(lambda: {
        "scores": defaultdict(float),
        "count": 0,
        "risk_level_sum": 0.0,
        "analytics_level_sum": 0.0,
        "ai_role_counts": defaultdict(int)
    })

    for root, _, files in os.walk(DATA_DIR):
        for filename in files:
            if filename.endswith(".json"):
                file_path = os.path.join(root, filename)
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        
                        product_name = data.get("product_name")
                        if not product_name:
                            continue

                        # Aggregate all data points
                        agg = aggregated_data[product_name]
                        agg["count"] += 1
                        
                        if data.get("scores"):
                            for key, value in data["scores"].items():
                                agg["scores"][key] += value
                        
                        if data.get("ai_role"):
                            agg["ai_role_counts"][data["ai_role"]] += 1

                        if data.get("risk_of_adversarial_attacks"):
                            agg["risk_level_sum"] += data["risk_of_adversarial_attacks"].get("level", 0.0)

                        if data.get("continuous_learning_feedback_loops"):
                            agg["analytics_level_sum"] += data["continuous_learning_feedback_loops"].get("analytics_type_level", 0.0)

                except (json.JSONDecodeError, IOError) as e:
                    print(f"Error reading or parsing {file_path}: {e}")

    # Calculate the final averages and prepare the output dictionary
    processed_data = {}
    for product, data in aggregated_data.items():
        count = data["count"]
        if count > 0:
            processed_data[product] = {
                "count": count,
                "avg_scores": {key: total / count for key, total in data["scores"].items()},
                "ai_role_counts": dict(data["ai_role_counts"]),
                "avg_risk_level": data["risk_level_sum"] / count,
                "avg_analytics_level": data["analytics_level_sum"] / count
            }
            
    return processed_data

def load_solution_data(product_name):
    """Loads the solution data for a specific product."""
    # Sanitize product name to create a safe filename
    # MODIFIED: Convert product_name to lowercase to match the file generation logic
    safe_filename = product_name.lower().replace(" ", "_").replace("/", "_") + ".json" 
    solution_path = os.path.join(SOLUTION_DIR, safe_filename)
    
    if os.path.exists(solution_path):
        try:
            with open(solution_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            print(f"Error reading solution file {solution_path}: {e}")
    return None

def create_spider_diagram_plotly(avg_scores, solution_scores=None):
    """
    MODIFIED: Generates a spider diagram and optionally adds a second trace for the solution.
    """
    labels = ['conversational', 'personalization', 'autonomy', 'accessibility', 'explainability']
    theta = [label.capitalize() for label in labels]
    
    fig = go.Figure()

    # Add trace for average user scores
    avg_values = [avg_scores.get(label.lower(), 0) for label in labels]
    fig.add_trace(go.Scatterpolar(
        r=avg_values,
        theta=theta,
        fill='toself',
        name='User Average'
    ))

    # ADDED: If solution scores are provided, add them as a new trace
    if solution_scores:
        solution_values = [solution_scores.get(label.lower(), 0) for label in labels]
        fig.add_trace(go.Scatterpolar(
            r=solution_values,
            theta=theta,
            fill='toself',
            name='Solution',
            line=dict(color='green')
        ))

    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 5])),
        showlegend=True,
        title="Average UX4AI Product Analysis",
        height=600
    )
    return fig

def update_visualization(selected_product, show_solution, all_data):
    """
    MODIFIED: Callback to update all visualizations based on product and solution toggle.
    """
    if not selected_product or not all_data:
        return None, "Select a product to view its averaged analysis."

    product_data = all_data.get(selected_product, {})
    if not product_data:
        return None, f"No data found for {selected_product}."

    # --- Build the Information Markdown ---
    count = product_data.get('count', 0)
    info_text = f"### Displaying average scores for **{selected_product}**\n"
    info_text += f"*Aggregated from **{count}** user submission(s).*\n\n---\n"
    
    # AI Role Stats
    ai_roles = product_data.get('ai_role_counts', {})
    info_text += "#### AI Role Breakdown:\n"
    info_text += f"- **AI is a Feature:** {ai_roles.get('AI is a Feature', 0)} submissions\n"
    info_text += f"- **AI is the Product:** {ai_roles.get('AI is the Product', 0)} submissions\n\n"

    # Average Slider Values
    info_text += "#### Average Slider Scores:\n"
    info_text += f"- **Risk of Adversarial Attacks:** {product_data.get('avg_risk_level', 0):.2f} / 5.0\n"
    info_text += f"- **Analytics Type:** {product_data.get('avg_analytics_level', 0):.2f} / 5.0\n"

    # --- Handle Solution Display ---
    solution_data = None
    if show_solution:
        solution_data = load_solution_data(selected_product)
        if solution_data:
            info_text += "\n---\n### Solution Details\n"
            info_text += f"**AI Role:** {solution_data.get('ai_role', 'N/A')}\n\n"
            risk_info = solution_data.get('risk_of_adversarial_attacks', {})
            info_text += f"**Risk Level:** {risk_info.get('level', 'N/A')} / 5.0\n"
            info_text += f"**Worst-case damage:** *{risk_info.get('description', 'N/A')}*\n\n"
            learning_info = solution_data.get('continuous_learning_feedback_loops', {})
            info_text += f"**Analytics Type:** {learning_info.get('analytics_type_level', 'N/A')} / 5.0\n"
            info_text += f"**Explanation:** *{learning_info.get('analytics_type_explanation', 'N/A')}*\n"
        else:
            info_text += "\n---\n*No solution file found for this product.*"

    # --- Generate the Spider Diagram ---
    solution_scores = solution_data.get('scores') if solution_data else None
    fig = create_spider_diagram_plotly(product_data.get('avg_scores', {}), solution_scores)
    
    return fig, info_text

def refresh_data():
    """Reloads all data from disk and updates the UI."""
    print("Refreshing data...")
    processed_data = load_and_process_data()
    product_list = sorted(list(processed_data.keys()))
    return processed_data, gr.update(choices=product_list, value=None)


# --- Main Application Setup ---
with gr.Blocks(title="UX4AI Dashboard") as dashboard:
    # Load data once when the app starts and store it in a State component
    initial_data = load_and_process_data()
    all_processed_data = gr.State(initial_data)
    
    gr.Markdown("# UX4AI Product Analysis - Dashboard")
    
    with gr.Row():
        with gr.Column(scale=1):
            refresh_btn = gr.Button("Refresh Data")
            product_dropdown = gr.Dropdown(
                choices=sorted(list(initial_data.keys())),
                label="Select a Product to Visualize"
            )
            show_solution_checkbox = gr.Checkbox(label="Show Solution Comparison", value=False)
            info_display = gr.Markdown("Select a product to begin.")
        
        with gr.Column(scale=3):
            plotly_chart_output = gr.Plot(label="Averaged UX4AI Spider Diagram")

    # --- Event Handling ---
    # When dropdown or checkbox changes, update the visualization
    product_dropdown.change(
        fn=update_visualization,
        inputs=[product_dropdown, show_solution_checkbox, all_processed_data],
        outputs=[plotly_chart_output, info_display]
    )
    show_solution_checkbox.change(
        fn=update_visualization,
        inputs=[product_dropdown, show_solution_checkbox, all_processed_data],
        outputs=[plotly_chart_output, info_display]
    )
    
    # When refresh button is clicked, reload data and update dropdown
    refresh_btn.click(
        fn=refresh_data,
        inputs=[],
        outputs=[all_processed_data, product_dropdown]
    )

if __name__ == "__main__":
    dashboard.launch(share=True)