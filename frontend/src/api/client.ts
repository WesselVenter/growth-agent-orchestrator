// Thin wrapper around the backend's REST + SSE API. Auth is entirely
// session-cookie based (set by the real POST /login route) — nothing here
// stores or checks the PIN itself; we just react to 401s and redirects.

export type RunStatus = 'pending' | 'running' | 'complete' | 'failed'

export interface RunSummary {
  id: string
  goal: string
  status: RunStatus
  created_at: string
  completed_at: string | null
}

export interface RunDetail extends RunSummary {
  report: string | null
}

export type AgentEventStatus = 'started' | 'completed'

export interface AgentEvent {
  id: number
  agent_name: string
  status: AgentEventStatus
  input_summary: string | null
  output_summary: string | null
  duration_ms: number | null
  timestamp: string
}

export class AuthError extends Error {
  constructor() {
    super('Not authenticated')
    this.name = 'AuthError'
  }
}

async function apiFetch(path: string, init?: RequestInit): Promise<Response> {
  // Explicit Accept (never text/html) is what tells the dev proxy's bypass
  // this is an API call, not a page navigation — see vite.config.ts.
  const res = await fetch(path, {
    credentials: 'include',
    ...init,
    headers: { Accept: 'application/json', ...init?.headers },
  })
  if (res.status === 401) throw new AuthError()
  return res
}

/**
 * Checks whether the current session is authenticated, without triggering
 * the backend's redirect-to-login behavior. We ask for a real protected
 * resource (GET /runs) with redirect: 'manual' — an authenticated session
 * gets a normal 200 JSON response; an unauthenticated one gets a 303 that
 * `manual` mode surfaces as an opaque redirect (status 0, type
 * 'opaqueredirect') instead of silently following it into an HTML page.
 */
export async function checkAuth(): Promise<boolean> {
  const res = await fetch('/runs', {
    credentials: 'include',
    redirect: 'manual',
    headers: { Accept: 'application/json' },
  })
  if (res.type === 'opaqueredirect') return false
  return res.status !== 401
}

/**
 * Logs in via the real backend route (POST /login, form-encoded, exactly
 * like the server-rendered login page does) and lets the resulting
 * Set-Cookie session do the work — no client-side auth logic beyond
 * checking whether it succeeded.
 *
 * `next` is set to /health (a public, always-200 route) purely so we can
 * detect success unambiguously: fetch() follows the backend's 303
 * redirect on success, and the final response status tells us whether
 * that landed on a real page (200) rather than another 401.
 */
export async function login(pin: string): Promise<boolean> {
  const res = await fetch('/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: new URLSearchParams({ pin, next: '/health' }),
    credentials: 'include',
  })
  return res.ok
}

export async function createRun(goal: string): Promise<{ run_id: string }> {
  const res = await apiFetch('/runs', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ goal }),
  })
  if (!res.ok) {
    const body = await res.json().catch(() => null)
    throw new Error(body?.detail ?? `Failed to create run (${res.status})`)
  }
  return res.json()
}

export async function listRuns(): Promise<RunSummary[]> {
  const res = await apiFetch('/runs')
  if (!res.ok) throw new Error(`Failed to list runs (${res.status})`)
  return res.json()
}

export async function getRun(id: string): Promise<RunDetail> {
  const res = await apiFetch(`/runs/${id}`)
  if (res.status === 404) throw new Error('Run not found')
  if (!res.ok) throw new Error(`Failed to load run (${res.status})`)
  return res.json()
}

/**
 * Opens the SSE stream for a run. Returns the EventSource so the caller
 * controls its lifecycle (close it on unmount). Expects two event types
 * from the backend: "agent_event" (an AgentEvent) and "run_status"
 * ({status}), the latter sent once right before the server closes the
 * stream.
 */
export function streamRun(
  runId: string,
  handlers: {
    onAgentEvent: (event: AgentEvent) => void
    onRunStatus: (status: RunStatus) => void
    onError?: () => void
  },
): EventSource {
  const source = new EventSource(`/runs/${runId}/stream`, { withCredentials: true })

  source.addEventListener('agent_event', (e) => {
    handlers.onAgentEvent(JSON.parse((e as MessageEvent).data))
  })
  source.addEventListener('run_status', (e) => {
    const data = JSON.parse((e as MessageEvent).data) as { status: RunStatus }
    handlers.onRunStatus(data.status)
  })
  source.addEventListener('error', () => {
    handlers.onError?.()
  })

  return source
}
