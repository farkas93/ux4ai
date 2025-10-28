import gradio as gr
import plotly.graph_objects as go
import json
import os
from collections import defaultdict

# --- Language setup ---
LANG_DIR = "./lang"
DEFAULT_LANG = "en"

def load_lang_file(lang_code):
    file_path = os.path.join(LANG_DIR, f"{lang_code}.json")
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Warning: Language file not found for '{lang_code}'. Falling back to default.")
        return load_lang_file(DEFAULT_LANG)
    except json.JSONDecodeError:
        print(f"Error decoding JSON for '{lang_code}', falling back to default.")
        return load_lang_file(DEFAULT_LANG)

LANG = load_lang_file(DEFAULT_LANG)

DATA_DIR = "./data"
SOLUTION_DIR = "./solutions"

def load_and_process_data():
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

def create_spider_diagram_plotly(avg_scores, solution_scores=None, lang_dict=LANG):
    labels = ['conversational', 'specialization', 'autonomy', 'accessibility', 'explainability']
    theta = [lang_dict[label + "_label"].split('(')[0].strip() for label in labels]
    fig = go.Figure()

    # Create a closed loop for the spider chart by repeating the first value and label
    theta_closed = theta + [theta[0]]

    avg_values = [avg_scores.get(label.lower(), 0) for label in labels]
    avg_values.append(avg_values[0]) # Append the first value to the end to close the shape
    fig.add_trace(go.Scatterpolar(r=avg_values, theta=theta_closed, fill='toself', name=lang_dict["user_average_label"]))

    if solution_scores:
        solution_values = [solution_scores.get(label.lower(), 0) for label in labels]
        solution_values.append(solution_values[0]) # Append the first value to the end to close the shape
        # MODIFIED: Changed name to use 'lecturer_label' and updated line color for consistency
        fig.add_trace(go.Scatterpolar(r=solution_values, theta=theta_closed, fill='toself', name=lang_dict.get("lecturer_label", "Lecturer"), line=dict(color='green')))

    fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 5])), showlegend=True, height=350)
    return fig

def update_visualization(selected_product, show_solution, all_data, lang_dict):
    if not selected_product or not all_data:
        return None, lang_dict["select_product_prompt"]
    product_data = all_data.get(selected_product, {})
    if not product_data:
        return None, lang_dict["no_data_found_for"].format(product=selected_product)

    info_text = f"### {lang_dict['displaying_avg_scores_for'].format(product=selected_product)}\n"
    info_text += f"*{lang_dict['aggregated_from'].format(count=product_data['count'])}*\n\n"
    ai_roles = product_data.get('ai_role_counts', {})
    info_text += f"- {lang_dict['ai_is_feature_label']}: {ai_roles.get(lang_dict['ai_role_feature'], 0)}\n"
    info_text += f"- {lang_dict['ai_is_product_label']}: {ai_roles.get(lang_dict['ai_role_product'], 0)}\n"
    info_text += f"- {lang_dict['risk_label']}: {product_data.get('avg_risk_level', 0):.2f} / 5\n"
    info_text += f"- {lang_dict['analytics_label']}: {product_data.get('avg_analytics_level', 0):.2f} / 5\n"

    solution_data = None
    if show_solution:
        solution_data = load_solution_data(selected_product)
        if solution_data:
            info_text += "\n---\n### " + lang_dict["solution_details_label"] + "\n"
            info_text += f"{lang_dict['ai_role_label']}: {solution_data.get('ai_role', 'N/A')}\n"
            risk_info = solution_data.get('risk_of_adversarial_attacks', {})
            info_text += f"{lang_dict['risk_level_label']}: {risk_info.get('level', 'N/A')} / 5\n"
            learning_info = solution_data.get('continuous_learning_feedback_loops', {})
            info_text += f"{lang_dict['analytics_type_label']}: {learning_info.get('analytics_type_level', 'N/A')} / 5\n"
        else:
            info_text += "\n---\n*" + lang_dict["no_solution_file_found"] + "*"

    fig = create_spider_diagram_plotly(product_data.get('avg_scores', {}), solution_data.get('scores') if solution_data else None, lang_dict)
    return fig, info_text

def create_comparison_spider_diagram_plotly(product1, product2, show_solution, show_user_average, all_data, lang_dict):
    labels = ['conversational', 'specialization', 'autonomy', 'accessibility', 'explainability']
    theta = [lang_dict[label + "_label"].split('(')[0].strip() for label in labels]
    # MODIFIED: Create a closed loop for the spider chart by repeating the first label
    theta_closed = theta + [theta[0]]
    fig = go.Figure()

    def add_trace(product_name, avg_scores, solution_scores, avg_color, sol_color):
        if show_user_average and avg_scores:
            # MODIFIED: Append the first value to the end to close the shape
            r_avg = [avg_scores.get(lbl.lower(), 0) for lbl in labels] + [avg_scores.get(labels[0].lower(), 0)]
            fig.add_trace(go.Scatterpolar(r=r_avg,
                                          theta=theta_closed, fill='none', name=f"{product_name} ({lang_dict['user_average_label']})", line=dict(color=avg_color, width=3)))
        if show_solution and solution_scores:
            # MODIFIED: Append the first value to the end to close the shape
            r_sol = [solution_scores.get(lbl.lower(), 0) for lbl in labels] + [solution_scores.get(labels[0].lower(), 0)]
            # MODIFIED: Renamed to 'Lecturer', removed dashed line, and updated line style
            fig.add_trace(go.Scatterpolar(r=r_sol,
                                          theta=theta_closed, fill='none', name=f"{product_name}", line=dict(color=sol_color, width=2)))

    if product1:
        p1_data = all_data.get(product1, {})
        # FIX: Safely load solution data to prevent errors if the file doesn't exist
        solution_data_p1 = load_solution_data(product1)
        p1_sol = solution_data_p1.get('scores') if show_solution and solution_data_p1 else None
        # MODIFIED: Updated solution color to green for better visibility
        add_trace(product1, p1_data.get('avg_scores', {}), p1_sol, 'blue', 'green')

    if product2:
        p2_data = all_data.get(product2, {})
        # FIX: Safely load solution data
        solution_data_p2 = load_solution_data(product2)
        p2_sol = solution_data_p2.get('scores') if show_solution and solution_data_p2 else None
        # MODIFIED: Updated solution color to purple for better visibility
        add_trace(product2, p2_data.get('avg_scores', {}), p2_sol, 'red', 'purple')

    fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 5])), showlegend=True, height=600)
    return fig

def update_comparison_visualization(p1, p2, show_solution, show_user_average, all_data, lang_dict):
    fig = create_comparison_spider_diagram_plotly(p1, p2, show_solution, show_user_average, all_data, lang_dict)
    info_text = "### " + lang_dict["product_comparison_label"] + "\n"
    if p1: info_text += f"- {p1}\n"
    if p2: info_text += f"- {p2}\n"
    if show_user_average: info_text += f"- {lang_dict['showing_user_avg_label']}\n"
    if show_solution: info_text += f"- {lang_dict['showing_solution_label']}\n"
    return fig, info_text

def generate_overview_plots(all_data, lang_dict):
    figs = []
    for product_name, product_data in all_data.items():
        avg_scores = product_data.get('avg_scores', {})
        if avg_scores:
            fig = create_spider_diagram_plotly(avg_scores, None, lang_dict)
            fig.update_layout(title_text=f"{product_name} {lang_dict['ux4ai_analysis_label']}")
            figs.append((product_name, fig))
    return figs

def refresh_data(lang_dict):
    processed_data = load_and_process_data()
    product_list = sorted(list(processed_data.keys()))
    compare_plot = create_comparison_spider_diagram_plotly(None, None, False, True, processed_data, lang_dict)
    overview_figs = [fig for _, fig in generate_overview_plots(processed_data, lang_dict)]
    return (
        processed_data,
        gr.update(choices=product_list, value=None),
        *overview_figs,
        compare_plot,
        gr.update(choices=product_list),
        gr.update(choices=product_list)
    )

# FIXED: Button text updates use `value=` not `label=`
def update_dashboard_lang(lang_code):
    new_lang = load_lang_file(lang_code)
    return (
        gr.update(value=f"# {new_lang['dashboard_header']}"),  # Markdown header
        gr.update(value=new_lang["refresh_all_data"]),         # Button text
        gr.update(label=new_lang["select_product"]),
        gr.update(label=new_lang["show_solution_comparison"]),
        gr.update(value=new_lang["select_product_prompt"]),    # Markdown text
        gr.update(label=new_lang["averaged_spider_diagram"]),
        gr.update(value=new_lang["refresh_overview_data"]),    # Button text
        gr.update(label=new_lang["show_solution_comparison"]),
        gr.update(label=new_lang["show_user_averages"]),
        gr.update(value=new_lang["select_two_products_prompt"]),
        gr.update(label=new_lang["product_comparison_spider_diagram"]),
        new_lang
    )

# --- Build UI ---
with gr.Blocks(title=LANG["dashboard_title"], css=".gr-row {flex-wrap: nowrap;} .gr-column {flex: 1;} .gr-plot {height: 350px;}") as dashboard:
    initial_data = load_and_process_data()
    current_lang_state = gr.State(LANG)
    all_processed_data = gr.State(initial_data)

    dashboard_header_markdown = gr.Markdown(f"# {LANG['dashboard_header']}")

    with gr.Row():
        en_button = gr.Button("🇬🇧 EN", size="sm")
        de_button = gr.Button("🇩🇪 DE", size="sm")

    with gr.Tab(LANG["tab_by_product"]):
        with gr.Row():
            with gr.Column(scale=1):
                refresh_btn_global = gr.Button(LANG["refresh_all_data"])
                product_dropdown = gr.Dropdown(choices=sorted(list(initial_data.keys())), label=LANG["select_product"])
                show_solution_checkbox = gr.Checkbox(label=LANG["show_solution_comparison"], value=False)
                info_display = gr.Markdown(LANG["select_product_prompt"])
            with gr.Column(scale=3):
                plotly_chart_output = gr.Plot(label=LANG["averaged_spider_diagram"])

    with gr.Tab(LANG["tab_overview"]):
        refresh_btn_overview = gr.Button(LANG["refresh_overview_data"])
        overview_plot_outputs = []
        figs_init = generate_overview_plots(initial_data, LANG)
        with gr.Row():
            for col_idx in range(4):
                with gr.Column():
                    for row_idx in range(2):
                        idx = row_idx + col_idx * 2
                        if idx < len(figs_init):
                            name, fig = figs_init[idx]
                            p = gr.Plot(label=f"{name} {LANG['overview_label']}", value=fig)
                            overview_plot_outputs.append(p)

    with gr.Tab(LANG["tab_compare_products"]):
        gr.Markdown("## " + LANG["compare_two_products_label"])
        with gr.Row():
            with gr.Column(scale=1):
                product1_dropdown = gr.Dropdown(choices=sorted(list(initial_data.keys())), label=LANG["select_product1"])
                product2_dropdown = gr.Dropdown(choices=sorted(list(initial_data.keys())), label=LANG["select_product2"])
                show_solution_compare_checkbox = gr.Checkbox(label=LANG["show_solution_comparison"], value=False)
                show_user_average_compare_checkbox = gr.Checkbox(label=LANG["show_user_averages"], value=True)
                compare_info_display = gr.Markdown(LANG["select_two_products_prompt"])
            with gr.Column(scale=3):
                compare_plotly_chart_output = gr.Plot(label=LANG["product_comparison_spider_diagram"],
                                                      value=create_comparison_spider_diagram_plotly(None, None, False, True, initial_data, LANG))

    # Events
    product_dropdown.change(update_visualization, [product_dropdown, show_solution_checkbox, all_processed_data, current_lang_state], [plotly_chart_output, info_display])
    show_solution_checkbox.change(update_visualization, [product_dropdown, show_solution_checkbox, all_processed_data, current_lang_state], [plotly_chart_output, info_display])

    product1_dropdown.change(update_comparison_visualization,
                             [product1_dropdown, product2_dropdown, show_solution_compare_checkbox, show_user_average_compare_checkbox, all_processed_data, current_lang_state],
                             [compare_plotly_chart_output, compare_info_display])
    product2_dropdown.change(update_comparison_visualization,
                             [product1_dropdown, product2_dropdown, show_solution_compare_checkbox, show_user_average_compare_checkbox, all_processed_data, current_lang_state],
                             [compare_plotly_chart_output, compare_info_display])
    show_solution_compare_checkbox.change(update_comparison_visualization,
                                          [product1_dropdown, product2_dropdown, show_solution_compare_checkbox, show_user_average_compare_checkbox, all_processed_data, current_lang_state],
                                          [compare_plotly_chart_output, compare_info_display])
    show_user_average_compare_checkbox.change(update_comparison_visualization,
                                              [product1_dropdown, product2_dropdown, show_solution_compare_checkbox, show_user_average_compare_checkbox, all_processed_data, current_lang_state],
                                              [compare_plotly_chart_output, compare_info_display])

    refresh_btn_global.click(refresh_data, [current_lang_state], [all_processed_data, product_dropdown, *overview_plot_outputs, compare_plotly_chart_output, product1_dropdown, product2_dropdown])
    refresh_btn_overview.click(lambda lang: [fig for _, fig in generate_overview_plots(load_and_process_data(), lang)], [current_lang_state], overview_plot_outputs)

    # Language buttons
    dashboard_components_to_update = [
        dashboard_header_markdown,
        refresh_btn_global,
        product_dropdown,
        show_solution_checkbox,
        info_display,
        plotly_chart_output,
        refresh_btn_overview,
        show_solution_compare_checkbox,
        show_user_average_compare_checkbox,
        compare_info_display,
        compare_plotly_chart_output
    ]

    en_button.click(lambda: update_dashboard_lang("en"), outputs=dashboard_components_to_update + [current_lang_state])
    de_button.click(lambda: update_dashboard_lang("de"), outputs=dashboard_components_to_update + [current_lang_state])

if __name__ == "__main__":
    dashboard.launch(share=True)