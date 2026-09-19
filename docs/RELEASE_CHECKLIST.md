# Release Checklist

## Automated in the repository

- [x] Unit and service tests pass
- [x] Revision conflicts are covered
- [x] Team authorization is covered
- [x] PDF, JSON, and Markdown export privacy is covered
- [x] Migration chain applies through the current head
- [x] Ruff checks pass
- [x] Authenticated route smoke tests pass
- [x] Playwright smoke test is collected when the E2E extra is installed
- [x] Backup and restore scripts pass shell syntax validation

## Required in CI or deployment environment

- [ ] Run `pytest -m postgres` against PostgreSQL
- [ ] Run `pytest -m e2e` after installing Chromium
- [ ] Build and start `docker compose up --build`
- [ ] Verify `/healthz` through the reverse proxy
- [ ] Verify `AIPM_COOKIE_SECURE=true` over HTTPS
- [ ] Run the 30-session save/navigation test
- [ ] Restart the application container and confirm committed data remains
- [ ] Execute and record a backup restore drill

## Classroom rehearsal

- [ ] Provision instructor and at least two team accounts
- [ ] Import and preview historical baselines
- [ ] Complete one team workflow in 50–60 minutes
- [ ] Confirm tablet and keyboard navigation
- [ ] Confirm German labels and help text for all visible controls
- [ ] Confirm export downloads and privacy contents
- [ ] Confirm support procedure and manual-deletion policy with the instructor
