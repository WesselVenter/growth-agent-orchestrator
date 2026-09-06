# Growth Agent Orchestrator — Frontend

React (Vite + TypeScript + Tailwind) UI for the orchestrator's `api/` backend.

## Setup

```
npm install
```

The backend must be running first (from the project root):

```
python -m uvicorn api.main:app --reload
```

By default the dev server proxies `/runs`, `/login`, and `/health` to
`http://127.0.0.1:8000` (see `vite.config.ts` — change `BACKEND_URL` if your
backend runs elsewhere).

## Run

```
npm run dev
```

Open the printed local URL (usually http://localhost:5173). You'll be
redirected to `/login` — enter the `APP_PIN` configured on the backend.

## Why a proxy, not CORS

The dev server proxies backend routes so the browser sees frontend and
backend as one origin. That's what lets the PIN-auth session cookie work
with zero CORS/SameSite configuration — the cookie is set for "this
origin" and every request, including the SSE stream, genuinely is
same-origin. In production, deploy the built frontend behind the same
reverse proxy / origin as the backend for the same reason.

## Pages

- `/login` — PIN entry, posts to the backend's real `/login` route
- `/new` — start a new run
- `/history` — past runs, links into each
- `/runs/:id` — live agent timeline (via SSE) + final markdown report once complete
