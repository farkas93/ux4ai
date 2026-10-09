# Export Schema

Project exports are JSON documents with `schema_version: "1.0"`.

PDF and Markdown are learning reports: product context and value hypothesis,
dimension radar and full rubric reasoning, Safety questions/assumptions by
checkpoint, the first learning loop with all five capability explanations,
source-linked supporting hypotheses, priorities, and recorded experiments.
PDF uses A4 pages, consistent typography, tinted note/hypothesis blocks, headers,
page numbers and continuation pages for long comments. Project history and
archived notes/hypotheses are excluded from these current-work reports; archival
JSON retains them. Deferred numeric Safety and self-improvement ratings are not
presented in the reports.

The matrix highlights **Test first** at evidence 0–5 and risk 5–10, matching the
Plotly UI. H-identifiers follow active hypothesis creation order (with UUID as a
deterministic tie breaker), not rank. Priority arithmetic and equal-score ties
are explained. The report includes all active hypotheses, even beyond the UI's
current ten-slot prioritization limit.

Top-level fields:

- `schema_version`
- `warning`
- `project`
- `scale_definitions`
- `dimension_assessments`
- `comparison_snapshots`
- `notes`
- `hypotheses`
- `hypothesis_relationships`
- `hypothesis_sources` (links to source notes/comparator snapshots)
- `experiments`
- `reflections`
- `safety_assessment`
- `safety_hypothesis_links`
- `improvement_loops`
- `project_history` (archival JSON only)

Exports contain project-owned reasoning and comparator provenance. They exclude credentials, password hashes, server paths, raw baseline records, and historical student identities.

The `warning` field is required in both JSON and Markdown output:

> Prototype profiles represent intended or observed prototype behavior, not established production quality or business impact.

Consumers should treat unknown scores as missing values, not zeroes. Comparator snapshots contain frozen baseline medians, spread, sample count, and per-dimension compatibility flags.
