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

Phase 1 currently provides the normalized foundation, authentication services, optimistic revision checks, and a minimal role-gated shell. The cookie-setting FastAPI adapter and workshop sections are added in subsequent phases.
