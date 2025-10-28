import json
import os
from collections import defaultdict
from docx import Document
from docx.shared import Inches
from docx.enum.text import WD_PARAGRAPH_ALIGNMENT
import plotly.graph_objects as go
import plotly.io as pio

# Ensure Kaleido is available for image export
pio.kaleido.scope.default_format = "png"
pio.kaleido.scope.default_width = 700
pio.kaleido.scope.default_height = 400

# --- Language setup (copied from your existing script) ---
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
REPORTS_DIR = "./reports" # New directory for generated reports

# Ensure reports directory exists
os.makedirs(REPORTS_DIR, exist_ok=True)

# --- Helper to load solution data (from your existing script) ---
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

# --- Function to create spider diagram for the report ---
def create_report_spider_diagram(user_scores, solution_scores, lang_dict, product_name):
    labels = ['conversational', 'specialization', 'autonomy', 'accessibility', 'explainability']
    theta = [lang_dict[label + "_label"].split('(')[0].strip() for label in labels]
    theta_closed = theta + [theta[0]] # Close the loop

    fig = go.Figure()

    # User scores trace
    if user_scores:
        user_values = [user_scores.get(label.lower(), 0) for label in labels]
        user_values.append(user_values[0]) # Close the shape
        fig.add_trace(go.Scatterpolar(
            r=user_values,
            theta=theta_closed,
            fill='toself',
            name=lang_dict["user_answer_label"], # Use a specific label for the report
            line=dict(color='blue', width=3)
        ))

    # Solution scores trace
    if solution_scores:
        solution_values = [solution_scores.get(label.lower(), 0) for label in labels]
        solution_values.append(solution_values[0]) # Close the shape
        fig.add_trace(go.Scatterpolar(
            r=solution_values,
            theta=theta_closed,
            fill='toself',
            name=lang_dict.get("lecturer_label", "Lecturer's Answer"), # Use lecturer label
            line=dict(color='green', width=2)
        ))

    fig.update_layout(
        polar=dict(
            radialaxis=dict(visible=True, range=[0, 5])
        ),
        showlegend=True,
        title=f"{lang_dict['spider_diagram_label']} - {product_name}",
        height=400,
        margin=dict(l=50, r=50, t=70, b=50) # Adjust margins for better fit
    )
    return fig

# --- Function to generate a report for a single student ---
def generate_student_report(username_full, student_product_files, lecturer_solutions, lang_dict):
    document = Document()
    document.add_heading(f"{lang_dict['report_title']} - {username_full}", level=1)

    # Define the fields to compare and their corresponding labels/paths in the JSON
    comparison_fields = [
        ("ai_role_label", "ai_role", ""),
        ("conversational_label", "scores", "conversational"),
        ("specialization_label", "scores", "specialization"),
        ("autonomy_label", "scores", "autonomy"),
        ("accessibility_label", "scores", "accessibility"),
        ("explainability_label", "scores", "explainability"),
        ("risk_level_label", "risk_of_adversarial_attacks", "level"),
        ("risk_description_label", "risk_of_adversarial_attacks", "description"),
        ("continuous_learning_aspects_label", "continuous_learning_feedback_loops", "aspects"),
        ("analytics_type_label", "continuous_learning_feedback_loops", "analytics_type_level"),
        ("analytics_explanation_label", "continuous_learning_feedback_loops", "analytics_type_explanation"),
    ]

    for student_file_path in student_product_files:
        try:
            with open(student_file_path, "r", encoding="utf-8") as f:
                student_data = json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            print(f"Error reading student file {student_file_path}: {e}")
            continue

        product_name = student_data.get("product_name", "Unknown Product")
        lecturer_data = lecturer_solutions.get(product_name)

        document.add_heading(f"{lang_dict['product_label']}: {product_name}", level=2)

        # Add product description from the original PRODUCTS list if available
        # (Assuming PRODUCTS is available or can be loaded here)
        # For simplicity, I'm skipping reloading PRODUCTS here, but you could add it.
        # document.add_paragraph(f"Description: {PRODUCTS.get(product_name, {}).get('description', 'N/A')}")

        # Create a table for side-by-side comparison
        table = document.add_table(rows=1, cols=3)
        table.style = 'Table Grid'
        hdr_cells = table.rows[0].cells
        hdr_cells[0].text = lang_dict['question_column_header']
        hdr_cells[1].text = lang_dict['user_answer_column_header']
        hdr_cells[2].text = lang_dict['lecturer_answer_column_header']

        for lang_key, top_level_key, sub_key in comparison_fields:
            question_text = lang_dict.get(lang_key, lang_key.replace('_label', '').replace('_', ' ').capitalize())
            
            # Get student's answer
            student_ans = student_data.get(top_level_key)
            if sub_key:
                student_ans = student_ans.get(sub_key, "N/A") if isinstance(student_ans, dict) else "N/A"
            else:
                student_ans = student_ans if student_ans is not None else "N/A"

            # Get lecturer's answer
            lecturer_ans = lecturer_data.get(top_level_key) if lecturer_data else None
            if sub_key:
                lecturer_ans = lecturer_ans.get(sub_key, "N/A") if isinstance(lecturer_ans, dict) else "N/A"
            else:
                lecturer_ans = lecturer_ans if lecturer_ans is not None else "N/A"

            row_cells = table.add_row().cells
            row_cells[0].text = str(question_text)
            row_cells[1].text = str(student_ans)
            row_cells[2].text = str(lecturer_ans)

        document.add_paragraph() # Add a blank line after the table

        # Generate and embed spider diagram
        user_scores_for_plot = student_data.get('scores', {})
        solution_scores_for_plot = lecturer_data.get('scores', {}) if lecturer_data else {}

        fig = create_report_spider_diagram(user_scores_for_plot, solution_scores_for_plot, lang_dict, product_name)
        
        # Save plot to a temporary file and embed
        temp_image_path = f"temp_spider_diagram_{username_full}_{product_name.replace(' ', '_')}.png"
        fig.write_image(temp_image_path)
        
        document.add_picture(temp_image_path, width=Inches(6.5))
        os.remove(temp_image_path) # Clean up temporary file
        
        document.add_page_break()

    # Save the document
    safe_username = username_full.replace(" ", "_").replace("/", "_")
    report_filename = os.path.join(REPORTS_DIR, f"{safe_username}_UX4AI_Report.docx")
    document.save(report_filename)
    print(f"Report generated for {username_full}: {report_filename}")

# --- Main execution logic ---
if __name__ == "__main__":
    # Load all lecturer solutions once
    lecturer_solutions_by_product = {}
    for filename in os.listdir(SOLUTION_DIR):
        if filename.endswith(".json"):
            product_name_from_file = filename.replace(".json", "").replace("_", " ").title()
            # Special handling for "Google Search" if it's "google_search.json"
            if product_name_from_file == "Google Search":
                lecturer_solutions_by_product["Google Search"] = load_solution_data("Google Search")
            else:
                # Try to map to actual product names if they differ from filename
                # This assumes product names in your PRODUCTS dict are canonical
                # For now, just use the title-cased filename part
                solution_data = load_solution_data(product_name_from_file)
                if solution_data and solution_data.get("product_name"):
                     lecturer_solutions_by_product[solution_data["product_name"]] = solution_data
                elif solution_data:
                    lecturer_solutions_by_product[product_name_from_file] = solution_data

    # Group student data by username
    student_data_grouped = defaultdict(list)
    if os.path.exists(DATA_DIR):
        for user_dir in os.listdir(DATA_DIR):
            user_path = os.path.join(DATA_DIR, user_dir)
            if os.path.isdir(user_path):
                # The user_dir name is the formatted username (e.g., "JSmith")
                # We need the full username for the report title, which isn't directly in the folder name.
                # Assuming the first JSON file in the user's directory will contain the full username,
                # or we can derive it from the folder name (e.g., JSmith -> J. Smith or John Smith)
                # For simplicity, let's use the folder name as a unique identifier for now.
                # If you need full name, you'd need to parse it from one of their product JSONs.
                
                # Let's try to get the full username from the first file found for a student
                full_username_for_report = user_dir # Default to folder name
                
                for filename in os.listdir(user_path):
                    if filename.endswith(".json"):
                        file_path = os.path.join(user_path, filename)
                        student_data_grouped[user_dir].append(file_path)
                        # Attempt to get full username from the first file
                        if not full_username_for_report or full_username_for_report == user_dir:
                            try:
                                with open(file_path, "r", encoding="utf-8") as f:
                                    data = json.load(f)
                                    if data.get("username"): # This is the formatted username like JSmith
                                        # You might need a more robust way to get "John Smith" from "JSmith"
                                        # For now, we'll use the formatted one.
                                        full_username_for_report = data["username"]
                            except:
                                pass # Ignore errors if file is malformed

                # Store the full username with the list of files
                if student_data_grouped[user_dir]:
                    student_data_grouped[full_username_for_report] = student_data_grouped.pop(user_dir)

    for username, product_files in student_data_grouped.items():
        if product_files:
            generate_student_report(username, product_files, lecturer_solutions_by_product, LANG)