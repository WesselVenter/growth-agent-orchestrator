import { useEffect, useState } from 'react'
import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { checkAuth } from '../api/client'

/**
 * Gates its child routes behind a real session check against the backend
 * (see checkAuth). We deliberately verify this *before* rendering any
 * protected page — in particular before RunView opens its EventSource —
 * since an unauthenticated SSE request would hit the backend's
 * redirect-to-login response, which EventSource can't parse as an event
 * stream and would just retry forever.
 */
export default function ProtectedRoute() {
  const [status, setStatus] = useState<'checking' | 'authed' | 'unauthed'>('checking')
  const location = useLocation()

  useEffect(() => {
    let cancelled = false
    setStatus('checking')
    checkAuth().then((ok) => {
      if (!cancelled) setStatus(ok ? 'authed' : 'unauthed')
    })
    return () => {
      cancelled = true
    }
  }, [location.pathname])

  if (status === 'checking') {
    return <div className="p-8 text-sm text-gray-500">Loading…</div>
  }
  if (status === 'unauthed') {
    return <Navigate to="/login" state={{ from: location.pathname }} replace />
  }
  return <Outlet />
}
