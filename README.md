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

For the authenticated server entry point, use:

```bash
uv run uvicorn aipm_toolkit.server:app --host 127.0.0.1 --port 7860
```

Open `http://127.0.0.1:7860/auth/login`. The server entry point protects `/app` with a database-backed HttpOnly session cookie and mounts the Gradio workspace there. `python -m aipm_toolkit.app` remains a development fallback for the standalone shell.

In the production-mounted workspace, callbacks prefer the authenticated request cookie over any client-side state value. The standalone Gradio fallback still supports its local development sign-in flow.

## PostgreSQL container

The intended local runtime uses PostgreSQL through Compose:

```bash
docker compose up --build
```

Open `http://127.0.0.1:7860/auth/login`. The app waits for PostgreSQL, applies Alembic migrations, and then starts Uvicorn. The Compose password is for local development only and must be replaced for any shared or deployed environment. Set `AIPM_COOKIE_SECURE=true` when serving through HTTPS.

To run the optional PostgreSQL smoke test against an existing database:

```bash
AIPM_TEST_DATABASE_URL='postgresql+psycopg://user:password@localhost:5432/aipm_test' uv run --extra test pytest -m postgres
```

## Browser E2E smoke test

Install the optional browser dependencies and Chromium once:

```bash
uv sync --extra e2e
uv run playwright install chromium
```

With the authenticated server running and `AIPM_E2E_PASSWORD` set in the environment, execute the browser smoke test:

```bash
export AIPM_E2E_PASSWORD
AIPM_E2E_URL='http://127.0.0.1:7860' \
AIPM_E2E_USERNAME='team-a' \
uv run --extra e2e pytest -m e2e
```

The ordinary test suite skips this test unless those environment variables are present.

Set `AIPM_DATABASE_URL` for PostgreSQL. The default SQLite URL is intended only for a quick local smoke test; integration and production use PostgreSQL.

The current implementation includes the Dimension Explorer and a historical baseline catalog. Import the legacy instructor references with:

```bash
uv run python -m aipm_toolkit.import_baselines solutions --publish
```

The importer preserves source records for instructor-only access, keeps valid zero scores, reports invalid values, and publishes only aggregate-ready reference data to teams. Teams can select one published comparator and save a purpose/scope snapshot from the Project Brief workspace. Historical comparators are classroom assessments, not rankings or current product ratings.

Legacy reference imports preserve per-dimension scale metadata. The historical autonomy scale is marked incompatible with the current autonomy definition, so its numeric difference is suppressed and its baseline radar point is shown as a gap.

The workspace also includes structured Notes and a Hypothesis Backlog. Notes can be linked to dimensions and used as provenance when creating supporting hypotheses. Hypothesis relationships are project-scoped; self-links and dependency cycles are rejected.

Saved notes and hypotheses can be reopened from the workspace, edited, and saved with revision checks. Stale edits are rejected instead of silently overwriting newer content.

The Hypothesis Backlog priority guidance now separates scored evidence-versus-impact entries from a `Needs assessment` list. Unknown values are never assigned arbitrary matrix coordinates.

Experiments can be planned against one primary hypothesis, updated with procedures, metrics, success criteria, guardrails, results, limitations, and decisions. Completing an experiment never automatically marks its hypothesis as supported. The workshop checklist requires a planned next experiment but remains guidance rather than a product-readiness score.

Saved experiments can be reopened from the experiment selector, edited, and saved again with their revision check intact.

Summary & Export provides authorized, versioned JSON and Markdown downloads. Exports include comparator provenance, notes, hypotheses, relationships, experiments, reflections, and the required prototype-profile warning; credentials, passwords, and historical identities are excluded.

Instructor accounts now have a course overview with per-project checklist progress and an instructor-only baseline import/publish panel. Team accounts cannot access either operation.

Instructors can also create course/team accounts from the instructor area. Passwords are Argon2-hashed immediately and are never included in project content or exports; the initial password should be shared through a separate secure channel.

The workspace also includes separate adversarial-risk and feedback-loop reflections. Risk scores are optional subjective discussion inputs; they are not mixed into the five dimension profile or presented as calibrated security assessments.

The team workspace now exposes the six workshop sections through an explicit section selector and numbered context headings. The integration suite exercises a representative create, reload, assess, hypothesize, experiment, and export journey.

English and German resource catalogs are validated at startup. The workspace language selector changes section context text while preserving stable internal keys and stored project content; remaining field labels will be migrated to the same catalog in the next localization pass.

Project Brief text and selection changes are tracked as dirty input and flushed through a two-second autosave timer. Failed or conflicting saves keep the dirty state and report the failure; the explicit Save brief action remains available.

Dimension assessments also round-trip server revisions and use the same dirty-state timer, so repeated saves update the loaded assessment rather than being treated as accidental stale writes.
