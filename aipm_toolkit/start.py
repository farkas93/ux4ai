import os
import subprocess


def main() -> None:
    subprocess.run(["alembic", "upgrade", "head"], check=True)
    host = os.getenv("AIPM_HOST", "0.0.0.0")
    port = os.getenv("AIPM_PORT", "7860")
    os.execvp("uvicorn", ["uvicorn", "aipm_toolkit.server:app", "--host", host, "--port", port])


if __name__ == "__main__":
    main()
