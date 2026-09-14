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

The current implementation includes the Dimension Explorer and a historical baseline catalog. Import the legacy instructor references with:

```bash
uv run python -m aipm_toolkit.import_baselines solutions --publish
```

The importer preserves source records for instructor-only access, keeps valid zero scores, reports invalid values, and publishes only aggregate-ready reference data to teams. Teams can select one published comparator and save a purpose/scope snapshot from the Project Brief workspace. Historical comparators are classroom assessments, not rankings or current product ratings.
