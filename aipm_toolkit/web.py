from functools import lru_cache
from html import escape

from alembic.script import ScriptDirectory
from anyio import CapacityLimiter, to_thread
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from .auth import (
    AuthenticationError,
    authenticate,
    get_authenticated_user,
    issue_session,
    revoke_session,
)
from .config import get_settings
from .db import SessionLocal
from .paths import migration_config
from .ui.login_style import LOGIN_CSS


def _safe_next(value: str | None) -> str:
    if value and value.startswith("/") and not value.startswith("//"):
        return value
    return "/app"


def _login_page(error: str = "", next_path: str = "/app") -> str:
    message = f'<p class="error" role="alert">{escape(error)}</p>' if error else ""
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>AI Product Toolkit · Sign in</title><style>{LOGIN_CSS}</style></head>
<body><main>
<div class="brand"><span class="brand-mark" aria-hidden="true">AI</span>AI Product Toolkit</div>
<div class="layout"><section aria-labelledby="intro-title">
<p class="eyebrow">A workspace for learning AI product management</p>
<h1 id="intro-title">Turn an AI idea into a clear value hypothesis.</h1>
<p class="intro">Explore who your product helps and why it matters. Capture questions and assumptions,
then build a backlog of testable hypotheses with your team.</p>
<ol class="steps">
<li><span class="step" aria-hidden="true">1</span><div><strong>Find the value</strong><small>Define the user, their problem, and your product idea.</small></div></li>
<li><span class="step" aria-hidden="true">2</span><div><strong>Explore the unknowns</strong><small>Assess product dimensions and imagine how the product could improve.</small></div></li>
<li><span class="step" aria-hidden="true">3</span><div><strong>Build your hypothesis backlog</strong><small>Turn assumptions into hypotheses and decide what to test next.</small></div></li>
</ol></section><section class="card" aria-labelledby="signin-title">
<h2 id="signin-title">Welcome to your workspace</h2>
<p class="hint">Sign in with the team or instructor account provided for your course.</p>{message}
<form method="post" action="/auth/login">
<input type="hidden" name="next" value="{escape(next_path)}">
<label for="username">Username</label><input id="username" name="username" autocomplete="username" placeholder="Your team alias or instructor username" required>
<label for="password">Password</label><input id="password" name="password" type="password" autocomplete="current-password" required>
<button type="submit">Sign in</button>
</form><p class="hint help">Need an account or help signing in? Ask your instructor.</p>
</section></div><footer>A learning toolkit for ideas, assumptions, and experiments.</footer>
</main></body></html>"""


@lru_cache(maxsize=1)
def _migration_heads() -> set[str]:
    return set(ScriptDirectory.from_config(migration_config()).get_heads())


def create_auth_app(session_factory=SessionLocal, desktop_runtime=None) -> FastAPI:
    app = FastAPI(title="AI Product Toolkit")
    settings = get_settings()
    login_limiter = CapacityLimiter(settings.password_concurrency_limit)

    def validate_session(token):
        # Each worker owns its SQLAlchemy session from creation through close.
        with session_factory() as db:
            get_authenticated_user(db, token)

    def authenticate_session(username, password, ip_address):
        with session_factory() as db:
            token, _ = authenticate(db, username, password, ip_address)
            return token

    @app.middleware("http")
    async def require_session(request: Request, call_next):
        if desktop_runtime is not None and not desktop_runtime.valid_request(
            request.headers.get("host", ""), request.headers.get("origin"),
            request.client.host if request.client else None,
        ):
            return JSONResponse({"detail": "Local workspace requests must originate on this device"}, status_code=403)
        path = request.url.path
        app_path = path == "/app" or path.startswith("/app/")
        # These routes contain Gradio's packaged frontend, never project files.
        # Do not exempt /file=, /gradio_api/, uploads, downloads, or app config.
        public_asset = path.startswith(("/app/assets/", "/app/static/"))
        if app_path and not public_asset:
            try:
                await to_thread.run_sync(validate_session, request.cookies.get(settings.cookie_name))
            except AuthenticationError:
                return RedirectResponse(
                    f"/auth/login?next={path}", status_code=303,
                    headers={"Cache-Control": "no-store", "Pragma": "no-cache", "Expires": "0"},
                )
        response = await call_next(request)
        if path == "/" or path.startswith("/auth/") or (app_path and not public_asset) or (public_asset and response.status_code >= 300):
            # Prevent nginx/browser caches from reusing redirects or session data.
            # Successful packaged assets may retain their normal cache policy.
            response.headers["Cache-Control"] = "no-store"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        return response

    @app.get("/healthz")
    async def healthz():
        return {"status": "ok"}

    @app.get("/manifest.json", include_in_schema=False)
    async def manifest():
        # Gradio's HTML references this root URL even when mounted at /app.
        return JSONResponse(
            {
                "name": "AI Product Toolkit",
                "short_name": "AI Toolkit",
                "description": "Explore product value and build a hypothesis backlog.",
                "start_url": "/app/",
                "scope": "/",
                "display": "standalone",
                "background_color": "#f3f6fa",
                "theme_color": "#0f766e",
            },
            media_type="application/manifest+json",
        )

    @app.get("/readyz")
    def readyz():
        try:
            with session_factory() as db:
                db.execute(text("SELECT 1"))
                applied = set(db.scalars(text("SELECT version_num FROM alembic_version")))
        except SQLAlchemyError as exc:
            raise HTTPException(status_code=503, detail="Database unavailable") from exc
        if applied != _migration_heads():
            raise HTTPException(status_code=503, detail="Database migrations are not current")
        return {"status": "ready"}

    @app.get("/", include_in_schema=False)
    async def root():
        return RedirectResponse("/app/" if desktop_runtime else "/auth/login", status_code=303)

    @app.get("/auth/login", response_class=HTMLResponse)
    async def login_page(next: str = "/app"):
        if desktop_runtime is not None:
            return HTMLResponse("Open this local workspace from the AI Product Toolkit desktop app.", status_code=401)
        return HTMLResponse(_login_page(next_path=_safe_next(next)))

    @app.post("/auth/login")
    async def login(request: Request):
        if desktop_runtime is not None:
            raise HTTPException(status_code=404, detail="Course login is unavailable in desktop mode")
        form = await request.form()
        username = str(form.get("username", ""))
        password = str(form.get("password", ""))
        next_path = _safe_next(str(form.get("next", "/app")))
        try:
            token = await to_thread.run_sync(
                authenticate_session, username, password,
                request.client.host if request.client else None,
                limiter=login_limiter,
            )
        except AuthenticationError:
            return HTMLResponse(_login_page("Invalid credentials or temporarily rate limited.", next_path), status_code=401)
        response = RedirectResponse(next_path, status_code=303)
        response.set_cookie(settings.cookie_name, token, max_age=settings.session_ttl_hours * 3600, httponly=True, secure=settings.cookie_secure, samesite="lax", path="/")
        return response

    @app.get("/auth/logout")
    def logout(request: Request):
        with session_factory() as db:
            revoke_session(db, request.cookies.get(settings.cookie_name))
        response = RedirectResponse("/auth/login", status_code=303)
        response.delete_cookie(settings.cookie_name, path="/")
        return response

    if desktop_runtime is not None:
        from .models import User

        @app.get("/desktop/start", include_in_schema=False)
        def start_desktop(token: str):
            if not desktop_runtime.claim_bootstrap(token):
                raise HTTPException(status_code=401, detail="Local launch link is invalid or already used")
            with session_factory() as db:
                user = db.get(User, desktop_runtime.user_id)
                if user is None:
                    raise HTTPException(status_code=503, detail="Local workspace identity is unavailable")
                raw_token = issue_session(db, user, ttl_hours=24 * 365)
            response = RedirectResponse("/app/", status_code=303)
            response.set_cookie(settings.cookie_name, raw_token, httponly=True,
                                secure=False, samesite="strict", path="/")
            response.headers["Cache-Control"] = "no-store"
            return response

        def require_control(request):
            if not desktop_runtime.valid_control(request.headers.get("authorization")):
                raise HTTPException(status_code=401, detail="Local instance control is unauthorized")

        @app.get("/desktop/state", include_in_schema=False)
        def desktop_state(request: Request):
            require_control(request)
            return desktop_runtime.state()

        @app.post("/desktop/focus", include_in_schema=False)
        def focus_desktop(request: Request):
            require_control(request)
            desktop_runtime.commands.put(("focus", None))
            return {"queued": True}

        @app.post("/desktop/quit", include_in_schema=False)
        def quit_desktop(request: Request):
            require_control(request)
            desktop_runtime.commands.put(("quit", None))
            return {"queued": True}

        @app.post("/desktop/download", include_in_schema=False)
        async def download_desktop(request: Request):
            if request.headers.get("x-aipm-desktop") != "1":
                raise HTTPException(status_code=403, detail="Invalid local download request")
            try:
                await to_thread.run_sync(validate_session, request.cookies.get(settings.cookie_name))
                payload = await request.json()
                url = payload.get("url")
                if not isinstance(url, str) or len(url) > 8192:
                    raise ValueError("Invalid download URL")
                desktop_runtime.request_download(url)
            except AuthenticationError as exc:
                raise HTTPException(status_code=401, detail="Authentication required") from exc
            except (ValueError, AttributeError) as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc
            return JSONResponse({"queued": True}, status_code=202)

    from .tunnel_services import close_public_access

    app.add_event_handler("shutdown", close_public_access)

    return app
