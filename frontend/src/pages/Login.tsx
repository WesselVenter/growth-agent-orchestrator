import { useState, type FormEvent } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { login } from '../api/client'

/**
 * Matches the backend's own server-rendered login page (api/main.py), but
 * as a React form. It POSTs the PIN to the real /login route and relies
 * entirely on the resulting session cookie — there is no client-side PIN
 * check or auth state here beyond "did the backend accept it".
 */
export default function Login() {
  const [pin, setPin] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()
  const location = useLocation()

  const from = (location.state as { from?: string } | null)?.from ?? '/history'

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setLoading(true)
    setError(null)
    try {
      const ok = await login(pin)
      if (ok) {
        navigate(from, { replace: true })
      } else {
        setError('Incorrect PIN.')
      }
    } catch {
      setError('Could not reach the server.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-100">
      <form onSubmit={handleSubmit} className="w-72 space-y-4 rounded-lg bg-white p-8 shadow">
        <h1 className="text-lg font-semibold text-gray-800">Enter PIN</h1>
        {error && <p className="text-sm text-red-600">{error}</p>}
        <input
          type="password"
          value={pin}
          onChange={(e) => setPin(e.target.value)}
          placeholder="PIN"
          autoFocus
          className="w-full rounded border px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
        />
        <button
          type="submit"
          disabled={loading || pin.length === 0}
          className="w-full rounded bg-blue-600 px-3 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
        >
          {loading ? 'Signing in…' : 'Sign in'}
        </button>
      </form>
    </div>
  )
}
