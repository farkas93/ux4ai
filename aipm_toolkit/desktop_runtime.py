"""Local instance coordination, independent of the native window toolkit."""

import hmac
import queue
import secrets
import threading
import time
from pathlib import Path
from urllib.parse import unquote, urlsplit
from uuid import UUID

from .paths import atomic_json, read_preferences


class DesktopRuntime:
    def __init__(self, data_dir: Path, port: int, user_id: UUID):
        self.data_dir = data_dir.resolve()
        self.origin = f"http://127.0.0.1:{port}"
        self.user_id = user_id
        self.control_token = secrets.token_urlsafe(32)
        self._bootstrap_token = secrets.token_urlsafe(32)
        self._bootstrap_deadline = time.monotonic() + 180
        self._bootstrap_used = False
        self._lock = threading.Lock()
        self.commands: queue.Queue = queue.Queue()
        self._close_result: bool | None = None
        self._close_error = ""
        self.preferences = read_preferences()

    @property
    def bootstrap_url(self):
        return f"{self.origin}/desktop/start?token={self._bootstrap_token}"

    def claim_bootstrap(self, token: str) -> bool:
        with self._lock:
            valid = (
                not self._bootstrap_used
                and time.monotonic() <= self._bootstrap_deadline
                and hmac.compare_digest(token, self._bootstrap_token)
            )
            if valid:
                self._bootstrap_used = True
            return valid

    def valid_control(self, authorization: str | None) -> bool:
        return hmac.compare_digest(authorization or "", f"Bearer {self.control_token}")

    def valid_request(self, host: str, origin: str | None, client: str | None) -> bool:
        expected = urlsplit(self.origin).netloc
        return host == expected and client in {"127.0.0.1", "::1"} and (
            origin is None or origin == self.origin
        )

    def begin_close(self):
        with self._lock:
            self._close_result = None
            self._close_error = ""

    def complete_close(self, saved: bool, message: str = ""):
        with self._lock:
            self._close_result = saved
            self._close_error = "" if saved else message
        self.commands.put(("closed" if saved else "save_failed", message))

    def state(self):
        with self._lock:
            return {"saved": self._close_result, "error": self._close_error}

    def save_preference(self, key, value):
        with self._lock:
            self.preferences[key] = value
            atomic_json(self.data_dir / "preferences.json", self.preferences)

    def request_download(self, url: str):
        parsed = urlsplit(url)
        if parsed.scheme != "http" or parsed.netloc != urlsplit(self.origin).netloc:
            raise ValueError("Only this application's generated files can be downloaded")
        prefix = "/app/gradio_api/file="
        if not parsed.path.startswith(prefix):
            raise ValueError("Invalid download URL")
        path = Path(unquote(parsed.path[len(prefix):])).resolve()
        permitted = (self.data_dir / "exports", self.data_dir / "cache")
        if not any(path.is_relative_to(root.resolve()) for root in permitted) or not path.is_file():
            raise ValueError("The prepared file is no longer available; prepare downloads again")
        self.commands.put(("download", path))


DESKTOP_JS = r"""
document.addEventListener('click', async (event) => {
    const anchor = event.target.closest('a[href]');
    if (!anchor) return;
    const url = new URL(anchor.href, window.location.href);
    if (url.origin !== window.location.origin ||
        !url.pathname.startsWith('/app/gradio_api/file=')) return;
    event.preventDefault();
    try {
        const response = await fetch('/desktop/download', {
            method: 'POST', credentials: 'same-origin',
            headers: {'Content-Type': 'application/json', 'X-AIPM-Desktop': '1'},
            body: JSON.stringify({url: url.href})
        });
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Download could not be prepared.');
        }
    } catch (error) { window.alert(error.message); }
}, true);
"""

SAVE_AND_CLOSE_JS = r"""(() => {
    const element = document.getElementById('toolkit-desktop-close-button');
    const button = element?.matches('button') ? element : element?.querySelector('button');
    if (!button) return false;
    button.click();
    return true;
})()"""
