"""Generate A4 report concept pages; sample text only, no app changes."""

from html import escape
from pathlib import Path

ROOT = Path(__file__).parent
INK, MUTED, TEAL = "#192c39", "#627580", "#0b766c"


def text(x, y, value, size=14, color=INK, weight=400):
    return f'<text x="{x}" y="{y}" font-size="{size}" fill="{color}" font-weight="{weight}">{escape(value)}</text>'


def paragraph(x, y, values, size=14, color=INK, leading=23):
    return "".join(text(x, y + leading * i, value, size, color) for i, value in enumerate(values))


def box(x, y, width, height, fill="#f4f7f7", stroke="none"):
    return f'<rect x="{x}" y="{y}" width="{width}" height="{height}" rx="6" fill="{fill}" stroke="{stroke}"/>'


def rule(y):
    return f'<path d="M56 {y}H738" stroke="#dce4e6"/>'


def label(y, name):
    return text(56, y, name.upper(), 11, TEAL, 700)


def note(y, kind, content, link):
    return (box(56, y, 682, 86) + text(72, y + 24, kind.upper(), 10, TEAL, 700)
            + text(72, y + 48, content, 14) + text(72, y + 70, link, 11, MUTED))


def page(number, title, subtitle, content):
    svg = ('<svg xmlns="http://www.w3.org/2000/svg" width="794" height="1123" viewBox="0 0 794 1123" '
           'role="img" aria-labelledby="title desc">'
           f'<title id="title">{escape(title)} — report design</title>'
           '<desc id="desc">A4 portrait report concept, with illustrative student-authored content.</desc>'
           '<style>text {font-family: Arial, sans-serif;}</style><rect width="794" height="1123" fill="white"/>'
           + text(56, 43, "AI PRODUCT TOOLKIT", 10, TEAL, 700)
           + text(562, 43, "convincer.io · Team cais-26", 10, MUTED)
           + rule(59) + text(56, 111, title, 30, INK, 700)
           + text(56, 140, subtitle, 13, MUTED) + content
           + rule(1067) + text(56, 1091, "Learning report · Intended product behavior, not proven product quality", 10, MUTED)
           + text(705, 1091, f"{number:02d}", 11, TEAL, 700) + '</svg>')
    (ROOT / f"{number:02d}-{title.lower().replace(' & ', '-').replace(' ', '-')}.svg").write_text(svg, encoding="utf-8")


def overview():
    s = label(192, "01 / Product and value")
    s += text(56, 239, "convincer.io", 44, INK, 700)
    s += paragraph(56, 276, ["An AI-assisted job application tool that helps people tailor", "their CV to a specific role without losing their own voice."], 18, MUTED, 28)
    s += label(370, "Who we help")
    s += paragraph(56, 401, ["Job seekers who spend significant time adapting applications", "to increasingly specific job descriptions."], 15)
    s += label(480, "Job to be done")
    s += paragraph(56, 511, ["Present relevant experience clearly for a particular role while", "keeping the application accurate and recognizably personal."], 15)
    s += box(56, 589, 682, 176, "#eaf4f1")
    s += text(78, 620, "MAIN VALUE HYPOTHESIS", 11, TEAL, 700)
    s += paragraph(78, 657, ["If we help job seekers tailor their CV to a role,", "we expect less application effort and more interview invitations", "while maintaining factual accuracy and user control."], 17, INK, 29)
    s += label(819, "What this report contains")
    s += paragraph(56, 851, ["02–03  Product dimensions and the reasoning behind them", "04       AI Safety questions and assumptions", "05       Self-Improvement loop and capability explanations", "06–07  Hypothesis backlog, priorities, and next learning step"], 14, MUTED, 28)
    s += text(56, 1017, "Workshop snapshot · 9 October 2026 · Product type: AI-native", 11, MUTED)
    page(1, "Product learning report", "An argument about value and uncertainty — not an activity log.", s)


def profile():
    s = label(188, "02 / Assessment overview")
    s += box(56, 214, 682, 370, "#fafbfc", "#e4eaed")
    s += ('<g transform="translate(230,265)"><polygon points="166,0 312,106 257,278 75,278 20,106" fill="none" stroke="#d6e1e5"/>'
          '<polygon points="166,50 264,121 227,236 105,236 68,121" fill="none" stroke="#d6e1e5"/>'
          '<path d="M166 0V170L312 106M166 170L257 278M166 170L75 278M166 170L20 106" fill="none" stroke="#d6e1e5"/>'
          '<polygon points="166,95 294,115 220,251 127,220 84,140" fill="#0b766c" fill-opacity=".12" stroke="#0b766c" stroke-width="2"/>'
          + text(127, -18, "Specialization", 11, MUTED) + text(319, 110, "Conversational", 11, MUTED)
          + text(253, 302, "Accessibility", 11, MUTED) + text(-3, 302, "Autonomy", 11, MUTED)
          + text(-92, 111, "Explainability", 11, MUTED) + '</g>')
    s += text(78, 557, "● Intended profile", 12, TEAL) + text(275, 557, "Historical comparator: not selected", 12, MUTED)
    s += label(630, "Profile at a glance")
    dimensions = [("Conversational interaction", "1.5", "Mostly guided; short clarifications"),
                  ("Specialization", "4.5", "Focused on role-specific applications"),
                  ("Autonomy", "2.0", "User reviews every proposed change"),
                  ("Accessibility / audience breadth", "4.0", "Broad audience; usability assumptions remain"),
                  ("Explainability", "3.0", "Explain suggested edits, not internal reasoning")]
    for i, (name, score, meaning) in enumerate(dimensions):
        y = 679 + i * 65
        s += text(56, y, name, 14, INK, 600) + text(393, y, f"{score}/5", 14, TEAL, 700)
        s += text(56, y + 24, meaning, 13, MUTED) + rule(y + 39)
    s += text(56, 1030, "The next pages preserve the team's full reasoning and open questions.", 12, MUTED)
    page(2, "Product dimensions", "Scores summarize the intended experience; comments explain why.", s)


def reasoning():
    s = label(186, "03 / Assessment reasoning")
    s += text(56, 225, "Conversational interaction", 22, INK, 700) + text(651, 225, "1.5 / 5", 17, TEAL, 700)
    s += text(56, 256, "Guided 0 ↔ Open-ended 5", 12, MUTED)
    s += label(301, "Team's reasoning")
    s += paragraph(56, 336, ["The main experience is a guided comparison between a CV and a job", "description. AI does not need to lead an open-ended conversation.", "Short clarifying questions may help users explain relevant experience", "without making the process feel like an interview."], 15, INK, 25)
    s += note(458, "Question", "Will users understand why a clarification is being asked?", "Assessment · Conversational interaction → H1")
    s += note(558, "Assumption", "A short guided flow is less effort than an open-ended chat.", "Assessment · Conversational interaction → not yet formulated as a hypothesis")
    s += rule(686)
    s += text(56, 729, "Autonomy", 22, INK, 700) + text(651, 729, "2.0 / 5", 17, TEAL, 700)
    s += label(772, "Team's reasoning")
    s += paragraph(56, 807, ["The tool proposes changes but does not submit an application.", "Users should approve every edit and be able to restore the original.", "This keeps consequential decisions with the applicant."], 15, INK, 25)
    s += note(910, "Question", "Can applicants reliably spot inaccurate suggested changes?", "Assessment · Autonomy → H2")
    page(3, "Reasoning behind the profile", "Student comments and uncertainties, grouped by rubric.", s)


def safety():
    s = label(187, "04 / Safety exploration")
    s += paragraph(56, 223, ["Questions below describe uncertainties the team identified.", "They are not a safety rating or evidence that the risks are controlled."], 14, MUTED)
    s += text(56, 309, "Harms", 21, INK, 700)
    s += text(56, 337, "Plausible failures and the people affected", 12, MUTED)
    s += note(365, "Question", "Could a proposed edit invent experience the applicant does not have?", "AI Safety · Harms → H2")
    s += note(466, "Assumption", "Applicants will review suggested changes before using them.", "AI Safety · Harms → H2")
    s += text(56, 609, "Controls", 21, INK, 700)
    s += text(56, 637, "Permissions, data access, and safeguards", 12, MUTED)
    s += note(665, "Question", "Could retrieval expose another applicant's records?", "AI Safety · Controls → H3")
    s += text(56, 809, "Ownership", 21, INK, 700)
    s += note(837, "Question", "Who checks whether suggested edits remain accurate over time?", "AI Safety · Ownership → no supporting hypothesis yet")
    s += text(56, 981, "Scope · Evaluation · Response", 13, INK, 600)
    s += text(56, 1007, "No questions or assumptions recorded for these checkpoints.", 12, MUTED)
    page(4, "AI Safety", "Capture the team's concerns, rather than a numeric claim of safety.", s)


def improvement():
    s = label(187, "05 / One learning loop")
    s += box(56, 215, 682, 103, "#eaf4f1")
    s += paragraph(78, 251, ["Analyze rejected suggested edits and propose", "clearer clarification prompts for the next cycle."], 19, INK, 29)
    s += label(357, "What the team believes AI can contribute")
    capabilities = [("01", "Label or summarize operational evidence", "YES", ["AI summarizes rejected edits; the team reviews the summaries."]),
                    ("02", "Diagnose specific problems", "PARTLY", ["Repeated rejection reasons may be visible, but diagnosis is", "still a team interpretation rather than an established capability."]),
                    ("03", "Propose concrete changes", "YES", ["AI can draft alternative prompt wording for review."]),
                    ("04", "Evaluate candidates against a baseline", "UNKNOWN", ["The team has not yet defined a repeatable comparison."]),
                    ("05", "Apply and monitor changes over repeated cycles", "NO", ["Changes are applied manually; repeated monitoring is not defined."])]
    for i, (number, title, answer, comments) in enumerate(capabilities):
        y = 401 + i * 98
        s += text(56, y, number, 11, TEAL, 700) + text(89, y, title, 14, INK, 600)
        s += text(655, y, answer, 10, TEAL, 700) + paragraph(89, y + 24, comments, 13, MUTED, 20)
        s += rule(y + 76)
    s += note(914, "Question", "Do summaries reveal the real reason applicants reject edits?", "Self-Improvement → H4")
    s += text(56, 1030, "No automated-loop level or implementation score is included.", 12, MUTED)
    page(5, "Self-Improvement", "The loop, capability answers, explanations, and unresolved assumptions.", s)


def backlog():
    s = label(187, "06 / From uncertainty to hypothesis")
    s += text(56, 231, "H2 · Accuracy of suggested edits", 23, INK, 700)
    s += text(56, 260, "Sources: Assessment · Autonomy and AI Safety · Harms", 12, TEAL)
    s += label(312, "Question")
    s += paragraph(56, 347, ["Can applicants spot an inaccurate suggestion? Could a proposed", "edit invent experience the applicant does not have?"], 15)
    s += label(429, "Assumption")
    s += paragraph(56, 464, ["Applicants review each proposed change and can identify", "when it no longer represents their actual experience."], 15)
    s += box(56, 546, 682, 134, "#eaf4f1")
    s += text(78, 577, "SUPPORTING HYPOTHESIS", 11, TEAL, 700)
    s += paragraph(78, 613, ["If each suggested edit shows the original text and an explanation,", "applicants will identify inaccurate changes before using the CV."], 17, INK, 27)
    s += label(730, "Why this matters to the value hypothesis")
    s += paragraph(56, 765, ["Saving application time is valuable only if applicants retain control", "and avoid introducing inaccurate claims. This hypothesis explores", "the accuracy constraint in the main value hypothesis."], 15)
    s += rule(871)
    s += text(56, 908, "Other hypotheses in this snapshot", 16, INK, 600)
    s += paragraph(56, 947, ["H1 · Guided clarification reduces application effort", "H3 · Restricted retrieval prevents cross-applicant disclosure", "H4 · Rejected-edit summaries reveal useful prompt improvements"], 14, MUTED, 25)
    s += text(56, 1030, "Repeat this layout for each active hypothesis; retain all linked source notes.", 12, MUTED)
    page(6, "Hypothesis backlog", "Readable H-identifiers connect source notes, hypotheses, and priorities.", s)


def priorities():
    s = label(187, "07 / Choose what to learn next")
    s += '<path d="M106 505V243M106 505H688" fill="none" stroke="#9aaeb9"/>'
    s += box(107, 244, 280, 128, "#edf6f2") + text(126, 270, "HIGH RISK · LITTLE EVIDENCE", 10, TEAL, 700)
    for x, y, h in [(224, 285, "H2"), (340, 320, "H3"), (515, 425, "H1"), (456, 359, "H4")]:
        s += f'<circle cx="{x}" cy="{y}" r="6" fill="{TEAL}"/>' + text(x + 12, y + 4, h, 12, INK, 600)
    s += text(311, 541, "Evidence available →", 12, MUTED)
    s += text(56, 575, "Priority = risk if wrong + (10 − evidence). Equal scores are tied.", 12, MUTED)
    s += box(56, 617, 682, 151, "#f4f7f7")
    s += text(76, 646, "FIRST TO DISCUSS · H2", 11, TEAL, 700)
    s += text(76, 678, "Accuracy of suggested edits", 20, INK, 700)
    s += paragraph(76, 708, ["Priority 17/20 = risk 9 + uncertainty 8 (10 − evidence 2).", "High consequence if inaccurate edits are accepted; little evidence yet."], 14)
    s += label(817, "Next experiment — if recorded by the team")
    s += paragraph(56, 852, ["Prototype walkthrough with deliberately inaccurate suggestions.", "Metric: proportion of inaccurate edits participants identify.", "Success criterion: set by the team before running the test.", "If no experiment is saved, display: No next experiment recorded."], 14, INK, 26)
    s += text(56, 995, "A discussion priority is not a calibrated risk estimate or readiness score.", 12, MUTED)
    page(7, "Priorities & next test", "Matrix first, then identifiable hypotheses and an explanation of the order.", s)


if __name__ == "__main__":
    for render in [overview, profile, reasoning, safety, improvement, backlog, priorities]:
        render()
