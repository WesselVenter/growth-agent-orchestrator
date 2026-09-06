import { useEffect, useRef, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import {
  getRun,
  streamRun,
  AuthError,
  type AgentEvent,
  type RunDetail,
  type RunStatus,
} from '../api/client'
import AgentTimeline from '../components/AgentTimeline'
import ReportView from '../components/ReportView'
import StatusBadge from '../components/StatusBadge'

const TERMINAL_STATUSES: RunStatus[] = ['complete', 'failed']

export default function RunView() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()

  const [runDetail, setRunDetail] = useState<RunDetail | null>(null)
  const [status, setStatus] = useState<RunStatus | null>(null)
  const [events, setEvents] = useState<AgentEvent[]>([])
  const [loadError, setLoadError] = useState<string | null>(null)
  const eventSourceRef = useRef<EventSource | null>(null)

  useEffect(() => {
    if (!id) return
    let cancelled = false
    setRunDetail(null)
    setStatus(null)
    setEvents([])
    setLoadError(null)

    getRun(id)
      .then((data) => {
        if (cancelled) return
        setRunDetail(data)
        setStatus(data.status)
      })
      .catch((err) => {
        if (cancelled) return
        if (err instanceof AuthError) {
          navigate('/login', { state: { from: `/runs/${id}` } })
          return
        }
        setLoadError(err instanceof Error ? err.message : 'Failed to load run.')
      })

    // Always open the stream, even for a run that's already finished — the
    // backend flushes the full AgentEvent backlog first, then immediately
    // sends the terminal run_status and closes. This is what populates the
    // full timeline whether you're watching live or opening an old run.
    const source = streamRun(id, {
      onAgentEvent: (ev) => {
        if (!cancelled) setEvents((prev) => [...prev, ev])
      },
      onRunStatus: (newStatus) => {
        if (cancelled) return
        setStatus(newStatus)
        source.close()
        if (TERMINAL_STATUSES.includes(newStatus)) {
          // Re-fetch to pick up the saved Report row now that it exists.
          getRun(id)
            .then((data) => {
              if (!cancelled) setRunDetail(data)
            })
            .catch(() => {})
        }
      },
    })
    eventSourceRef.current = source

    return () => {
      cancelled = true
      source.close()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id])

  if (loadError) {
    return (
      <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
        {loadError}
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div>
        <Link to="/history" className="text-sm text-blue-600 hover:underline">
          ← Back to history
        </Link>
        <div className="mt-1 flex items-center gap-3">
          <h1 className="text-xl font-semibold text-gray-900">
            {runDetail?.goal ?? 'Loading run…'}
          </h1>
          {status && <StatusBadge status={status} />}
        </div>
      </div>

      <section>
        <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide text-gray-500">
          Agent activity
        </h2>
        <AgentTimeline events={events} />
      </section>

      {status === 'failed' && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          This run failed. Check the agent activity above for details.
        </div>
      )}

      {status === 'complete' && runDetail?.report && (
        <section>
          <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide text-gray-500">
            Final report
          </h2>
          <ReportView markdown={runDetail.report} />
        </section>
      )}
    </div>
  )
}
