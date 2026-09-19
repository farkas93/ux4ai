# Export Schema

Project exports are JSON documents with `schema_version: "1.0"`.

The Summary & Export tab also generates a PDF report. The PDF includes the product setup, dimension radar (including a compatible comparator overlay), risk/evidence matrix, ranked backlog, questions, assumptions, and experiment plans.

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
- `experiments`
- `reflections`

Exports contain project-owned reasoning and comparator provenance. They exclude credentials, password hashes, server paths, raw baseline records, and historical student identities.

The `warning` field is required in both JSON and Markdown output:

> Prototype profiles represent intended or observed prototype behavior, not established production quality or business impact.

Consumers should treat unknown scores as missing values, not zeroes. Comparator snapshots contain frozen baseline medians, spread, sample count, and per-dimension compatibility flags.
