# Growth Agent Orchestrator

A multi-agent system for SynapsesAI that turns a plain-English growth goal
into research, qualified leads, content, and outreach drafts.

## How it works

You give the CLI a goal, e.g.:

```
python cli.py "find 10 leads in the legal sector, Gauteng"
```

The **Coordinator** (`agents/coordinator.py`) parses the goal, routes it to
the relevant teams (`orchestration/router.py`), runs each team's agent
pipeline, and assembles a final report:

- **Research** — `researcher` (web search) → `synthesizer` (structured market brief)
- **Leadgen** — `prospector` (web search) → `qualifier` (ICP scoring)
- **Content** — `strategist` → `writer` → `critic` (revision loop, up to 2 passes)
- **Sales** — `outreach_drafter` (uses leads + content output)

Every agent call goes through `agents/base.py`'s `Agent.call()`, which logs
timestamp, input, output, tool calls, and duration to a shared `Trace`
(`orchestration/trace.py`). Handoffs between agents/teams are logged too.

Business context (SynapsesAI's services, ICP, differentiators, funnel) lives
in one place: `context/business_profile.py`. Every agent's system prompt is
built from it, so updating the business profile updates every agent.

## Setup

```
pip install -r requirements.txt
cp .env.example .env   # then fill in the values below
```

## Run (CLI)

```
python cli.py "write 3 LinkedIn posts about AI adoption for SA manufacturers"
```

Each run is saved under `runs/<run_id>/`:
- `goal.txt` — the original goal
- `report.md` — the final assembled report
- `trace.json` — full trace of every agent call and handoff

## Run (web app)

The `api/` module wraps the same orchestrator in a FastAPI app (Postgres-backed
run history, live SSE progress, PIN-gated) with a React frontend in `frontend/`.

Local dev runs backend and frontend as two processes:

```
python -m uvicorn api.main:app --reload      # backend, http://127.0.0.1:8000
cd frontend && npm install && npm run dev    # frontend, http://localhost:5173
```

Vite's dev server proxies `/runs`, `/login`, `/health` to the backend (see
`frontend/vite.config.ts`), so open the frontend URL, not the backend one.
See `frontend/README.md` for details.

For a single-process deployment (one server serving both the API and the
built frontend), see **Deployment** below.

## Project structure

```
agents/
    base.py                 # shared Agent class
    coordinator.py           # routes goal to teams, assembles final report
    research/                # researcher, synthesizer
    leadgen/                 # prospector, qualifier
    content/                 # strategist, writer, critic
    sales/                   # outreach_drafter
orchestration/
    router.py                # keyword-based team routing
    trace.py                 # call/handoff logging; also mirrors agent
                              # start/complete events to Postgres
    run.py                   # entrypoint used by cli.py and api/jobs.py
context/
    business_profile.py      # SynapsesAI brand/ICP/services, shared context
api/
    main.py                  # FastAPI app: PIN auth, serves the built SPA
    db.py                    # Postgres connection (DATABASE_URL)
    models.py                # Run, AgentEvent, Report (SQLAlchemy)
    jobs.py                  # runs orchestration.run as a background job
    migrations/               # Alembic
    routes/
        runs.py               # POST/GET /runs, GET /runs/{id}
        stream.py             # GET /runs/{id}/stream (SSE)
frontend/                    # React (Vite + TS + Tailwind) UI — see frontend/README.md
runs/                        # timestamped output per CLI invocation
cli.py                       # `python cli.py "<goal>"`
railway.toml, nixpacks.toml  # single-service Railway deployment config
```

## Environment variables

Set in `.env` for local dev; set the same names as real environment
variables (not in a `.env` file) when deploying.

| Variable | Required | Notes |
|---|---|---|
| `ANTHROPIC_API_KEY` | Yes | https://console.anthropic.com/settings/keys |
| `ANTHROPIC_MODEL` | No | Overrides the default model for all agents |
| `DATABASE_URL` | Yes (for `api/`) | Postgres connection string. On Railway, provision a Postgres plugin in the same project and reference its `DATABASE_URL` — see Deployment below |
| `APP_PIN` | Yes (for `api/`) | The shared PIN required to sign in. **Use a real value in production** — `.env.example`'s placeholder (`2468`) is for local testing only, never deploy with it |
| `SESSION_SECRET_KEY` | Yes (for `api/`) | Signs the session cookie. Generate one with `python -c "import secrets; print(secrets.token_hex(32))"` — a long random string, not something memorable |
| `SESSION_HTTPS_ONLY` | No | Set to `true` once served over HTTPS (Railway's default domains are HTTPS, so set this to `true` in production) |

## Deployment (Railway, single service)

FastAPI serves both the API and the built React app from one process — no
separate frontend host, no CORS to configure.

1. **Create the Railway project** (or use an existing one) and add a
   Postgres plugin to it if you don't already have one — this provisions
   `DATABASE_URL` automatically as a project-level reference.
2. **Create a service** from this repo (GitHub repo or `railway up` from
   the CLI). Railway will pick up `railway.toml` and `nixpacks.toml`
   automatically:
   - `nixpacks.toml` installs Python + Node, runs `pip install -r requirements.txt`,
     `npm ci` and `npm run build` in `frontend/`.
   - `railway.toml` sets the start command to run `alembic upgrade head`
     (applying any pending migrations) and then start `uvicorn`, plus a
     `/health` healthcheck and an on-failure restart policy.
3. **Set environment variables** on the service (Settings → Variables):
   - `DATABASE_URL` — reference the Postgres plugin's variable (Railway
     lets you reference `${{Postgres.DATABASE_URL}}` from another plugin
     in the same project, rather than hardcoding it)
   - `ANTHROPIC_API_KEY`
   - `APP_PIN` — a real PIN, not `2468`
   - `SESSION_SECRET_KEY` — generate with the command above
   - `SESSION_HTTPS_ONLY=true`
4. **Deploy.** Watch the build logs for the `npm run build` step and the
   `alembic upgrade head` line in the start logs — if either fails, the
   deploy will show it clearly.
5. **Open the service's Railway-provided domain.** You should land on the
   login page; enter `APP_PIN` to get in.

Since this hasn't been deployed to a live Railway project as part of this
work (only verified locally against the exact build/start commands and a
real Postgres instance), watch the first deploy's logs closely — if
Railway's Nixpacks auto-detection behaves differently than expected for a
frontend-in-a-subdirectory repo, `nixpacks.toml`'s explicit phases are what
to adjust.

### Why one process, and how routing collisions are handled

Frontend client-side routes and backend API routes share literal path
prefixes — `GET /runs/{id}` is both the JSON API endpoint *and* the URL of
the React `RunView` page. `api/main.py`'s `SPAFallbackMiddleware` resolves
this the same way `frontend/vite.config.ts`'s dev-proxy `bypass` did in
local dev: by checking the request's `Accept` header. A browser page
navigation (`Accept: text/html`) gets the SPA shell (`frontend/dist/index.html`)
regardless of path, served *before* routing even happens, with
`Cache-Control: no-store` so the browser never reuses that response for a
later JSON `fetch()` to the identical URL. Everything else — the API's own
`fetch()` calls (`Accept: application/json`) and the SSE stream
(`Accept: text/event-stream`) — passes through untouched to the real
routes. `PinAuthMiddleware` then only guards the `/runs` API prefix; the
SPA shell, its static assets, and `/login`/`/health` are always public, so
the app can load and show its own login screen before a session exists.
