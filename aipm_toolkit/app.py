"""UI assembly for the AIPM Toolkit workspace."""

from .ui.callbacks import _resolve_token  # noqa: F401  (re-exported for compatibility)
from .ui.shell import build_app

app = build_app()


if __name__ == "__main__":
    app.launch()
