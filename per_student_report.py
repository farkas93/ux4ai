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

# --- Language setup ---
LANG_DIR = "./lang"
DEFAULT_LANG = "de" # Default language for reports

def load_lang_file(lang_code):
    file_path = os.path.join(LANG_DIR, f"{lang_code}.json")
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Warning: Language file not found for '{lang_code}'. Falling back to default.")
        # Ensure we don't infinitely recurse if default lang file is also missing
        if lang_code == DEFAULT_LANG:
            raise FileNotFoundError(f"Default language file '{DEFAULT_LANG}.json' also not found.")
        return load_lang_file(DEFAULT_LANG)
    except json.JSONDecodeError:
        print(f"Error decoding JSON for '{lang_code}', falling back to default.")
        if lang_code == DEFAULT_LANG:
            raise json.JSONDecodeError(f"Default language file '{DEFAULT_LANG}.json' is malformed.", doc="", pos=0)
        return load_lang_file(DEFAULT_LANG)

# --- Directories ---
DATA_DIR = "./data"
SOLUTION_DIR = "./solutions"
REPORTS_DIR = "./reports" # New directory for generated reports

# Ensure reports directory exists
os.makedirs(REPORTS_DIR, exist_ok=True)

# --- Helper to load solution data ---
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
    # Extract just the main label part, removing descriptions in parentheses
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
            name=lang_dict["user_average_label"], # Use "Class Average" from en.json
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
            name=lang_dict["solution_label"], # Use "Lecturer" from en.json
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

        # Create a table for side-by-side comparison
        table = document.add_table(rows=1, cols=3)
        table.style = 'Table Grid'
        hdr_cells = table.rows[0].cells
        hdr_cells[0].text = lang_dict['question_column_header']
        hdr_cells[1].text = lang_dict['user_answer_column_header']
        hdr_cells[2].text = lang_dict['lecturer_answer_column_header']

        for lang_key, top_level_key, sub_key in comparison_fields:
            # Extract just the main label part, removing descriptions in parentheses
            question_text = lang_dict.get(lang_key, lang_key.replace('_label', '').replace('_', ' ').capitalize()).split('(')[0].strip()
            
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
        temp_image_path = f"temp_spider_diagram_{username_full.replace(' ', '_')}_{product_name.replace(' ', '_')}.png"
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
    # You can change 'en' to 'de' or any other language code you have
    report_language = "en" 
    current_lang_dict = load_lang_file(report_language)

    # Load all lecturer solutions once
    lecturer_solutions_by_product = {}
    for filename in os.listdir(SOLUTION_DIR):
        if filename.endswith(".json"):
            # Attempt to load the solution data and use its internal product_name if available
            # This handles cases where filename might not perfectly match the product_name in JSON
            temp_product_name = filename.replace(".json", "").replace("_", " ").title()
            solution_data = load_solution_data(temp_product_name)
            if solution_data and solution_data.get("product_name"):
                 lecturer_solutions_by_product[solution_data["product_name"]] = solution_data
            elif solution_data: # Fallback to filename if product_name isn't in JSON
                lecturer_solutions_by_product[temp_product_name] = solution_data

    # Group student data by username
    student_data_grouped = defaultdict(list)
    if os.path.exists(DATA_DIR):
        for user_dir in os.listdir(DATA_DIR):
            user_path = os.path.join(DATA_DIR, user_dir)
            if os.path.isdir(user_path):
                # We need the *formatted* username (e.g., JSmith) from the JSON for the folder structure
                # and potentially the *full* username (e.g., John Smith) for the report title.
                # The `username` key in the JSON is the formatted one from the form.
                
                user_formatted_name_from_folder = user_dir # e.g., "PMueller"
                full_username_for_report = user_dir # Default to folder name, will try to update from data

                for filename in os.listdir(user_path):
                    if filename.endswith(".json"):
                        file_path = os.path.join(user_path, filename)
                        student_data_grouped[user_formatted_name_from_folder].append(file_path)
                        
                        # Try to get the full username from the first file found for this student
                        # The 'username' key in the JSON is the *formatted* one like "JSmith"
                        # The user's prompt says "Enter your first and last name (e.g., 'Peter Mueller'). Will be formatted as 'PMueller'."
                        # So, the `username` field in the JSON is the *formatted* one.
                        # If you need "Peter Mueller" in the report title, you'd need to store it in the JSON
                        # or derive it (which is harder). For now, we use the formatted username from the JSON.
                        if full_username_for_report == user_dir: # Only update if not already set from a previous file
                            try:
                                with open(file_path, "r", encoding="utf-8") as f:
                                    data = json.load(f)
                                    if data.get("username"): 
                                        full_username_for_report = data["username"] 
                            except:
                                pass # Ignore errors if file is malformed

                # After processing all files for a user_dir, update the key to use the actual formatted username
                if student_data_grouped[user_formatted_name_from_folder]:
                    student_data_grouped[full_username_for_report] = student_data_grouped.pop(user_formatted_name_from_folder)


    for username, product_files in student_data_grouped.items():
        if product_files:
            generate_student_report(username, product_files, lecturer_solutions_by_product, current_lang_dict)