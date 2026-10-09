"""Insight-focused learning reports, shared by Markdown and paginated PDF."""

from pathlib import Path

from fpdf import FPDF

from .dimensions import DEFAULT_DIMENSIONS
from .improvement_services import QUESTIONS
from .priority_rules import RANKING_RULE, priority_group_score
from .safety_services import CHECKPOINTS

INK = (25, 44, 57)
TEAL = (11, 118, 108)
MUTED = (98, 117, 128)


def report_sections(document):
    """Build content from recorded student work, without inventing conclusions."""
    project = document["project"]
    notes = [n for n in document["notes"] if not n["archived_at"]]
    hypotheses = [h for h in document["hypotheses"] if h["kind"] == "supporting" and not h["archived_at"]]
    identifiers = {h["id"]: f"H{i + 1}" for i, h in enumerate(hypotheses)}
    main = next((h for h in document["hypotheses"] if h["kind"] == "main" and not h["archived_at"]), {})
    sections = []

    def note_blocks(selected):
        result = []
        for note in selected:
            links = [identifiers[s["hypothesis_id"]] for s in document["hypothesis_sources"] if s["note_id"] == note["id"] and s["hypothesis_id"] in identifiers]
            result.append((note["note_type"].title(), note["text"]))
            if note.get("origin_section") == "safety":
                source = "AI Safety · " + (note.get("origin_key") or "").title()
            elif note.get("origin_section") == "self_improvement":
                source = "Self-Improvement"
            elif note["dimensions"]:
                source = "Assessment · " + ", ".join(d["title"] for d in DEFAULT_DIMENSIONS if d["key"] in note["dimensions"])
            else:
                source = "Backlog Creator"
            result.append(("Source", source))
            result.append(("Linked hypothesis", ", ".join(dict.fromkeys(links)) or "Not yet developed into a hypothesis"))
        return result or [("Questions and assumptions", "No questions or assumptions recorded.")]

    context = [("Product", project["product_name"]), ("Description", project["short_description"]),
               ("Target user", project["target_user"]), ("Job to be done", project["job_to_be_done"]),
               ("Current problem", project["current_problem"]), ("AI product type", project["product_type"]),
               ("Main value hypothesis", main.get("statement")), ("Prototype", project["figma_url"])]
    sections.append(("Product and value", context))
    profile = [("Interpretation", document["warning"])]
    estimates = {row["dimension_key"]: row for row in document["dimension_assessments"]}
    for definition in DEFAULT_DIMENSIONS:
        row = estimates.get(definition["key"], {})
        score = f"{row['score']}/5" if row.get("status") == "estimated" and row.get("score") is not None else row.get("status", "unassessed")
        profile.append((definition["title"], score))
    for snapshot in document["comparison_snapshots"][-1:]:
        dataset = snapshot["dataset"]
        profile.append(("Historical comparator", f"{snapshot['product']} · {dataset['cohort_label']} · {dataset['source_type']} · scale {dataset['scale_version']}"))
        profile.append(("Comparison purpose and scope", f"{snapshot['purpose']}: {snapshot['scope_explanation']}"))
        profile.append(("Provenance", dataset["provenance_notes"]))
        profile.append(("Compatibility", "Unknown or incompatible baseline dimensions are shown as gaps, not numeric comparisons."))
    if not document["comparison_snapshots"]:
        profile.append(("Historical comparator", "No comparator selected."))
    sections.append(("Product dimensions", profile))
    for definition in DEFAULT_DIMENSIONS:
        row = estimates.get(definition["key"], {})
        blocks = [("Rubric", f"{definition['low_anchor']} (0) — {definition['high_anchor']} (5)"),
                  ("Team's reasoning", row.get("rationale"))]
        for label, key in (("Assessment basis", "basis"), ("Evidence", "evidence"), ("Uncertainty", "uncertainty")):
            if row.get(key):
                blocks.append((label, row[key]))
        blocks += note_blocks([n for n in notes if definition["key"] in n["dimensions"]])
        sections.append((f"Assessment · {definition['title']}", blocks))
    safety = [("Safety exploration", "These are the team's questions and assumptions, not a rating of product safety.")]
    for key, (title, prompt) in CHECKPOINTS.items():
        safety.append((title, prompt))
        safety += note_blocks([n for n in notes if n["origin_section"] == "safety" and n["origin_key"] == key])
    sections.append(("AI Safety", safety))
    improvement = []
    loop = next(iter(document["improvement_loops"]), None)
    if loop:
        improvement.append(("Learning loop", loop["name"]))
        for key, question in list(QUESTIONS.items())[:5]:
            answer = loop["capabilities"].get(key, {})
            improvement.append((question, (answer.get("answer") or "unanswered").title()))
            improvement.append(("Team's explanation", answer.get("explanation")))
    else:
        improvement.append(("Learning loop", "No improvement loop recorded."))
    improvement += note_blocks([n for n in notes if n["origin_section"] == "self_improvement"])
    sections.append(("Self-Improvement", improvement))
    unassigned = [n for n in notes if not n["dimensions"] and n["origin_section"] not in {"safety", "self_improvement"}]
    if unassigned:
        sections.append(("Other questions and assumptions", note_blocks(unassigned)))
    for hypothesis in hypotheses:
        linked_ids = {s["note_id"] for s in document["hypothesis_sources"] if s["hypothesis_id"] == hypothesis["id"]}
        blocks = [("Supporting hypothesis", hypothesis["statement"])]
        blocks += note_blocks([n for n in notes if n["id"] in linked_ids])
        blocks += [("Value link", hypothesis["value_link"]), ("Expected trade-off", hypothesis["expected_tradeoff"])]
        if hypothesis["evidence_rationale"]:
            blocks.append(("Evidence rationale", hypothesis["evidence_rationale"]))
        relations = [f"{identifiers.get(r['from_hypothesis_id'], 'Main value hypothesis')} → {r['relation_type'].replace('_', ' ')} → {identifiers.get(r['to_hypothesis_id'], 'Main value hypothesis')}" for r in document["hypothesis_relationships"] if hypothesis["id"] in {r["from_hypothesis_id"], r["to_hypothesis_id"]} and all(endpoint in identifiers or endpoint == main.get("id") for endpoint in (r["from_hypothesis_id"], r["to_hypothesis_id"]))]
        if relations:
            blocks.append(("Relationships", "\n".join(relations)))
        sections.append((f"{identifiers[hypothesis['id']]} · Hypothesis backlog", blocks))
    priority = [("Test first", RANKING_RULE)]
    ranked = sorted(hypotheses, key=lambda h: tuple(-value for value in priority_group_score(float(h["priority_risk"]), float(h["priority_evidence"]))))
    last_score, position = None, 0
    for index, hypothesis in enumerate(ranked):
        risk, evidence = float(hypothesis["priority_risk"]), float(hypothesis["priority_evidence"])
        group_score = priority_group_score(risk, evidence)
        if group_score != last_score:
            position = index + 1
        last_score = group_score
        priority.append((f"Test order {position} · {identifiers[hypothesis['id']]}", hypothesis["statement"]))
        why = "High risk with limited evidence." if group_score[0] else "Outside the Test first area; consider after higher-risk uncertainties."
        priority.append(("Risk and evidence", f"{risk:g}/10 risk if wrong · {evidence:g}/10 evidence available. {why}"))
    if not ranked:
        priority.append(("Hypotheses", "No supporting hypotheses recorded."))
    sections.append(("Priorities and next test", priority))
    experiments = []
    for experiment in document["experiments"]:
        for key in ("title", "method", "status", "procedure", "participants", "comparison_baseline", "metric", "success_criterion", "guardrail", "resources", "owner", "planned_date", "results", "evidence_links", "limitations", "conclusion", "resulting_decision"):
            if experiment.get(key):
                experiments.append((key.replace("_", " ").title(), experiment[key]))
        experiments.append(("Primary hypothesis", identifiers.get(experiment["primary_hypothesis_id"], "Previously archived hypothesis / main value hypothesis")))
    sections.append(("Experiments", experiments or [("Next test", "No experiment recorded.")]))
    return sections


def markdown_report(document):
    lines = [f"# {document['project']['product_name']} · Product learning report", "", f"> {document['warning']}"]
    for title, blocks in report_sections(document):
        lines += ["", f"## {title}"]
        for label, value in blocks:
            lines += ["", f"### {label}", "", str(value or "Not recorded.")]
    return "\n".join(lines) + "\n"


class LearningPDF(FPDF):
    def __init__(self, product):
        super().__init__(format="A4")
        self.product = product
        self.topic = ""
        self.report_font = "Helvetica"
        self.set_margins(15, 24, 15)
        self.set_auto_page_break(True, margin=20)
        regular = Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")
        bold = regular.with_name("DejaVuSans-Bold.ttf")
        if regular.exists() and bold.exists():
            self.add_font("Report", fname=str(regular))
            self.add_font("Report", style="B", fname=str(bold))
            self.report_font = "Report"

    def clean(self, value):
        value = str(value or "Not recorded.")
        return value if self.report_font == "Report" else value.encode("latin-1", "replace").decode("latin-1")

    def header(self):
        self.set_font(self.report_font, "B", 8)
        self.set_text_color(*TEAL)
        self.set_xy(15, 10)
        self.cell(95, 5, "AI PRODUCT TOOLKIT")
        self.set_font(self.report_font, size=8)
        self.set_text_color(*MUTED)
        self.cell(85, 5, self.clean(self.product[:45]), align="R")
        self.set_draw_color(220, 228, 230)
        self.line(15, 18, 195, 18)
        self.set_y(26)
        if self.topic:
            self.set_font(self.report_font, size=8)
            self.cell(0, 5, self.clean(self.topic), new_x="LMARGIN", new_y="NEXT")

    def footer(self):
        self.set_y(-15)
        self.set_font(self.report_font, size=7)
        self.set_text_color(*MUTED)
        self.cell(165, 5, "Learning report: intended behavior, not established product quality")
        self.cell(15, 5, str(self.page_no()), align="R")

    def section(self, title, number):
        self.topic = title
        self.add_page()
        self.set_text_color(*TEAL)
        self.set_font(self.report_font, "B", 9)
        self.multi_cell(0, 6, f"{number:02d} / PRODUCT LEARNING", new_x="LMARGIN", new_y="NEXT")
        self.set_text_color(*INK)
        self.set_font(self.report_font, "B", 20)
        self.multi_cell(0, 10, self.clean(title), new_x="LMARGIN", new_y="NEXT")
        self.ln(5)

    def block(self, label, value):
        if self.get_y() > 245:
            self.add_page()
        self.set_font(self.report_font, "B", 9)
        self.set_text_color(*TEAL)
        self.multi_cell(0, 6, self.clean(label.upper()), new_x="LMARGIN", new_y="NEXT")
        self.set_font(self.report_font, size=10)
        self.set_text_color(*INK)
        self.set_fill_color(234, 244, 241)
        self.multi_cell(0, 6, self.clean(value), fill=label in {"Question", "Assumption", "Main value hypothesis", "Supporting hypothesis"}, new_x="LMARGIN", new_y="NEXT")
        self.ln(5)


def pdf_report(document, draw_radar, draw_matrix):
    pdf = LearningPDF(document["project"]["product_name"])
    for number, (title, blocks) in enumerate(report_sections(document), start=1):
        pdf.section(title, number)
        if title == "Product dimensions":
            y = pdf.get_y()
            draw_radar(pdf, document, 25, y, 155, pdf.report_font)
            pdf.set_y(y + 165)
            pdf.block("Chart legend", "Blue: intended product profile. Red: historical reference. Gaps indicate unknown or incompatible dimensions.")
        if title == "Priorities and next test":
            y = pdf.get_y() + 8
            pdf.set_font(pdf.report_font, "B", 9)
            pdf.set_text_color(*TEAL)
            pdf.set_xy(28, y)
            pdf.cell(155, 5, "TEST FIRST · High risk with limited evidence")
            y += 7
            draw_matrix(pdf, document, 28, y, 155, 95, pdf.report_font)
            pdf.set_y(y + 108)
        for label, value in blocks:
            pdf.block(label, value)
    return bytes(pdf.output())
