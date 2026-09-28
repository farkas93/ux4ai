import os
import subprocess

from .seed import bootstrap_instructor


def main() -> None:
    run_migrations = os.getenv("AIPM_RUN_MIGRATIONS", "true").strip().lower() in {"1", "true", "yes"}
    if run_migrations:
        subprocess.run(["alembic", "upgrade", "head"], check=True)
    username = os.getenv("AIPM_INSTRUCTOR_USERNAME")
    password = os.getenv("AIPM_INSTRUCTOR_PASSWORD")
    if username or password:
        if not username or not password:
            raise RuntimeError("AIPM_INSTRUCTOR_USERNAME and AIPM_INSTRUCTOR_PASSWORD must be set together")
        bootstrap_instructor(username, password, os.getenv("AIPM_COURSE_NAME", "AIPM Workshop"))
    host = os.getenv("AIPM_HOST", "0.0.0.0")
    port = os.getenv("AIPM_PORT", "7860")
    os.execvp("uvicorn", ["uvicorn", "aipm_toolkit.server:app", "--host", host, "--port", port])


if __name__ == "__main__":
    main()
