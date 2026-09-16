from html import escape

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from .auth import AuthenticationError, authenticate, revoke_session
from .config import get_settings
from .db import SessionLocal


def _safe_next(value: str | None) -> str:
    if value and value.startswith("/") and not value.startswith("//"):
        return value
    return "/app"


def _login_page(error: str = "", next_path: str = "/app") -> str:
    message = f'<p role="alert">{escape(error)}</p>' if error else ""
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>AIPM Toolkit sign in</title></head>
<body><main><h1>AIPM Toolkit</h1>{message}
<form method="post" action="/auth/login">
<input type="hidden" name="next" value="{escape(next_path)}">
<label>Username <input name="username" autocomplete="username" required></label>
<label>Password <input name="password" type="password" autocomplete="current-password" required></label>
<button type="submit">Sign in</button>
</form></main></body></html>"""


def create_auth_app(session_factory=SessionLocal) -> FastAPI:
    app = FastAPI(title="AIPM Toolkit")
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

    return app
