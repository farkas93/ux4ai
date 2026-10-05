from functools import lru_cache
from html import escape

from alembic.config import Config
from alembic.script import ScriptDirectory
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from .auth import AuthenticationError, authenticate, revoke_session
from .config import get_settings
from .db import SessionLocal
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
<li><span class="step" aria-hidden="true">2</span><div><strong>Explore the unknowns</strong><small>Discuss product dimensions, AI safety, and improvement.</small></div></li>
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
    return set(ScriptDirectory.from_config(Config("alembic.ini")).get_heads())


def create_auth_app(session_factory=SessionLocal) -> FastAPI:
    app = FastAPI(title="AI Product Toolkit")
    settings = get_settings()

    @app.middleware("http")
    async def require_session(request: Request, call_next):
        path = request.url.path
        if path.startswith("/app"):
            with session_factory() as db:
                try:
                    from .auth import get_authenticated_user
                    get_authenticated_user(db, request.cookies.get(settings.cookie_name))
                except AuthenticationError:
                    return RedirectResponse(f"/auth/login?next={path}", status_code=303)
        return await call_next(request)

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
    async def readyz():
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
        return RedirectResponse("/auth/login", status_code=303)

    @app.get("/auth/login", response_class=HTMLResponse)
    async def login_page(next: str = "/app"):
        return HTMLResponse(_login_page(next_path=_safe_next(next)))

    @app.post("/auth/login")
    async def login(request: Request):
        form = await request.form()
        username = str(form.get("username", ""))
        password = str(form.get("password", ""))
        next_path = _safe_next(str(form.get("next", "/app")))
        with session_factory() as db:
            try:
                token, _ = authenticate(db, username, password, request.client.host if request.client else None)
            except AuthenticationError:
                return HTMLResponse(_login_page("Invalid credentials or temporarily rate limited.", next_path), status_code=401)
        response = RedirectResponse(next_path, status_code=303)
        response.set_cookie(settings.cookie_name, token, max_age=settings.session_ttl_hours * 3600, httponly=True, secure=settings.cookie_secure, samesite="lax", path="/")
        return response

    @app.get("/auth/logout")
    async def logout(request: Request):
        with session_factory() as db:
            revoke_session(db, request.cookies.get(settings.cookie_name))
        response = RedirectResponse("/auth/login", status_code=303)
        response.delete_cookie(settings.cookie_name, path="/")
        return response

    from .tunnel_services import close_public_access

    app.add_event_handler("shutdown", close_public_access)

    return app
