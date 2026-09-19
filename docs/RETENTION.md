# Retention and Deletion

Course retention settings are instructor-controlled and stored with the course. The default is 180 days; deployments should confirm the policy before the workshop begins.

Project deletion is instructor-only and requires explicit confirmation. Deletion removes the project brief and associated editable content, including notes, hypotheses, relationships, assessments, experiments, reflections, and comparison snapshots.

Before deletion:

1. Generate the JSON and Markdown exports if the submission must be retained.
2. Confirm the project UUID and course with the instructor.
3. Confirm the backup schedule and restore point.
4. Use the instructor deletion control with explicit confirmation.

Database backups follow the procedures in `README.md` and `ops/backup_postgres.sh`. Deletion and retention actions should be recorded in deployment operations logs without logging project content or credentials.
