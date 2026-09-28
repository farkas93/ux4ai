"""Process-local lifecycle for the optional public Gradio share tunnel.

The LAN NodePort is independent and remains available. Public access always
reaches the existing authenticated FastAPI app; this module only manages FRP.
"""

import atexit
import logging
import secrets
import threading
from urllib.parse import urlparse

from gradio import networking
from gradio.tunneling import CURRENT_TUNNELS

_lock = threading.Lock()
_tunnel = None
_public_url: str | None = None
_logger = logging.getLogger(__name__)


def public_access_status() -> dict[str, str | bool | None]:
    global _tunnel, _public_url
    with _lock:
        if _tunnel is not None and (_tunnel.proc is None or _tunnel.proc.poll() is not None):
            _tunnel = None
            _public_url = None
        return {"enabled": _tunnel is not None, "url": _public_url}


def open_public_access(port: int = 7860) -> str:
    """Open an authenticated gradio.live route to this process's FastAPI port."""
    global _tunnel, _public_url
    with _lock:
        if _tunnel is not None and _tunnel.proc is not None and _tunnel.proc.poll() is None:
            return _public_url or ""
        before = {id(tunnel) for tunnel in CURRENT_TUNNELS}
        try:
            url = networking.setup_tunnel(
                local_host="127.0.0.1",
                local_port=port,
                share_token=secrets.token_urlsafe(24),
                share_server_address=None,
                share_server_tls_certificate=None,
            )
            tunnel = next((item for item in reversed(CURRENT_TUNNELS) if id(item) not in before), None)
            if tunnel is None:
                raise RuntimeError("Gradio did not return a tunnel process")
            _tunnel = tunnel
            parsed = urlparse(url if "://" in url else f"https://{url}")
            _public_url = parsed.geturl()
            return _public_url
        except Exception:
            for tunnel in [item for item in CURRENT_TUNNELS if id(item) not in before]:
                try:
                    tunnel.kill()
                except Exception as cleanup_error:  # noqa: BLE001 - cleanup must not mask setup failure
                    _logger.warning("Could not clean up failed Gradio tunnel: %s", cleanup_error)
                finally:
                    CURRENT_TUNNELS.remove(tunnel)
            _tunnel = None
            _public_url = None
            raise


def close_public_access() -> None:
    """Close the public tunnel without restarting the app or its LAN service."""
    global _tunnel, _public_url
    with _lock:
        if _tunnel is not None:
            try:
                _tunnel.kill()
            finally:
                if _tunnel in CURRENT_TUNNELS:
                    CURRENT_TUNNELS.remove(_tunnel)
                _tunnel = None
                _public_url = None
        else:
            _public_url = None


atexit.register(close_public_access)
