"""Render design-only SVG review boards. Does not import or modify the app."""

from html import escape
from pathlib import Path

OUT = Path(__file__).parent
INK = "#243449"
MUTED = "#69798c"
TEAL = "#0f766e"
NAV = ["Project Setup", "Assessment", "AI Safety", "Self-Improvement",
       "Backlog Creator", "Prioritization", "Summary & Export", "Project History"]


def rect(x, y, w, h, fill="white", stroke="#e0e7ef", radius=12):
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{radius}" fill="{fill}" stroke="{stroke}"/>'


def text(x, y, label, size=14, color=INK, weight=400):
    return f'<text x="{x}" y="{y}" font-size="{size}" fill="{color}" font-weight="{weight}">{escape(label)}</text>'


def lines(x, y, labels, size=14, color=MUTED, spacing=23):
    return "".join(text(x, y + i * spacing, label, size, color) for i, label in enumerate(labels))


def button(x, y, label, w=150, primary=True):
    return rect(x, y, w, 38, TEAL if primary else "#f8fafc", TEAL if primary else "#e0e7ef", 7) + text(x + 14, y + 24, label, 13, "white" if primary else INK, 600)


def field(x, y, w, label, value="", h=42):
    return text(x, y, label, 13, INK, 600) + rect(x, y + 12, w, h, "#f9fbfd", radius=7) + text(x + 12, y + 37, value, 13, MUTED)


def card(x, y, w, h, title, subtitle=None):
    result = rect(x, y, w, h) + text(x + 20, y + 32, title, 17, INK, 650)
    if subtitle:
        result += text(x + 20, y + 58, subtitle, 13, MUTED)
    return result


def radar(x, y, small=False):
    scale = .66 if small else 1
    return (f'<g transform="translate({x},{y}) scale({scale})">'
            '<polygon points="130,12 246,97 202,232 58,232 14,97" fill="#f5f8fb" stroke="#dce5ee"/>'
            '<polygon points="130,52 208,109 178,200 82,200 52,109" fill="none" stroke="#dce5ee"/>'
            '<path d="M130 12V134L246 97M130 134L202 232M130 134L58 232M130 134L14 97" fill="none" stroke="#dce5ee"/>'
            '<polygon points="130,64 210,108 160,205 86,190 63,112" fill="#0f766e" fill-opacity=".12" stroke="#0f766e" stroke-width="2"/>'
            + text(105, 0, "Focus", 11, MUTED) + text(213, 252, "Reach", 11, MUTED)
            + text(7, 252, "Agency", 11, MUTED) + '</g>')


def shell(title, subtitle, active):
    s = rect(24, 56, 1090, 874, "#f7f9fc", radius=16)
    s += rect(24, 56, 1090, 64, "white", radius=16)
    s += text(44, 96, "AI Product Toolkit", 18, INK, 700)
    s += rect(272, 73, 205, 32, "#f8fafc", radius=6) + text(284, 94, "convincer.io                 ▾", 13)
    s += text(498, 94, "+ Product", 13, TEAL, 600)
    s += text(936, 94, "EN ▾", 13) + text(995, 94, "cais-26 ▾", 13)
    s += text(46, 157, "WORKSPACE", 10, MUTED, 700)
    for i, label in enumerate(NAV):
        y = 187 + i * 43
        if i == active:
            s += rect(36, y - 23, 167, 35, "#e2f2ee", "#e2f2ee", 7)
        s += text(48, y, label, 13, TEAL if i == active else MUTED, 650 if i == active else 400)
    s += text(46, 595, "Learning tools", 11, MUTED)
    s += text(232, 164, title, 26, INK, 700) + text(232, 193, subtitle, 14, MUTED)
    s += text(970, 164, "● Saved", 12, TEAL)
    # Mobile shell: a single section selector, no full-width horizontal tab list.
    s += rect(1150, 56, 350, 874, "#f7f9fc", radius=20)
    s += text(1170, 92, "AI Product Toolkit", 17, INK, 700) + text(1460, 92, "☰", 19)
    s += rect(1170, 111, 310, 36, "white", radius=7) + text(1183, 134, "convincer.io                              ▾", 13)
    s += rect(1170, 157, 310, 36, "#e2f2ee", "#e2f2ee", 7) + text(1183, 180, title + "  ▾", 13, TEAL, 600)
    s += text(1170, 229, title, 23, INK, 700)
    s += text(1170, 254, "● Saved", 12, TEAL)
    return s


def note_composer(x, y, w, example, mobile=False):
    s = text(x, y, "Questions & assumptions", 14, INK, 650)
    s += rect(x, y + 15, w, 51, "#f2f7f6", "#dfebe8", 7)
    s += text(x + 12, y + 36, "QUESTION", 10, TEAL, 700)
    s += text(x + 12, y + 55, example, 12)
    s += rect(x, y + 79, w, 38, "#f9fbfd", radius=7) + text(x + 12, y + 103, "Question ▾  What needs exploring?", 12, MUTED)
    s += button(x, y + 128, "Add to backlog", 145)
    if not mobile:
        s += text(x + 162, y + 152, "Develop it in Backlog Creator →", 12, MUTED)
    return s


def setup():
    s = shell("Project Setup", "Start with who you help and the change you expect.", 0)
    s += card(232, 220, 425, 255, "1 · Product idea", "Keep it brief. You can refine it later.")
    s += field(252, 311, 385, "Short description", "Clarify support requests before routing.", 76)
    s += field(252, 426, 385, "AI product type", "Feature ▾")
    s += card(675, 220, 415, 255, "2 · User & problem")
    s += field(695, 285, 375, "Who is it for?", "Support teams")
    s += field(695, 367, 375, "Job to be done", "Understand the customer's real request.", 70)
    s += card(232, 495, 858, 268, "3 · Main value hypothesis", "What outcome should improve for this user?")
    s += lines(252, 590, ["If we help support teams clarify requests before routing,", "we expect fewer hand-offs while maintaining customer control."], 17, INK, 30)
    s += text(252, 709, "Prototype link (optional)   figma.com/…", 13, MUTED)
    s += button(232, 788, "Save product setup", 172)
    s += card(1170, 278, 310, 207, "1 · Product idea")
    s += field(1190, 339, 270, "Short description", "Clarify support requests", 58)
    s += field(1190, 433, 270, "AI product type", "Feature ▾")
    s += card(1170, 499, 310, 165, "2 · User & problem")
    s += field(1190, 559, 270, "Who is it for?", "Support teams")
    s += card(1170, 678, 310, 156, "3 · Value hypothesis")
    s += lines(1190, 745, ["If we help support teams clarify…", "we expect fewer hand-offs…"], 13, INK)
    s += button(1170, 857, "Save product setup", 310)
    return s


def assessment():
    s = shell("Assessment", "Explore the intended characteristics of your product.", 1)
    s += card(232, 220, 504, 440, "Conversational interaction", "Guided ↔ Open-ended")
    s += text(252, 316, "Intended characteristic", 13, INK, 600) + text(671, 316, "1.5 / 5", 13, TEAL)
    s += '<path d="M256 343H710" stroke="#dce5ee" stroke-width="6"/><path d="M256 343H392" stroke="#0f766e" stroke-width="6"/><circle cx="392" cy="343" r="8" fill="white" stroke="#0f766e"/>'
    s += field(252, 388, 464, "Reasoning", "Interaction is guided, with short clarifications.", 55)
    s += note_composer(252, 496, 464, "Will customers understand the clarification?")
    for i, label in enumerate(["Specialization", "Autonomy", "Accessibility", "Explainability"]):
        s += rect(232, 676 + i * 47, 504, 38) + text(250, 701 + i * 47, label, 13, INK, 600) + text(678, 701 + i * 47, "2.5 ▾", 12, MUTED)
    s += card(754, 220, 336, 375, "Product profile") + radar(790, 285)
    s += text(782, 567, "● Current product", 12, TEAL)
    s += card(754, 614, 336, 144, "Historical comparison", "Optional classroom reference")
    s += field(774, 702, 296, "Compare with", "Select a reference ▾")
    s += card(1170, 278, 310, 76, "Product profile & comparison  ▾")
    s += card(1170, 368, 310, 416, "Conversational interaction")
    s += text(1190, 426, "Guided ↔ Open-ended · 1.5 / 5", 12, MUTED)
    s += '<path d="M1194 453H1454" stroke="#dce5ee" stroke-width="6"/><circle cx="1272" cy="453" r="8" fill="white" stroke="#0f766e"/>'
    s += field(1190, 493, 270, "Reasoning", "Short guided clarifications", 47)
    s += note_composer(1190, 592, 270, "Do users understand the question?", True)
    s += rect(1170, 800, 310, 39) + text(1190, 825, "Specialization                         ▾", 13)
    s += button(1170, 857, "Save assessment", 310)
    return s


def safety():
    s = shell("AI Safety", "What could go wrong, and what do you need to explore?", 2)
    s += card(232, 220, 556, 365, "Harms", "Plausible failures and the people affected")
    s += lines(252, 315, ["Could someone receive the wrong information?", "Whose trust or privacy could be affected?"], 15, INK)
    s += note_composer(252, 389, 516, "Could retrieval expose another user's records?")
    for i, title in enumerate(["Scope", "Controls", "Evaluation", "Response", "Ownership"]):
        s += rect(232, 603 + i * 49, 556, 40) + text(252, 629 + i * 49, title, 14, INK, 600) + text(750, 629 + i * 49, "▾", 14)
    s += card(806, 220, 284, 212, "Your exploration")
    s += lines(826, 290, ["2 questions", "1 assumption", "", "Next: turn an uncertainty", "into a hypothesis in the backlog."], 13)
    s += card(1170, 278, 310, 368, "Harms", "Failures and affected people")
    s += lines(1190, 374, ["Could someone get wrong information?", "Whose trust could be affected?"], 12, INK)
    s += note_composer(1190, 443, 270, "Could retrieval expose records?", True)
    for i, label in enumerate(["Scope", "Controls", "Evaluation", "Response", "Ownership"]):
        s += rect(1170, 662 + i * 46, 310, 36) + text(1190, 686 + i * 46, label + "  ▾", 13)
    return s


def improvement():
    s = shell("Self-Improvement", "Imagine one way your product could learn from its use.", 3)
    s += card(232, 220, 858, 146, "Your learning loop")
    s += field(252, 283, 818, "Describe one concrete loop", "Review failed conversations and propose better clarification prompts.")
    s += card(232, 385, 504, 267, "Explore what AI contributes")
    s += text(252, 446, "Does AI summarize operational evidence?", 14, INK, 600)
    s += text(252, 482, "● Yes      ○ Partly      ○ No      ○ Unknown", 13, TEAL)
    s += field(252, 524, 464, "Explanation", "The team reviews AI summaries of failed chats.", 55)
    questions = ["Diagnose problems", "Propose changes", "Compare candidates", "Apply & monitor changes"]
    for i, label in enumerate(questions):
        s += rect(232, 668 + i * 45, 504, 36) + text(252, 691 + i * 45, label + "  ▾", 13)
    s += card(754, 385, 336, 267, "Questions & assumptions")
    s += note_composer(774, 455, 296, "Will summaries reveal repeat issues?", True)
    s += button(754, 680, "Save learning loop", 170)
    s += card(1170, 278, 310, 132, "Your learning loop")
    s += lines(1190, 344, ["Review failed chats and propose", "better clarification prompts."], 13, INK)
    s += card(1170, 424, 310, 200, "AI summarizes evidence?")
    s += text(1190, 484, "● Yes  ○ Partly  ○ No  ○ Unknown", 12, TEAL)
    s += field(1190, 532, 270, "Explanation", "We review summaries of failed chats.", 46)
    s += card(1170, 638, 310, 195, "Questions & assumptions")
    s += note_composer(1190, 688, 270, "Do summaries reveal repeat issues?", True)
    s += button(1170, 867, "Save learning loop", 310)
    return s


def backlog():
    s = shell("Backlog Creator", "Turn a question or assumption into something you can test.", 4)
    s += text(232, 239, "All sources ▾     All entries ▾", 13, MUTED) + button(934, 215, "+ Add entry", 156, False)
    s += card(232, 273, 858, 234, "Clarifying the request", "From Assessment · Conversational interaction")
    s += field(252, 366, 250, "Assumption", "Users understand the prompt", 66)
    s += field(518, 366, 250, "Question", "Do users know how to respond?", 66)
    s += field(784, 366, 286, "Hypothesis", "If we clarify, hand-offs decrease", 66)
    s += text(252, 475, "Product dimension: Conversational ▾", 12, MUTED)
    s += text(915, 475, "Remove", 12, MUTED) + button(986, 453, "Save", 84)
    s += card(232, 525, 858, 234, "Privacy of retrieved information", "From AI Safety · Harms")
    s += field(252, 618, 250, "Assumption", "", 66)
    s += field(518, 618, 250, "Question", "Could retrieval expose records?", 66)
    s += field(784, 618, 286, "Hypothesis", "Write a testable expectation…", 66)
    s += text(252, 727, "No product dimension assigned", 12, MUTED)
    s += text(915, 727, "Remove", 12, MUTED) + button(986, 705, "Save", 84)
    s += text(232, 802, "Removed entries remain in Project History.", 12, MUTED)
    s += card(1170, 278, 310, 90, "Privacy of retrieved information")
    s += text(1190, 340, "From AI Safety · Harms", 12, TEAL)
    s += card(1170, 382, 310, 416, "Develop this entry")
    s += field(1190, 444, 270, "Question", "Could retrieval expose records?", 58)
    s += field(1190, 545, 270, "Assumption", "Optional: what do you believe?", 58)
    s += field(1190, 646, 270, "Hypothesis", "If… then…", 58)
    s += text(1190, 763, "Remove", 12, MUTED) + button(1374, 741, "Save", 86)
    s += button(1170, 830, "+ Add entry", 310, False)
    return s


def priority():
    s = shell("Prioritization", "Which hypothesis is most important to test next?", 5)
    s += card(232, 220, 430, 280, "H1 · Clarifying the request", "If we clarify, hand-offs decrease.")
    s += text(252, 318, "Risk if wrong                       8 / 10", 14)
    s += '<path d="M256 347H635" stroke="#dce5ee" stroke-width="6"/><circle cx="559" cy="347" r="8" fill="white" stroke="#0f766e"/>'
    s += text(252, 393, "Evidence available                  2 / 10", 14)
    s += '<path d="M256 422H635" stroke="#dce5ee" stroke-width="6"/><circle cx="332" cy="422" r="8" fill="white" stroke="#0f766e"/>'
    s += text(252, 475, "Changes saved automatically", 12, MUTED)
    s += card(680, 220, 410, 380, "Risk & evidence")
    s += '<path d="M720 535V295M720 535H1045" stroke="#9caec1" fill="none"/>'
    s += rect(721, 297, 155, 120, "#e2f2ee", "none", 0)
    s += text(732, 321, "Test early", 12, TEAL, 600)
    s += '<circle cx="786" cy="344" r="8" fill="#0f766e"/>' + text(800, 348, "H1", 12)
    s += '<circle cx="945" cy="462" r="8" fill="#8ca3b8"/>' + text(959, 466, "H2", 12)
    s += text(830, 570, "Evidence available →", 12, MUTED)
    s += card(680, 618, 410, 185, "Suggested test order")
    s += lines(700, 687, ["1 · Clarifying the request", "2 · Privacy of retrieved information", "", "Use the ranking to discuss your next test."], 14)
    s += card(1170, 278, 310, 148, "Test order")
    s += lines(1190, 339, ["1 · Clarifying the request", "2 · Privacy of retrieved information"], 13, INK)
    s += card(1170, 440, 310, 224, "H1 · Clarifying the request")
    s += lines(1190, 510, ["Risk if wrong: 8 / 10", "Evidence available: 2 / 10", "", "Changes saved automatically"], 13)
    s += rect(1170, 680, 310, 55) + text(1190, 714, "View risk & evidence matrix  ▾", 13)
    return s


def summary():
    s = shell("Summary & Export", "Bring your idea and learning together.", 6)
    s += card(232, 220, 560, 305, "convincer.io", "Clarify support requests before routing.")
    s += text(252, 320, "Main value hypothesis", 14, INK, 650)
    s += lines(252, 354, ["If we clarify requests before routing,", "we expect fewer hand-offs while", "maintaining customer control."], 17, INK, 29)
    s += card(810, 220, 280, 305, "Workshop progress")
    s += lines(830, 292, ["✓ Product concept", "✓ Product dimensions", "✓ Questions & assumptions", "✓ Supporting hypotheses", "○ Discuss your next test"], 13, INK, 35)
    s += card(232, 545, 858, 151, "Take your work with you", "Export for discussion, presentation, or further work.")
    s += button(252, 636, "Download PDF", 170) + button(440, 636, "Markdown", 150, False) + button(608, 636, "JSON", 120, False)
    s += card(232, 715, 858, 127, "Open questions")
    s += lines(252, 779, ["Could retrieval expose another user's records?", "Will AI summaries reveal repeat issues?"], 14)
    s += card(1170, 278, 310, 249, "convincer.io", "Your main value hypothesis")
    s += lines(1190, 383, ["If we clarify before routing,", "we expect fewer hand-offs", "while maintaining customer control."], 14, INK, 25)
    s += card(1170, 543, 310, 136, "Workshop progress")
    s += lines(1190, 608, ["✓ Concept, dimensions, hypotheses", "○ Discuss your next test"], 12)
    s += button(1170, 703, "Download PDF", 310)
    s += button(1170, 753, "Markdown", 148, False) + button(1332, 753, "JSON", 148, False)
    return s


def history():
    s = shell("Project History", "See how your thinking has changed.", 7)
    s += text(232, 239, "All activity ▾", 13, MUTED) + button(960, 215, "Refresh", 130, False)
    events = [("Today · 10:42", "Rewrote a question as a hypothesis", "From AI Safety · Harms", "If retrieval is restricted, exposure decreases."),
              ("Today · 10:36", "Updated the value hypothesis", "Project Setup", "Changed the expected outcome and constraint."),
              ("Yesterday · 15:12", "Added a question", "Self-Improvement", "Will summaries reveal repeat issues?"),
              ("Yesterday · 15:04", "Removed a backlog entry", "Backlog Creator", "The original entry remains in history.")]
    for i, (stamp, title, source, detail) in enumerate(events):
        y = 272 + i * 139
        s += rect(232, y, 858, 121) + text(252, y + 28, stamp, 11, MUTED)
        s += text(252, y + 56, title, 16, INK, 600) + text(252, y + 80, source, 12, TEAL)
        s += text(252, y + 103, detail, 13, MUTED)
    for i, (_, title, source, _) in enumerate(events):
        y = 278 + i * 142
        s += card(1170, y, 310, 126, "Today" if i < 2 else "Yesterday")
        short = ["Question → hypothesis", "Value hypothesis updated", "Question added", "Backlog entry removed"][i]
        s += text(1190, y + 65, short, 14, INK, 600) + text(1190, y + 96, source, 12, TEAL)
    return s


def instructor():
    s = shell("Instructor", "Manage the workshop and team access.", -1)
    s += card(232, 220, 858, 219, "Course overview", "AIPM Workshop · 4 teams · 6 products")
    s += lines(252, 320, ["TEAM                 PRODUCT                         WORKSHOP PROGRESS", "cais-26              convincer.io                     5 of 7 steps", "team-b               Study companion                  3 of 7 steps"], 13, INK, 32)
    s += card(232, 459, 418, 208, "Public workshop link", "LAN access stays available")
    s += text(252, 550, "● Public link closed", 14, TEAL, 600)
    s += button(252, 595, "Open public link", 170)
    s += card(670, 459, 420, 208, "Create a team")
    s += field(690, 526, 190, "Team alias", "team-c") + field(898, 526, 172, "Initial password", "••••••••••••")
    s += button(690, 605, "Create account", 160)
    s += rect(232, 688, 858, 47) + text(252, 718, "Historical reference import                                          ▾", 14)
    s += rect(232, 750, 858, 47) + text(252, 780, "Product administration                                               ▾", 14)
    s += card(1170, 278, 310, 149, "Course overview")
    s += lines(1190, 343, ["4 teams · 6 products", "View team progress →"], 13)
    s += card(1170, 443, 310, 150, "Public workshop link")
    s += text(1190, 505, "● Public link closed", 13, TEAL)
    s += button(1190, 536, "Open public link", 270)
    s += card(1170, 610, 310, 188, "Create a team")
    s += field(1190, 674, 270, "Team alias", "team-c")
    s += button(1190, 738, "Create account", 270)
    return s


def login():
    s = rect(24, 56, 1090, 874, "#f7f9fc", radius=16)
    s += text(72, 114, "AI Product Toolkit", 20, INK, 700)
    s += text(72, 264, "AI PRODUCT MANAGEMENT · LEARNING WORKSPACE", 11, TEAL, 700)
    s += lines(72, 327, ["Find the value.", "Question the assumptions.", "Decide what to test."], 36, INK, 47)
    s += lines(72, 510, ["A student workspace to shape a value hypothesis", "and build a backlog of testable ideas."], 17, MUTED, 28)
    s += lines(72, 627, ["01  Define who you help and why it matters", "02  Explore dimensions, safety, and improvement", "03  Turn questions into hypotheses"], 14, INK, 40)
    s += card(649, 248, 401, 422, "Welcome to your workspace", "Use your course team or instructor account.")
    s += field(677, 358, 345, "Username", "Your team alias") + field(677, 451, 345, "Password", "••••••••••••")
    s += button(677, 537, "Sign in", 345)
    s += text(677, 623, "Need access? Ask your instructor.", 13, MUTED)
    s += rect(1150, 56, 350, 874, "#f7f9fc", radius=20)
    s += text(1170, 103, "AI Product Toolkit", 20, INK, 700)
    s += lines(1170, 183, ["Find value. Build your", "hypothesis backlog."], 26, INK, 34)
    s += lines(1170, 275, ["Explore questions and assumptions", "with your team, then decide what", "to test next."], 14, MUTED, 24)
    s += card(1170, 374, 310, 350, "Sign in")
    s += field(1190, 448, 270, "Username", "Your team alias") + field(1190, 544, 270, "Password", "••••••••••••")
    s += button(1190, 625, "Sign in", 270)
    s += text(1170, 768, "Need access? Ask your instructor.", 13, MUTED)
    return s


PAGES = {"01-login": login, "02-project-setup": setup, "03-assessment": assessment,
         "04-ai-safety": safety, "05-self-improvement": improvement, "06-backlog-creator": backlog,
         "07-prioritization": priority, "08-summary-export": summary,
         "09-project-history": history, "10-instructor": instructor}


if __name__ == "__main__":
    for name, render in PAGES.items():
        title = name[3:].replace("-", " ").title()
        svg = ('<svg xmlns="http://www.w3.org/2000/svg" width="1530" height="980" viewBox="0 0 1530 980" '
               'role="img" aria-labelledby="title desc">'
               f'<title id="title">{title}: desktop and mobile design proposal</title>'
               '<desc id="desc">Static review mockup, not a functioning interface. Desktop at left and mobile at right.</desc>'
               '<style>text {font-family: Arial, sans-serif;} </style>'
               + rect(0, 0, 1530, 980, "#ecf1f6", "none", 0)
               + text(24, 31, title.upper() + " · DESKTOP", 12, MUTED, 600)
               + text(1150, 31, "MOBILE · STACKED LAYOUT", 12, MUTED, 600)
               + render()
               + text(24, 961, "DRAFT 01 · Review layout and learning flow before implementation. Sample content only.", 11, MUTED)
               + '</svg>')
        (OUT / f"{name}.svg").write_text(svg, encoding="utf-8")
