# Data Lifecycle: Retention and Deletion

There is **no automatic deletion and no retention policy** in this application. Nothing is removed on a schedule; no job consumes any retention setting.

Deletion is always manual and explicit:

- **Team members** can delete their own product in the Summary & Export tab ("Danger zone"), with an explicit confirmation checkbox. Deletion removes the product and all of its editable content.
- **Instructors** can delete any product from the instructor area with the same explicit confirmation.

Deletion removes the product setup and associated content, including notes, hypotheses, relationships, assessments, experiments, reflections, and comparison snapshots. It cannot be undone from the application.

Before deleting a product that should be preserved:

1. Generate the JSON and Markdown exports from the Summary & Export tab.
2. Confirm the product UUID with the team or instructor.
3. Confirm the backup schedule and restore point.
4. Use the deletion control with explicit confirmation.

Database backups follow the procedures in `README.md` and `ops/backup_postgres.sh`. Deletion actions should be recorded in deployment operations logs without logging product content or credentials.
