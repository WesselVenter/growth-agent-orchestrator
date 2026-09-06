import { useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { createRun, AuthError } from '../api/client'

export default function NewRun() {
  const [goal, setGoal] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const navigate = useNavigate()

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    if (!goal.trim()) return

    setSubmitting(true)
    setError(null)
    try {
      const { run_id } = await createRun(goal.trim())
      navigate(`/runs/${run_id}`)
    } catch (err) {
      if (err instanceof AuthError) {
        navigate('/login', { state: { from: '/new' } })
        return
      }
      setError(err instanceof Error ? err.message : 'Failed to start run.')
      setSubmitting(false)
    }
  }

  return (
    <div className="mx-auto max-w-xl">
      <h1 className="mb-4 text-xl font-semibold text-gray-900">Start a new run</h1>
      <form onSubmit={handleSubmit} className="space-y-3 rounded-lg border bg-white p-5 shadow-sm">
        <label htmlFor="goal" className="block text-sm font-medium text-gray-700">
          Goal
        </label>
        <textarea
          id="goal"
          value={goal}
          onChange={(e) => setGoal(e.target.value)}
          rows={3}
          placeholder='e.g. "find 10 leads in the legal sector, Gauteng"'
          className="w-full resize-none rounded border px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
        />
        {error && <p className="text-sm text-red-600">{error}</p>}
        <button
          type="submit"
          disabled={submitting || !goal.trim()}
          className="rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
        >
          {submitting ? 'Starting…' : 'Start run'}
        </button>
      </form>
    </div>
  )
}
