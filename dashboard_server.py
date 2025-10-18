import gradio as gr
import plotly.graph_objects as go
import json
import os
from collections import defaultdict

DATA_DIR = "./data"
SOLUTION_DIR = "./solutions"


def load_and_process_data():
    """Scans the data directory, aggregates scores and stats for each product."""
    if not os.path.exists(DATA_DIR):
        print(f"Warning: Data directory '{DATA_DIR}' not found.")
        return {}

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
                    print(f"Error reading {file_path}: {e}")

    processed_data = {}
    for product, data in aggregated_data.items():
        count = data["count"]
        if count > 0:
            processed_data[product] = {
                "count": count,
                "avg_scores": {k: total / count for k, total in data["scores"].items()},
                "ai_role_counts": dict(data["ai_role_counts"]),
                "avg_risk_level": data["risk_level_sum"] / count,
                "avg_analytics_level": data["analytics_level_sum"] / count
            }
    return processed_data


def load_solution_data(product_name):
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
    labels = ['conversational', 'personalization', 'autonomy', 'accessibility', 'explainability']
    theta = [label.capitalize() for label in labels]
    fig = go.Figure()

    avg_values = [avg_scores.get(label.lower(), 0) for label in labels]
    fig.add_trace(go.Scatterpolar(r=avg_values, theta=theta, fill='toself', name='User Average'))

    if solution_scores:
        solution_values = [solution_scores.get(label.lower(), 0) for label in labels]
        fig.add_trace(go.Scatterpolar(r=solution_values, theta=theta, fill='toself', name='Solution', line=dict(color='green')))

    fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 5])), showlegend=True, height=350)
    return fig


def update_visualization(selected_product, show_solution, all_data):
    if not selected_product or not all_data:
        return None, "Select a product to view its averaged analysis."
    product_data = all_data.get(selected_product, {})
    if not product_data:
        return None, f"No data found for {selected_product}."

    info_text = f"### Displaying average scores for **{selected_product}**\n"
    info_text += f"*Aggregated from **{product_data['count']}** user submission(s).*\n\n"
    ai_roles = product_data.get('ai_role_counts', {})
    info_text += f"- **AI is a Feature:** {ai_roles.get('AI is a Feature', 0)} submissions\n"
    info_text += f"- **AI is the Product:** {ai_roles.get('AI is the Product', 0)} submissions\n"
    info_text += f"- **Risk:** {product_data.get('avg_risk_level', 0):.2f} / 5\n"
    info_text += f"- **Analytics:** {product_data.get('avg_analytics_level', 0):.2f} / 5\n"

    solution_data = None
    if show_solution:
        solution_data = load_solution_data(selected_product)
        if solution_data:
            info_text += "\n---\n### Solution Details\n"
            info_text += f"**AI Role:** {solution_data.get('ai_role', 'N/A')}\n"
            risk_info = solution_data.get('risk_of_adversarial_attacks', {})
            info_text += f"**Risk Level:** {risk_info.get('level', 'N/A')} / 5\n"
            learning_info = solution_data.get('continuous_learning_feedback_loops', {})
            info_text += f"**Analytics Type:** {learning_info.get('analytics_type_level', 'N/A')} / 5\n"
        else:
            info_text += "\n---\n*No solution file found.*"

    fig = create_spider_diagram_plotly(product_data.get('avg_scores', {}), solution_data.get('scores') if solution_data else None)
    return fig, info_text


def create_comparison_spider_diagram_plotly(product1, product2, show_solution, show_user_average, all_data):
    labels = ['conversational', 'personalization', 'autonomy', 'accessibility', 'explainability']
    theta = [label.capitalize() for label in labels]
    fig = go.Figure()

    def add_trace(product_name, avg_scores, solution_scores, avg_color, sol_color):
        if show_user_average and avg_scores:
            fig.add_trace(go.Scatterpolar(r=[avg_scores.get(lbl.lower(), 0) for lbl in labels],
                                          theta=theta, fill='none', name=f"{product_name} (User Avg)", line=dict(color=avg_color, width=3)))
        if show_solution and solution_scores:
            fig.add_trace(go.Scatterpolar(r=[solution_scores.get(lbl.lower(), 0) for lbl in labels],
                                          theta=theta, fill='none', name=f"{product_name} (Solution)", line=dict(color=sol_color, dash='dash', width=2)))

    if product1:
        p1_data = all_data.get(product1, {})
        p1_sol = load_solution_data(product1).get('scores') if show_solution else None
        add_trace(product1, p1_data.get('avg_scores', {}), p1_sol, 'blue', 'darkblue')

    if product2:
        p2_data = all_data.get(product2, {})
        p2_sol = load_solution_data(product2).get('scores') if show_solution else None
        add_trace(product2, p2_data.get('avg_scores', {}), p2_sol, 'red', 'darkred')

    fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 5])), showlegend=True, height=600)
    return fig


def update_comparison_visualization(p1, p2, show_solution, show_user_average, all_data):
    fig = create_comparison_spider_diagram_plotly(p1, p2, show_solution, show_user_average, all_data)
    info_text = "### Product Comparison\n"
    if p1: info_text += f"- {p1}\n"
    if p2: info_text += f"- {p2}\n"
    if show_user_average: info_text += "- Showing User Averages\n"
    if show_solution: info_text += "- Showing Solutions\n"
    return fig, info_text


def generate_overview_plots(all_data):
    figs = []
    for product_name, product_data in all_data.items():
        avg_scores = product_data.get('avg_scores', {})
        if avg_scores:
            fig = create_spider_diagram_plotly(avg_scores)
            fig.update_layout(title_text=f"{product_name} UX4AI Analysis")
            figs.append((product_name, fig))
    return figs


def refresh_data():
    processed_data = load_and_process_data()
    product_list = sorted(list(processed_data.keys()))
    compare_plot = create_comparison_spider_diagram_plotly(None, None, False, True, processed_data)
    overview_figs = [fig for _, fig in generate_overview_plots(processed_data)]

    return (
        processed_data,
        gr.update(choices=product_list, value=None),
        *overview_figs,
        compare_plot,
        gr.update(choices=product_list),
        gr.update(choices=product_list)
    )


with gr.Blocks(title="UX4AI Dashboard", css=".gr-row {flex-wrap: nowrap;} .gr-column {flex: 1;} .gr-plot {height: 350px;}") as dashboard:
    initial_data = load_and_process_data()
    all_processed_data = gr.State(initial_data)

    gr.Markdown("# UX4AI Product Analysis - Dashboard")

    # By Product Tab
    with gr.Tab("By Product"):
        with gr.Row():
            with gr.Column(scale=1):
                refresh_btn_global = gr.Button("Refresh All Data")
                product_dropdown = gr.Dropdown(choices=sorted(list(initial_data.keys())), label="Select Product")
                show_solution_checkbox = gr.Checkbox(label="Show Solution Comparison", value=False)
                info_display = gr.Markdown("Select a product to begin.")
            with gr.Column(scale=3):
                plotly_chart_output = gr.Plot(label="Averaged UX4AI Spider Diagram")

    # Overview Tab (4x2 grid, column-major)
    with gr.Tab("Overview"):
        refresh_btn_overview = gr.Button("Refresh Overview Data")
        overview_plot_outputs = []
        figs_init = generate_overview_plots(initial_data)

        with gr.Row():
            for col_idx in range(4):
                with gr.Column():
                    for row_idx in range(2):
                        idx = row_idx + col_idx * 2  # column-major fill
                        if idx < len(figs_init):
                            name, fig = figs_init[idx]
                            p = gr.Plot(label=f"{name} Overview", value=fig)
                            overview_plot_outputs.append(p)

    # Compare Products Tab
    with gr.Tab("Compare Products"):
        gr.Markdown("## Compare Two Products")
        with gr.Row():
            with gr.Column(scale=1):
                product1_dropdown = gr.Dropdown(choices=sorted(list(initial_data.keys())), label="Select Product 1")
                product2_dropdown = gr.Dropdown(choices=sorted(list(initial_data.keys())), label="Select Product 2")
                show_solution_compare_checkbox = gr.Checkbox(label="Show Solution Comparison", value=False)
                show_user_average_compare_checkbox = gr.Checkbox(label="Show User Averages", value=True)
                compare_info_display = gr.Markdown("Select two products to compare.")
            with gr.Column(scale=3):
                compare_plotly_chart_output = gr.Plot(label="Product Comparison Spider Diagram",
                                                      value=create_comparison_spider_diagram_plotly(None, None, False, True, initial_data))

    # Events
    product_dropdown.change(update_visualization, [product_dropdown, show_solution_checkbox, all_processed_data], [plotly_chart_output, info_display])
    show_solution_checkbox.change(update_visualization, [product_dropdown, show_solution_checkbox, all_processed_data], [plotly_chart_output, info_display])

    product1_dropdown.change(update_comparison_visualization,
                             [product1_dropdown, product2_dropdown, show_solution_compare_checkbox, show_user_average_compare_checkbox, all_processed_data],
                             [compare_plotly_chart_output, compare_info_display])
    product2_dropdown.change(update_comparison_visualization,
                             [product1_dropdown, product2_dropdown, show_solution_compare_checkbox, show_user_average_compare_checkbox, all_processed_data],
                             [compare_plotly_chart_output, compare_info_display])
    show_solution_compare_checkbox.change(update_comparison_visualization,
                                          [product1_dropdown, product2_dropdown, show_solution_compare_checkbox, show_user_average_compare_checkbox, all_processed_data],
                                          [compare_plotly_chart_output, compare_info_display])
    show_user_average_compare_checkbox.change(update_comparison_visualization,
                                              [product1_dropdown, product2_dropdown, show_solution_compare_checkbox, show_user_average_compare_checkbox, all_processed_data],
                                              [compare_plotly_chart_output, compare_info_display])

    refresh_btn_global.click(refresh_data, [], [all_processed_data, product_dropdown, *overview_plot_outputs, compare_plotly_chart_output, product1_dropdown, product2_dropdown])
    refresh_btn_overview.click(lambda: [fig for _, fig in generate_overview_plots(load_and_process_data())], [], overview_plot_outputs)

if __name__ == "__main__":
    dashboard.launch(share=True)