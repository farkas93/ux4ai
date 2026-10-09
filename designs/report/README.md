# Product learning report · Design proposal 01

Open `index.html` locally to review the seven SVG pages. These are A4 portrait design boards, not a replacement report generator. All text, values, charts, and H-links are illustrative sample content.

## Editorial direction

The report should communicate **what students believe, why they believe it, and what remains uncertain**. It should read as a coherent product argument rather than a dump of database fields.

1. **Product learning report** — product, target user, job/problem, full main value hypothesis and report contents.
2. **Product dimensions** — radar with readable labels and a compact overview of all five scores and their intended meaning.
3. **Reasoning behind the profile** — full assessment rationale plus current questions and assumptions, grouped under the relevant dimension. Repeat/continue for all five dimensions.
4. **AI Safety** — current questions/assumptions under all six checkpoint topics; explicitly state when a topic has no entries. Preserve links to the corresponding hypotheses.
5. **Self-Improvement** — the single learning-loop description, all five capability answers with their explanations, and the section's questions and assumptions.
6. **Hypothesis backlog** — H-identifiers, source questions, source assumptions, complete hypothesis statements and recorded value links. Continue for every active hypothesis.
7. **Priorities & next test** — matrix above the ranking, consistent H-identifiers, source context, risk/evidence values, arithmetic and ties, followed by the team's recorded next experiment.

**Project history is excluded.** It belongs in the app's history view and archival JSON export, not in the learning report. Archived backlog content is likewise excluded from the current report unless explicitly requested as an appendix later.

Safety coverage, implementation maturity and numeric self-improvement levels remain excluded, matching their deferral in the student interface.

## Content mapping / implementation requirements

| Report material | Current source |
| --- | --- |
| Product context and value hypothesis | `Project` and main `Hypothesis` |
| Five dimension scores and reasoning | `DimensionEstimate.score`, `.status`, `.rationale` |
| Assessment questions/assumptions | Active `Note` joined to `NoteDimension` |
| Safety discussion | Active `Note.origin_section == safety`, grouped by `origin_key` |
| Learning-loop description and explanations | First-created `ImprovementLoop`, five visible entries in `capabilities_json` |
| Loop questions/assumptions | Active `Note.origin_section == self_improvement` |
| Source → supporting hypothesis | `HypothesisSource` links (must be added to report export data; currently missing there) |
| Value link / experiment | Stored hypothesis fields and `Experiment` records |
| Comparator | Saved snapshot including cohort, source, scale version and compatibility |

No generated insight should be presented as a student-authored conclusion. Explanatory sentences in these boards are sample prose: a future renderer should print actual recorded comments or clearly marked derived explanations. Never invent an experiment, success criterion, note-to-hypothesis link or evidence claim.

H-numbers must use the same deterministic order as the UI, not ranking position. All active hypotheses should be included in the report even if the UI currently shows a limited number of priority slots. An unlinked question stays visible and is labeled as not yet developed into a hypothesis.

## Visual system and print behavior

- White A4 pages, restrained teal accents, generous but purposeful margins, consistent page headers/footers.
- Clear hierarchy: section number → topic → student's reasoning → question/assumption → hypothesis.
- Charts remain supporting visuals; explanatory text is the core content.
- Light tinted blocks distinguish questions/assumptions and hypothesis statements without heavy dashboard borders.
- Explicit small labels rather than UUIDs, raw keys, or log timestamps.
- Preserve full comments. Wrap text, expand blocks and create continuation pages instead of clipping or shrinking it to illegibility.
- Keep a topic heading with at least two lines of content; keep source notes near the corresponding hypothesis where possible.
- Each of the five dimension discussions and six Safety topics needs a deliberate empty state, not silent omission.
- These seven boards are representative templates, **not a fixed seven-page cap**. Real content determines the final number of pages.
- Charts in these SVGs illustrate layout only. The renderer must use actual scores/coordinates, proper axes, and compatible comparator data.

## Feedback requested

Review `03-reasoning-behind-the-profile.svg`, `04-ai-safety.svg`, and `05-self-improvement.svg` first: these address the missing reasoning. Then review the backlog and priority pages for traceability.

- Is this amount of detail right for a student hand-in?
- Do we keep the product overview as a standalone opening page or condense it?
- Should each hypothesis have its own page, or share a page when its content is short?
- Do the section headings, note blocks and page density feel polished enough?

`render.py` regenerates the static sample boards. No application export behavior has been changed by this design task.
