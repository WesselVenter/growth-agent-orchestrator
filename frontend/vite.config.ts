import type { IncomingMessage } from 'node:http'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import { defineConfig, type ProxyOptions } from 'vite'

// Proxy API calls to the FastAPI backend so the browser sees everything as
// one origin (http://localhost:5173) — this is what makes the PIN-auth
// session cookie work without any CORS/SameSite gymnastics: the backend's
// cookie is set for "this origin" and every request (including the SSE
// stream) genuinely is same-origin from the browser's point of view.
const BACKEND_URL = 'http://127.0.0.1:8000'

// The SPA's client-side routes (/runs/:id, /login) share a literal path
// prefix with real backend REST routes (GET /runs/{id}, GET/POST /login).
// Client-side <Link> navigation never hits this proxy at all (no new HTTP
// request), so it isn't visible in normal in-app use — but a hard
// navigation (typed URL, refresh, bookmark) for those same paths *does*
// hit the dev server directly, and without this bypass it would get
// proxied straight to the backend's JSON/HTML instead of serving the SPA.
// Browsers send `Accept: text/html` for page navigations but not for our
// fetch()/EventSource calls, so that header is what tells them apart.
function bypassPageNavigation(req: IncomingMessage): string | null | undefined {
  const accept = req.headers.accept ?? ''
  if (accept.includes('text/html')) {
    return req.url // non-null return = "don't proxy, let Vite serve the SPA for this"
  }
  return undefined // let the proxy handle it
}

const proxied: ProxyOptions = { target: BACKEND_URL, changeOrigin: true, bypass: bypassPageNavigation }

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    proxy: {
      '/runs': proxied,
      '/login': proxied,
      '/health': proxied,
    },
  },
})
