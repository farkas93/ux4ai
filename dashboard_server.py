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

# ADDED: Function to create a spider diagram for comparing two products
def create_comparison_spider_diagram_plotly(product1_name, product2_name, show_solution, show_user_average, all_data):
    """
    Generates a spider diagram comparing two products, with optional solution and user average traces.
    """
    labels = ['conversational', 'personalization', 'autonomy', 'accessibility', 'explainability']
    theta = [label.capitalize() for label in labels]
    
    fig = go.Figure()

    # Define colors for better distinction
    color1_avg = 'blue'
    color1_sol = 'darkblue'
    color2_avg = 'red'
    color2_sol = 'darkred'

    # Process Product 1
    p1_data = all_data.get(product1_name, {})
    p1_avg_scores = p1_data.get('avg_scores', {})
    p1_solution_scores = load_solution_data(product1_name).get('scores') if show_solution and product1_name else None

    # Process Product 2
    p2_data = all_data.get(product2_name, {})
    p2_avg_scores = p2_data.get('avg_scores', {})
    p2_solution_scores = load_solution_data(product2_name).get('scores') if show_solution and product2_name else None

    # Add traces based on toggles
    if show_user_average:
        if product1_name and p1_avg_scores:
            p1_avg_values = [p1_avg_scores.get(label.lower(), 0) for label in labels]
            fig.add_trace(go.Scatterpolar(
                r=p1_avg_values,
                theta=theta,
                fill='none', # MODIFIED: Changed fill to 'none' for comparison clarity
                name=f'{product1_name} (User Avg)',
                line=dict(color=color1_avg, width=3)
            ))
        if product2_name and p2_avg_scores:
            p2_avg_values = [p2_avg_scores.get(label.lower(), 0) for label in labels]
            fig.add_trace(go.Scatterpolar(
                r=p2_avg_values,
                theta=theta,
                fill='none', # MODIFIED: Changed fill to 'none' for comparison clarity
                name=f'{product2_name} (User Avg)',
                line=dict(color=color2_avg, width=3)
            ))

    if show_solution:
        if product1_name and p1_solution_scores:
            p1_sol_values = [p1_solution_scores.get(label.lower(), 0) for label in labels]
            fig.add_trace(go.Scatterpolar(
                r=p1_sol_values,
                theta=theta,
                fill='none', # MODIFIED: Changed fill to 'none' for comparison clarity
                name=f'{product1_name} (Solution)',
                line=dict(color=color1_sol, dash='dash', width=2)
            ))
        if product2_name and p2_solution_scores:
            p2_sol_values = [p2_solution_scores.get(label.lower(), 0) for label in labels]
            fig.add_trace(go.Scatterpolar(
                r=p2_sol_values,
                theta=theta,
                fill='none', # MODIFIED: Changed fill to 'none' for comparison clarity
                name=f'{product2_name} (Solution)',
                line=dict(color=color2_sol, dash='dash', width=2)
            ))

    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 5])),
        showlegend=True,
        title="UX4AI Product Comparison",
        height=600
    )
    return fig

# ADDED: Callback to update the comparison visualization
def update_comparison_visualization(product1, product2, show_solution, show_user_average, all_data):
    """
    Callback to update the comparison spider diagram based on selected products and toggles.
    """
    if not product1 and not product2:
        return create_comparison_spider_diagram_plotly(None, None, show_solution, show_user_average, all_data), "Select at least one product to compare."
    
    # MODIFIED: Pass all required parameters to the plotting function
    fig = create_comparison_spider_diagram_plotly(product1, product2, show_solution, show_user_average, all_data)
    
    info_text = "### Product Comparison\n"
    if product1:
        info_text += f"- **Product 1:** {product1}\n"
    if product2:
        info_text += f"- **Product 2:** {product2}\n"
    if show_user_average:
        info_text += "- Showing User Averages\n"
    if show_solution:
        info_text += "- Showing Solution Comparisons\n"
    
    return fig, info_text


def generate_overview_html(all_data):
    """
    Generates an HTML string containing spider diagrams for all products.
    Ensures a visible message is returned even if no data or diagrams are generated.
    This version explicitly loads Plotly.js once and then embeds plots.
    """
    if not all_data:
        return "<h3 style='color: red;'>Error: No product data available to generate overview. Please ensure your 'data' directory exists and contains valid JSON files.</h3>"

    # ADDED: Start with a script tag to load Plotly.js once for the entire HTML content
    html_parts = [
        "<script src='https://cdn.plot.ly/plotly-latest.min.js'></script>"
    ]
    
    plot_counter = 0
    for product_name, product_data in all_data.items():
        avg_scores = product_data.get('avg_scores', {})
        if avg_scores:
            fig = create_spider_diagram_plotly(avg_scores)
            fig.update_layout(title_text=f"**{product_name}** UX4AI Product Analysis", title_x=0.5) 
            
            # MODIFIED: Generate only the plot div and data, assuming Plotly.js is already loaded.
            # Set include_plotlyjs=False because we already loaded it once.
            # Set full_html=False to get just the div and script for the plot.
            plot_html = fig.to_html(full_html=False, include_plotlyjs=False)
            html_parts.append(plot_html)
            plot_counter += 1
        else:
            html_parts.append(f"<p style='color: orange;'>Warning: Could not generate spider diagram for **{product_name}**: No average scores found.</p>")
    
    if plot_counter == 0:
        return "<h3 style='color: red;'>Error: No spider diagrams could be generated from the available data. Check individual product data for 'avg_scores'.</h3>"
        
    # Join all individual plot HTMLs with a horizontal rule for separation
    return "<hr>".join(html_parts)

# MODIFIED: refresh_data function now returns the overview HTML as well, and an initial comparison plot
def refresh_data():
    """Reloads all data from disk and updates the UI for both tabs."""
    print("Refreshing data...")
    processed_data = load_and_process_data()
    product_list = sorted(list(processed_data.keys()))
    
    # Generate overview HTML with the refreshed data
    overview_html = generate_overview_html(processed_data) 
    
    # Generate an initial empty comparison plot for the compare tab
    initial_compare_plot = create_comparison_spider_diagram_plotly(None, None, False, True, processed_data)
    
    # MODIFIED: Added overview_html and initial_compare_plot to return values
    return processed_data, gr.update(choices=product_list, value=None), overview_html, initial_compare_plot


# --- Main Application Setup ---
with gr.Blocks(title="UX4AI Dashboard") as dashboard:
    # Load data once when the app starts and store it in a State component
    initial_data = load_and_process_data()
    all_processed_data = gr.State(initial_data)
    
    gr.Markdown("# UX4AI Product Analysis - Dashboard")
    
    with gr.Tab("By Product"): 
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

        # --- Event Handling for "By Product" Tab ---
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
    
    # ADDED: New Tab for overview of all products
    with gr.Tab("Overview"): 
        gr.Markdown("## Overview of All Product Analyses")
        # Initial generation of overview HTML, now with improved error handling
        initial_overview_html = generate_overview_html(initial_data)
        overview_html_output = gr.HTML(value=initial_overview_html)
        
    # ADDED: New Tab for comparing two products
    with gr.Tab("Compare Products"):
        gr.Markdown("## Compare Two Products")
        with gr.Row():
            with gr.Column(scale=1):
                product1_dropdown = gr.Dropdown(
                    choices=sorted(list(initial_data.keys())),
                    label="Select Product 1"
                )
                product2_dropdown = gr.Dropdown(
                    choices=sorted(list(initial_data.keys())),
                    label="Select Product 2"
                )
                # ADDED: Toggles for comparison tab
                show_solution_compare_checkbox = gr.Checkbox(label="Show Solution Comparison", value=False)
                show_user_average_compare_checkbox = gr.Checkbox(label="Show User Averages", value=True)
                compare_info_display = gr.Markdown("Select two products to compare.")
            
            with gr.Column(scale=3):
                # ADDED: Output for comparison plot
                initial_compare_plot = create_comparison_spider_diagram_plotly(None, None, False, True, initial_data)
                compare_plotly_chart_output = gr.Plot(label="Product Comparison Spider Diagram", value=initial_compare_plot)

        # ADDED: Event handling for the Compare Products tab
        product1_dropdown.change(
            fn=update_comparison_visualization,
            inputs=[product1_dropdown, product2_dropdown, show_solution_compare_checkbox, show_user_average_compare_checkbox, all_processed_data],
            outputs=[compare_plotly_chart_output, compare_info_display]
        )
        product2_dropdown.change(
            fn=update_comparison_visualization,
            inputs=[product1_dropdown, product2_dropdown, show_solution_compare_checkbox, show_user_average_compare_checkbox, all_processed_data],
            outputs=[compare_plotly_chart_output, compare_info_display]
        )
        show_solution_compare_checkbox.change(
            fn=update_comparison_visualization,
            inputs=[product1_dropdown, product2_dropdown, show_solution_compare_checkbox, show_user_average_compare_checkbox, all_processed_data],
            outputs=[compare_plotly_chart_output, compare_info_display]
        )
        show_user_average_compare_checkbox.change(
            fn=update_comparison_visualization,
            inputs=[product1_dropdown, product2_dropdown, show_solution_compare_checkbox, show_user_average_compare_checkbox, all_processed_data],
            outputs=[compare_plotly_chart_output, compare_info_display]
        )
        
    # --- Global Event Handling (e.g., for refresh button) ---
    # MODIFIED: When refresh button is clicked, reload data and update dropdowns, overview HTML, and comparison plot
    refresh_btn.click(
        fn=refresh_data,
        inputs=[],
        outputs=[all_processed_data, product_dropdown, overview_html_output, compare_plotly_chart_output] 
    )

if __name__ == "__main__":
    dashboard.launch(share=True)