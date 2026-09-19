# Deployment Guide

## Runtime

Use PostgreSQL as the persistent database and run the authenticated FastAPI entry point:

```bash
export AIPM_DATABASE_URL='postgresql+psycopg://user:password@host:5432/aipm'
export AIPM_COOKIE_SECURE=true
uv run uvicorn aipm_toolkit.server:app --host 0.0.0.0 --port 7860
```

In production, terminate HTTPS at a reverse proxy and forward requests to the application container. Do not expose the application directly to the public Internet without HTTPS.

## First setup

1. Apply migrations with `uv run alembic upgrade head`.
2. Create the first instructor account with the seed command or a controlled provisioning job.
3. Sign in at `/auth/login`.
4. Create the course and team accounts from the instructor area.
5. Import and preview baseline data before publication.
6. Run the browser smoke test against the deployed URL.

## Health and restart

- Health endpoint: `/healthz`
- Startup command: `python -m aipm_toolkit.start`
- Startup applies migrations before Uvicorn starts.
- PostgreSQL data is independent of the application container lifecycle.

## Release checks

- Confirm `AIPM_COOKIE_SECURE=true` behind HTTPS.
- Confirm secrets are deployment-provided, not committed.
- Run PostgreSQL integration tests.
- Run Playwright Chromium tests.
- Confirm backups and a restore drill.
- Confirm course retention policy with the instructor.
