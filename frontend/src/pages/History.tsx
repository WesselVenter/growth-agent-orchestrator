import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { listRuns, AuthError, type RunSummary } from '../api/client'
import StatusBadge from '../components/StatusBadge'

export default function History() {
  const [runs, setRuns] = useState<RunSummary[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const navigate = useNavigate()

  async function load() {
    setError(null)
    try {
      setRuns(await listRuns())
    } catch (err) {
      if (err instanceof AuthError) {
        navigate('/login', { state: { from: '/history' } })
        return
      }
      setError(err instanceof Error ? err.message : 'Failed to load runs.')
    }
  }

  useEffect(() => {
    load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  return (
    <div>
      <div className="mb-4 flex items-center justify-between">
        <h1 className="text-xl font-semibold text-gray-900">Past runs</h1>
        <button
          onClick={load}
          className="rounded border px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-100"
        >
          Refresh
        </button>
      </div>

      {error && <p className="text-sm text-red-600">{error}</p>}

      {runs === null && !error && <p className="text-sm text-gray-400">Loading…</p>}

      {runs !== null && runs.length === 0 && (
        <p className="text-sm text-gray-400">
          No runs yet. <Link to="/new" className="text-blue-600 hover:underline">Start one.</Link>
        </p>
      )}

      {runs !== null && runs.length > 0 && (
        <ul className="divide-y rounded-lg border bg-white shadow-sm">
          {runs.map((run) => (
            <li key={run.id}>
              <Link
                to={`/runs/${run.id}`}
                className="flex items-center justify-between gap-4 px-4 py-3 hover:bg-gray-50"
              >
                <div className="min-w-0">
                  <p className="truncate text-sm font-medium text-gray-900">{run.goal}</p>
                  <p className="text-xs text-gray-400">
                    {new Date(run.created_at).toLocaleString()}
                  </p>
                </div>
                <StatusBadge status={run.status} />
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
