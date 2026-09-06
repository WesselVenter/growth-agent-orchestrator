import { useMemo, useState } from 'react'
import type { AgentEvent } from '../api/client'

const SUMMARY_TRUNCATE_LENGTH = 150

interface TimelineItem {
  key: string
  agentName: string
  startedAt: string
  completedAt?: string
  durationMs?: number | null
  outputSummary?: string | null
}

/**
 * The backend logs a "started" AgentEvent row and, separately, a
 * "completed" one for each agent call. Pair them up into one timeline
 * entry per call. The orchestrator runs strictly sequentially (no
 * concurrent agents), and the same agent_name can legitimately appear
 * multiple times in one run (e.g. writer/critic revision passes), so we
 * match each "completed" to the oldest still-open "started" for that same
 * agent_name (FIFO per name) rather than assuming names are unique.
 */
function buildTimeline(events: AgentEvent[]): TimelineItem[] {
  const items: TimelineItem[] = []
  const openByAgent = new Map<string, TimelineItem[]>()

  for (const ev of events) {
    if (ev.status === 'started') {
      const item: TimelineItem = {
        key: `${ev.agent_name}-${ev.id}`,
        agentName: ev.agent_name,
        startedAt: ev.timestamp,
      }
      items.push(item)
      const queue = openByAgent.get(ev.agent_name) ?? []
      queue.push(item)
      openByAgent.set(ev.agent_name, queue)
    } else {
      const queue = openByAgent.get(ev.agent_name)
      const item = queue?.shift()
      if (item) {
        item.completedAt = ev.timestamp
        item.durationMs = ev.duration_ms
        item.outputSummary = ev.output_summary
      } else {
        // A "completed" with no matching open "started" shouldn't happen
        // in practice, but render it standalone rather than dropping it.
        items.push({
          key: `${ev.agent_name}-${ev.id}`,
          agentName: ev.agent_name,
          startedAt: ev.timestamp,
          completedAt: ev.timestamp,
          durationMs: ev.duration_ms,
          outputSummary: ev.output_summary,
        })
      }
    }
  }

  return items
}

function formatDuration(ms?: number | null): string {
  if (ms == null) return ''
  if (ms < 1000) return `${ms}ms`
  return `${(ms / 1000).toFixed(1)}s`
}

/**
 * output_summary can be very long markdown — a full prospector or
 * coordinator output easily runs several hundred words. Never render the
 * full text inline in the timeline; truncate to ~150 characters as plain
 * text with a "show more" toggle. (The final report gets its own proper
 * markdown rendering in ReportView — this is just a live-progress glance.)
 */
function TruncatedSummary({ text }: { text: string }) {
  const [expanded, setExpanded] = useState(false)
  const isLong = text.length > SUMMARY_TRUNCATE_LENGTH

  if (!isLong) {
    return <p className="text-sm text-gray-600 whitespace-pre-wrap break-words">{text}</p>
  }

  return (
    <div className="text-sm text-gray-600">
      <p className="whitespace-pre-wrap break-words">
        {expanded ? text : text.slice(0, SUMMARY_TRUNCATE_LENGTH).trimEnd() + '…'}
      </p>
      <button
        type="button"
        onClick={() => setExpanded((v) => !v)}
        className="mt-1 text-xs font-medium text-blue-600 hover:underline"
      >
        {expanded ? 'Show less' : 'Show more'}
      </button>
    </div>
  )
}

function Spinner() {
  return (
    <span className="inline-block h-4 w-4 shrink-0 animate-spin rounded-full border-2 border-gray-300 border-t-blue-600" />
  )
}

function CheckIcon() {
  return (
    <span className="flex h-4 w-4 shrink-0 items-center justify-center rounded-full bg-green-100 text-green-700">
      <svg viewBox="0 0 16 16" fill="currentColor" className="h-3 w-3">
        <path d="M13.5 4.5 6.5 11.5 2.5 7.5l1-1 3 3 6-6z" />
      </svg>
    </span>
  )
}

export default function AgentTimeline({ events }: { events: AgentEvent[] }) {
  const items = useMemo(() => buildTimeline(events), [events])

  if (items.length === 0) {
    return <p className="text-sm text-gray-400">Waiting for the first agent to start…</p>
  }

  return (
    <ol className="space-y-3">
      {items.map((item) => {
        const isComplete = Boolean(item.completedAt)
        return (
          <li key={item.key} className="flex gap-3 rounded-lg border bg-white p-3 shadow-sm">
            <div className="pt-0.5">{isComplete ? <CheckIcon /> : <Spinner />}</div>
            <div className="min-w-0 flex-1">
              <div className="flex items-baseline gap-2">
                <span className="font-medium text-gray-900">{item.agentName}</span>
                {isComplete ? (
                  <span className="text-xs text-gray-400">{formatDuration(item.durationMs)}</span>
                ) : (
                  <span className="text-xs text-gray-400">running…</span>
                )}
              </div>
              {item.outputSummary && <TruncatedSummary text={item.outputSummary} />}
            </div>
          </li>
        )
      })}
    </ol>
  )
}
