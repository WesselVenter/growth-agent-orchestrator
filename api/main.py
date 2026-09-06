"""FastAPI app: single-PIN auth (session cookie) gating the Runs API + SSE
stream, and — once frontend/dist exists (see frontend/README.md or the
Railway build step) — serving the built React SPA for every other route.

Run locally with:
    python -m uvicorn api.main:app --reload

In local dev without a built frontend, run `npm run dev` in frontend/
instead and let Vite's dev-server proxy (frontend/vite.config.ts) forward
API calls here; frontend/dist won't exist yet, so the SPA-serving pieces
below simply no-op and every non-API path 404s from this process, which is
expected — it's the deployed/production entrypoint.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, Form, Request
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from starlette.types import Receive, Scope, Send

load_dotenv()

APP_PIN = os.environ.get("APP_PIN")
SESSION_SECRET_KEY = os.environ.get("SESSION_SECRET_KEY")

if not APP_PIN:
    raise RuntimeError("APP_PIN environment variable is required (set it in .env).")
if not SESSION_SECRET_KEY:
    raise RuntimeError("SESSION_SECRET_KEY environment variable is required (set it in .env).")

SESSION_KEY = "authenticated"
DEFAULT_NEXT = "/health"

# The only real protected data surface. Everything else — the SPA shell,
# its static assets, POST /login, GET /health — is public; the frontend's
# own client-side routing (ProtectedRoute) decides what a human sees,
# while this middleware protects the actual API.
PROTECTED_PATH_PREFIX = "/runs"

FRONTEND_DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist"
FRONTEND_INDEX = FRONTEND_DIST / "index.html"


def _wants_html(scope: Scope) -> bool:
    for key, value in scope.get("headers", []):
        if key == b"accept":
            return b"text/html" in value
    return False


class SPAFallbackMiddleware:
    """Serves the built SPA's index.html for browser page navigations,
    before routing happens — not just as a "catch unmatched paths"
    fallback, but to resolve a genuine collision: several frontend
    client-side routes are byte-for-byte identical to backend API paths
    (GET /runs/{id} is both the RunView page URL and a JSON endpoint). A
    fallback route registered *after* the API routes would never even be
    reached for those paths, since Starlette's router commits to the first
    matching route regardless of what the client actually wants back.

    Intercepting here, pre-routing, on the Accept header is what lets a
    hard navigation/refresh on a client-side route serve the SPA instead
    of the API's JSON — the exact same fix as frontend/vite.config.ts's
    dev-proxy `bypass`, applied server-side because in production there's
    no separate dev server left to do it in.

    Everything else — POST requests, and GETs with a non-HTML Accept
    (our own fetch() calls send `Accept: application/json`; EventSource
    sends `Accept: text/event-stream`) — passes straight through to normal
    routing: the real API routes, or the StaticFiles mount below for
    actual asset files.
    """

    def __init__(self, app) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if (
            scope["type"] == "http"
            and scope["method"] == "GET"
            and FRONTEND_INDEX.exists()
            and _wants_html(scope)
        ):
            # No caching: FileResponse sets ETag/Last-Modified by default,
            # and without Cache-Control the browser can and will reuse a
            # cached response for this exact URL on a *later* fetch() to
            # the same path with a different Accept header (e.g. RunView's
            # JSON call to GET /runs/{id} right after a hard refresh of
            # that same URL) — silently resurrecting the very bug this
            # middleware exists to fix. Vary: Accept is defense in depth
            # for any intermediary that ignores Cache-Control.
            response = FileResponse(
                FRONTEND_INDEX,
                headers={"Cache-Control": "no-store", "Vary": "Accept"},
            )
            await response(scope, receive, send)
            return

        await self.app(scope, receive, send)


class PinAuthMiddleware:
    """Plain ASGI middleware (not BaseHTTPMiddleware / a route dependency),
    so it applies uniformly to every route — JSON routes and the SSE
    stream alike — and never buffers a streaming response the way
    BaseHTTPMiddleware can.

    Only guards PROTECTED_PATH_PREFIX. By the time a request reaches here,
    SPAFallbackMiddleware (outer) has already peeled off every browser
    page navigation, so anything hitting a /runs* path at this point is,
    by construction, a POST or a non-HTML GET (fetch/EventSource) — never
    something a redirect would meaningfully help, so an unauthenticated
    request always just gets plain 401 JSON.

    Requires SessionMiddleware to run first so request.session is already
    populated; see the add_middleware() call order below, which controls
    that.
    """

    def __init__(self, app) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or not scope["path"].startswith(PROTECTED_PATH_PREFIX):
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive=receive)
        if request.session.get(SESSION_KEY) is True:
            await self.app(scope, receive, send)
            return

        response = JSONResponse({"detail": "Not authenticated"}, status_code=401)
        await response(scope, receive, send)


app = FastAPI(title="Growth Agent Orchestrator API")

# Order matters here. Starlette's add_middleware() prepends to the
# middleware list, and the list is then wrapped outermost-first from the
# *last* entry added — so the middleware added *last* runs *first* on each
# request. Desired execution order: SPAFallback -> Session -> PinAuth ->
# routes, so SPAFallback is added last, PinAuth first.
app.add_middleware(PinAuthMiddleware)
app.add_middleware(
    SessionMiddleware,
    secret_key=SESSION_SECRET_KEY,
    session_cookie="gao_session",
    same_site="lax",
    https_only=os.environ.get("SESSION_HTTPS_ONLY", "false").lower() == "true",
)
app.add_middleware(SPAFallbackMiddleware)

from api.routes import runs, stream  # noqa: E402  (import after app/middleware setup)

app.include_router(runs.router)
app.include_router(stream.router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/login", response_model=None)
def login_submit(
    request: Request, pin: str = Form(...), next: str = Form(DEFAULT_NEXT)
) -> RedirectResponse | JSONResponse:
    if pin != APP_PIN:
        return JSONResponse({"detail": "Incorrect PIN."}, status_code=401)

    request.session[SESSION_KEY] = True
    return RedirectResponse(url=next or DEFAULT_NEXT, status_code=303)


# Real static asset files (JS/CSS bundle, anything under frontend/public).
# Registered *after* the API routers, so those exact paths always win;
# this only ever serves what's left over. Never crashes if the frontend
# hasn't been built (e.g. local backend-only dev) — StaticFiles requires
# an existing directory, so it's only mounted when frontend/dist exists.
if FRONTEND_DIST.exists():
    app.mount("/", StaticFiles(directory=FRONTEND_DIST, html=True), name="frontend")
