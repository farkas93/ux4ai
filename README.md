# AIPM Toolkit

The new application lives in `aipm_toolkit/`; the original workshop scripts remain available for legacy-data reference.

## Phase 1 setup

```bash
uv sync --extra test
uv run alembic upgrade head
uv run python -m aipm_toolkit.seed instructor change-this-password --role instructor
uv run python -m aipm_toolkit.seed team-a change-this-team-password --role team --team-alias team-a
uv run python -m aipm_toolkit.app
```

Set `AIPM_DATABASE_URL` for PostgreSQL. The default SQLite URL is intended only for a quick local smoke test; integration and production use PostgreSQL.

Phase 3 adds the Dimension Explorer with versioned definitions for the five required dimensions, explicit `Unassessed`/`Estimated`/`Unknown` states, 0.1-step scores, rationales, evidence, uncertainty, and revision protection. Historical comparators and radar/table comparison are intentionally next; no baseline values are invented in this phase.
