"""Packaged entry point: profile bootstrap, loopback server and desktop window."""

import argparse
import json
import logging
import os
import signal
import socket
import sqlite3
import sys
import tempfile
import threading
import time
import urllib.request
from logging.handlers import RotatingFileHandler
from pathlib import Path
from xml.sax.saxutils import escape

logger = logging.getLogger(__name__)


def default_data_dir() -> Path:
    from platformdirs import user_data_path

    return user_data_path("AIProductToolkit", appauthor=False).resolve()


def configure_profile(data_dir: Path):
    if "aipm_toolkit.db" in sys.modules:
        raise RuntimeError("Desktop profile must be configured before importing the database")
    os.environ.update({
        "AIPM_MODE": "desktop", "AIPM_DATA_DIR": str(data_dir),
        "GRADIO_ANALYTICS_ENABLED": "False", "HF_HUB_DISABLE_TELEMETRY": "1",
        "HF_HUB_OFFLINE": "1", "GRADIO_SSR_MODE": "False", "GRADIO_MCP_SERVER": "False",
        "GRADIO_TEMP_DIR": str(data_dir / "cache" / "gradio"),
        "HF_HOME": str(data_dir / "cache" / "huggingface"),
        "XDG_CACHE_HOME": str(data_dir / "cache"),
        "TMPDIR": str(data_dir / "cache" / "tmp"),
        "TEMP": str(data_dir / "cache" / "tmp"), "TMP": str(data_dir / "cache" / "tmp"),
    })
    sys.dont_write_bytecode = True
    for name in ("imports", "exports", "backups", "logs", "cache/tmp", "cache/gradio"):
        (data_dir / name).mkdir(parents=True, exist_ok=True, mode=0o700)
    tempfile.tempdir = str(data_dir / "cache" / "tmp")
    from .config import get_settings

    get_settings.cache_clear()
    if sys.platform.startswith("linux"):
        from .paths import resource_path

        # Fontconfig is an OS library, but the app supplies a valid fallback
        # font set and profile-local cache even on minimal desktop systems.
        font_cache = data_dir / "cache" / "fontconfig"
        font_cache.mkdir(parents=True, exist_ok=True, mode=0o700)
        fonts = escape(resource_path("fonts").as_posix())
        cache = escape(font_cache.as_posix())
        config = font_cache / "fonts.conf"
        config.write_text(
            '<?xml version="1.0"?><!DOCTYPE fontconfig SYSTEM "urn:fontconfig:fonts.dtd">'
            f'<fontconfig><dir>{fonts}</dir><dir>/usr/share/fonts</dir>'
            f'<dir>/usr/local/share/fonts</dir><cachedir>{cache}</cachedir></fontconfig>',
            encoding="utf-8",
        )
        os.environ["FONTCONFIG_FILE"] = str(config)
    log = RotatingFileHandler(data_dir / "logs" / "application.log", maxBytes=2_000_000,
                              backupCount=3, encoding="utf-8")
    logging.basicConfig(level=logging.INFO, handlers=[log])


def initialize_storage(data_dir: Path):
    from alembic.script import ScriptDirectory
    from sqlalchemy import delete, select

    from alembic import command

    from .assessment_services import ensure_scale_definitions
    from .baseline_services import import_legacy_reference_json, publish_all_reference_datasets
    from .db import SessionLocal, engine
    from .models import Course, Role, SessionRecord, Team, User
    from .paths import migration_config, resource_path

    config = migration_config()
    config.attributes["skip_logging"] = True
    heads = set(ScriptDirectory.from_config(config).get_heads())
    path = data_dir / "workspace.sqlite3"
    if path.exists() and path.stat().st_size:
        with sqlite3.connect(f"{path.as_uri()}?mode=ro", uri=True) as source:
            try:
                applied = {row[0] for row in source.execute("SELECT version_num FROM alembic_version")}
            except sqlite3.OperationalError:
                applied = set()
            if applied != heads:
                backup = data_dir / "backups" / f"before-upgrade-{time.time_ns()}.sqlite3"
                with sqlite3.connect(backup) as target:
                    source.backup(target)
    with engine.begin() as connection:
        config.attributes["connection"] = connection
        command.upgrade(config, "head")
    with SessionLocal.begin() as db:
        user = db.scalar(select(User).where(User.username == "desktop-local"))
        if user is None:
            course = Course(name="Personal workspace")
            db.add(course)
            db.flush()
            team = Team(course_id=course.id, alias="local")
            db.add(team)
            db.flush()
            user = User(username="desktop-local", role=Role.TEAM.value, team_id=team.id,
                        password_hash="!desktop-launch-session-only")
            db.add(user)
            db.flush()
        if user.role != Role.TEAM.value or user.team_id is None or not user.is_active:
            raise RuntimeError("The local workspace identity is invalid")
        # Sessions belong to one launch; old cookies do not survive a restart.
        db.execute(delete(SessionRecord).where(SessionRecord.user_id == user.id))
        user_id = user.id
    with SessionLocal() as db:
        ensure_scale_definitions(db)
        catalog = resource_path("baseline")
        manifest = json.loads((catalog / "import_manifest.json").read_text(encoding="utf-8"))
        report = import_legacy_reference_json(db, catalog / "products", manifest=manifest)
        if report["invalid_values"]:
            raise RuntimeError("Bundled product reference catalog failed validation")
        publish_all_reference_datasets(db, manifest["cohort_label"])
    return user_id, engine


class LocalServer:
    def __init__(self, runtime, sock):
        self.runtime = runtime
        self.socket = sock
        self.failure = None
        self.server = None
        self.thread = threading.Thread(target=self._run, name="aipm-local-server", daemon=True)

    def _run(self):
        import asyncio

        import uvicorn

        from .application import create_application

        try:
            app = create_application(desktop_runtime=self.runtime)
            config = uvicorn.Config(app, host="127.0.0.1", port=0, loop="asyncio", http="h11",
                                    ws="none", access_log=False, log_config=None,
                                    timeout_graceful_shutdown=15)
            self.server = uvicorn.Server(config)
            asyncio.run(self.server.serve(sockets=[self.socket]))
        except BaseException as exc:
            self.failure = exc
            logger.exception("Local application server failed")

    def start(self):
        self.thread.start()
        deadline = time.monotonic() + 60
        # Explicitly ignore HTTP_PROXY for local readiness requests.
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        while time.monotonic() < deadline:
            if self.failure is not None:
                raise RuntimeError("Local server failed to start") from self.failure
            try:
                with opener.open(self.runtime.origin + "/readyz", timeout=1) as response:
                    if response.status == 200:
                        return
            except OSError:
                pass
            time.sleep(0.05)
        raise TimeoutError("Local application did not become ready")

    def stop(self):
        if self.server is not None:
            self.server.should_exit = True
        self.thread.join(timeout=20)
        if self.thread.is_alive():
            raise RuntimeError("Local server did not stop cleanly")
        self.socket.close()


def _focus_existing(data_dir):
    try:
        metadata = json.loads((data_dir / "instance.json").read_text(encoding="utf-8"))
        parsed = urllib.parse.urlsplit(metadata["origin"])
        if parsed.scheme != "http" or parsed.hostname != "127.0.0.1":
            return False
        request = urllib.request.Request(metadata["origin"] + "/desktop/focus", data=b"{}",
                                         headers={"Authorization": "Bearer " + metadata["control_token"],
                                                  "Content-Type": "application/json"})
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open(request, timeout=2):
            return True
    except (OSError, ValueError, KeyError):
        return False


def main(argv=None):
    parser = argparse.ArgumentParser(description="AI Product Toolkit desktop")
    parser.add_argument("--data-dir", type=Path, help="Use a separate local workspace profile")
    parser.add_argument("--headless", action="store_true", help="Run the local runtime for automated tests")
    parser.add_argument("--smoke-test", action="store_true", help="Validate native window startup, then quit")
    args = parser.parse_args(argv)
    if args.smoke_test and args.data_dir is None:
        parser.error("--smoke-test requires an explicit disposable --data-dir")
    data_dir = (args.data_dir or default_data_dir()).expanduser().resolve()
    data_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    from filelock import FileLock, Timeout

    lock = FileLock(data_dir / "workspace.lock")
    try:
        lock.acquire(timeout=0)
    except Timeout:
        if _focus_existing(data_dir):
            return 0
        parser.exit(1, "This workspace is already running. Close its other instance first.\n")
    server = engine = runtime = sock = None
    try:
        configure_profile(data_dir)
        user_id, engine = initialize_storage(data_dir)
        if args.smoke_test:
            from sqlalchemy import select

            from .db import SessionLocal
            from .dimensions import DEFAULT_DIMENSIONS
            from .hypothesis_services import create_hypothesis, set_placement
            from .models import DimensionEstimate, Project, User
            from .services import create_project

            with SessionLocal() as db:
                actor = db.get(User, user_id)
                if db.scalar(select(Project.id).where(Project.team_id == actor.team_id)) is None:
                    project = create_project(db, actor, "Desktop qualification project")
                    for definition in DEFAULT_DIMENSIONS:
                        db.add(DimensionEstimate(project_id=project.id, dimension_key=definition["key"],
                                                 scale_version=1, status="estimated", score=3.5,
                                                 rationale="Offline native qualification"))
                    db.commit()
                    hypothesis = create_hypothesis(db, actor, project.id, "Native chart qualification")
                    set_placement(db, actor, hypothesis.id, hypothesis.revision, 6.5, 3.5)
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind(("127.0.0.1", 0))
        from .desktop_runtime import DesktopRuntime
        from .paths import atomic_json

        runtime = DesktopRuntime(data_dir, sock.getsockname()[1], user_id)
        server = LocalServer(runtime, sock)
        server.start()
        metadata = {"pid": os.getpid(), "origin": runtime.origin,
                    "control_token": runtime.control_token}
        if args.headless:
            metadata["bootstrap_url"] = runtime.bootstrap_url
        atomic_json(data_dir / "instance.json", metadata)
        if args.headless:
            stopped = threading.Event()
            signal.signal(signal.SIGINT, lambda *_: stopped.set())
            signal.signal(signal.SIGTERM, lambda *_: stopped.set())
            while not stopped.wait(0.1):
                while not runtime.commands.empty():
                    command, _value = runtime.commands.get()
                    if command in {"closed", "quit"}:
                        stopped.set()
                if server.failure is not None or not server.thread.is_alive():
                    raise RuntimeError("Local server exited unexpectedly")
            return 0
        from .desktop_window import run_window

        return run_window(runtime, smoke_test=args.smoke_test)
    except Exception:
        logger.exception("Desktop startup failed")
        if args.headless or args.smoke_test:
            raise
        from .desktop_window import show_startup_error

        show_startup_error("AI Product Toolkit could not start. See logs/application.log in " + str(data_dir))
        return 1
    finally:
        try:
            if server is not None:
                server.stop()
            elif sock is not None:
                sock.close()
            if engine is not None:
                from sqlalchemy import delete

                from .db import SessionLocal
                from .models import SessionRecord

                if runtime is not None:
                    with SessionLocal.begin() as db:
                        db.execute(delete(SessionRecord).where(SessionRecord.user_id == runtime.user_id))
                engine.dispose()
        finally:
            (data_dir / "instance.json").unlink(missing_ok=True)
            lock.release()


if __name__ == "__main__":
    raise SystemExit(main())
