"""Qt window adapters around the existing loopback Gradio application."""

import logging
import os
import shutil
import sys
import tempfile
from pathlib import Path

from .desktop_runtime import SAVE_AND_CLOSE_JS
from .paths import atomic_json, resource_path

logger = logging.getLogger(__name__)


def copy_download(source: Path, destination: Path):
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=destination.parent, prefix=".aipm-export-", delete=False) as file:
            temporary = Path(file.name)
            with source.open("rb") as original:
                shutil.copyfileobj(original, file)
            file.flush()
            os.fsync(file.fileno())
        os.replace(temporary, destination)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def show_startup_error(message):
    try:
        from PySide6.QtWidgets import QApplication, QMessageBox

        app = QApplication.instance() or QApplication([])
        QMessageBox.critical(None, "AI Product Toolkit", message)
        return app
    except ImportError:
        logger.exception("The desktop GUI dependencies are unavailable")
        if sys.stderr is not None:
            print(message, file=sys.stderr)


def run_window(runtime, smoke_test=False):
    # Qt's GUI runs on the main thread; Uvicorn owns its separate asyncio loop.
    from PySide6.QtCore import QTimer, QUrl
    from PySide6.QtGui import QFontDatabase
    from PySide6.QtQml import QQmlApplicationEngine
    from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox

    flags = "--disable-background-networking --disable-component-update --disable-sync"
    if sys.platform == "win32":
        from PySide6.QtWebView import QtWebView

        os.environ["QT_WEBVIEW_PLUGIN"] = "webview2"
        os.environ["WEBVIEW2_USER_DATA_FOLDER"] = str(runtime.data_dir / "cache" / "webview2")
        os.environ.setdefault("WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS", flags)
        if getattr(sys, "frozen", False):
            fixed = resource_path("webview2")
            if not (fixed / "msedgewebview2.exe").exists():
                raise RuntimeError("The bundled WebView2 runtime is missing")
            os.environ["WEBVIEW2_BROWSER_EXECUTABLE_FOLDER"] = str(fixed)
        QtWebView.initialize()
        renderer = "WebView.qml"
    else:
        from PySide6.QtWebEngineQuick import QtWebEngineQuick

        os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = (
            os.environ.get("QTWEBENGINE_CHROMIUM_FLAGS", "") + " " + flags
        ).strip()
        QtWebEngineQuick.initialize()
        renderer = "WebEngine.qml"
    app = QApplication.instance() or QApplication(sys.argv[:1])
    app.setApplicationName("AI Product Toolkit")
    app.setOrganizationName("AIProductToolkit")
    QFontDatabase.addApplicationFont(str(resource_path("fonts/DejaVuSans.ttf")))
    engine = QQmlApplicationEngine()
    engine.warnings.connect(lambda errors: logger.error("QML: %s", "\n".join(error.toString() for error in errors)))
    context = engine.rootContext()
    context.setContextProperty("initialUrl", QUrl(runtime.bootstrap_url))
    context.setContextProperty("rendererFile", renderer)
    context.setContextProperty("profileCachePath", (runtime.data_dir / "cache" / "browser").as_posix())
    context.setContextProperty("profileStoragePath", (runtime.data_dir / "cache" / "browser-storage").as_posix())
    context.setContextProperty("saveScript", SAVE_AND_CLOSE_JS)
    engine.load(QUrl.fromLocalFile(str(resource_path("desktop/Window.qml"))))
    if not engine.rootObjects():
        raise RuntimeError("The application window could not be loaded")
    window = engine.rootObjects()[0]
    closing = False
    ready = False
    exit_code = 0
    section_index = 0
    section_pending = False
    sections = [("Value Hypothesis", "page-project-setup", False),
                ("Explore Dimensions", "page-assessment", True),
                ("Explore Backlog", "page-backlog-creator", False),
                ("Explore Priority", "page-prioritization", True),
                ("Build Self-Improvement", "page-self-improvement", False),
                ("Summary & Export", "page-summary-export", False)]

    def allow_close():
        window.setProperty("shutdownAllowed", True)
        window.close()
        app.quit()

    def request_close():
        nonlocal closing
        if closing:
            return
        closing = True
        runtime.begin_close()
        window.requestSave()

    def save_unavailable():
        nonlocal closing
        if not ready:
            allow_close()  # No editable workspace has been presented yet.
        else:
            closing = False
            QMessageBox.warning(None, "AI Product Toolkit", "Saving could not be requested. Please try closing again.")

    def check_result(value):
        nonlocal ready
        if value and not ready:
            ready = True

    def section_result(value):
        nonlocal section_index, section_pending
        section_pending = False
        if value:
            section_index += 1

    def drain_commands():
        nonlocal closing, exit_code, section_pending
        while not runtime.commands.empty():
            command, value = runtime.commands.get()
            if command == "closed":
                allow_close()
            elif command == "quit":
                request_close()
            elif command == "focus":
                window.showNormal()
                window.raise_()
                window.requestActivate()
            elif command == "save_failed":
                closing = False
                logger.error("Native close could not save the workspace: %s", value)
                if smoke_test:
                    atomic_json(runtime.data_dir / "native-smoke.json",
                                {"ready": ready, "renderer": renderer, "save_error": str(value)})
                    exit_code = 1
                    allow_close()
                    continue
                choice = QMessageBox.warning(
                    None, "Changes could not be saved", str(value) + "\n\nClose without saving these edits?",
                    QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel,
                    QMessageBox.StandardButton.Cancel,
                )
                if choice == QMessageBox.StandardButton.Discard:
                    allow_close()
            elif command == "download":
                source = Path(value)
                downloads = Path.home() / "Downloads"
                initial = (downloads if downloads.is_dir() else Path.home()) / source.name
                destination, _filter = QFileDialog.getSaveFileName(None, "Save exported file", str(initial))
                if destination:
                    try:
                        copy_download(source, Path(destination))
                    except OSError as exc:
                        QMessageBox.warning(None, "Export could not be saved", str(exc))
        if not ready and not closing:
            window.checkReady()
        if smoke_test and ready and not closing:
            if section_index == len(sections):
                atomic_json(runtime.data_dir / "native-smoke.json",
                            {"ready": True, "renderer": renderer, "sections": len(sections), "graphs": True})
                request_close()
            elif not section_pending:
                section_pending = True
                window.checkSection(*sections[section_index])

    def startup_timeout():
        nonlocal exit_code
        if smoke_test and (not ready or section_index < len(sections)):
            exit_code = 1
            atomic_json(runtime.data_dir / "native-smoke.json", {"ready": False, "renderer": renderer})
            allow_close()

    window.closeRequested.connect(request_close)
    window.saveUnavailable.connect(save_unavailable)
    window.readyChecked.connect(check_result)
    window.sectionChecked.connect(section_result)
    timer = QTimer()
    timer.timeout.connect(drain_commands)
    timer.start(200)
    QTimer.singleShot(60_000, startup_timeout)
    window.show()
    app.exec()
    return exit_code
