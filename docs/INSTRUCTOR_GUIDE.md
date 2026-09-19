# Instructor Guide

## Provision a course

1. Sign in with the instructor account.
2. Create team aliases and initial passwords in the instructor area.
3. Share each initial password through a separate secure channel.
4. Note that deletion is manual only: nothing is deleted automatically; see `docs/RETENTION.md`.

## Import historical baselines

Preview first:

```bash
uv run python -m aipm_toolkit.import_baselines solutions \
  --manifest examples/import_manifest.json --preview
```

Import and publish only after checking the report:

```bash
uv run python -m aipm_toolkit.import_baselines solutions \
  --manifest examples/import_manifest.json --publish
```

Published datasets are immutable. Corrections must be imported as a replacement version rather than changing an already published dataset.

## Monitor progress

The instructor overview shows each team alias, product name, and checklist progress. Project content remains team-owned; instructor access is for course overview and administration.

## Privacy

- Ask teams to use synthetic or non-sensitive material.
- Do not request personal names as team content.
- Do not place credentials in projects, notes, experiments, or exports.
- Historical source records containing identifiers remain instructor-only.
