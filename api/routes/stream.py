"""SSE endpoint: GET /runs/{id}/stream.

Polls Postgres for new AgentEvent rows belonging to a run and streams them
to the client as Server-Sent Events as they're inserted, closing the stream
once the run's status becomes complete/failed.

Deliberately does NOT try to share in-memory state with the background job
thread (api.jobs) — the SSE request handler and that thread are logically
separate and may even end up on different workers in some deployments.
Postgres is the single source of truth connecting them: the thread writes
AgentEvent rows as agents run, and this endpoint just polls for rows newer
than the last one it sent.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from starlette.concurrency import run_in_threadpool

from api.db import session_scope
from api.models import AgentEvent, Run

router = APIRouter(prefix="/runs", tags=["stream"])

POLL_INTERVAL_SECONDS = 0.75
TERMINAL_STATUSES = {"complete", "failed"}


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


def _poll(run_id: str, since_id: int) -> tuple[str | None, list[dict], int]:
    """Sync DB call, run off the event loop via run_in_threadpool. Returns
    (run_status_or_None_if_run_missing, new_events_as_dicts, new_since_id)."""
    with session_scope() as session:
        run = session.get(Run, run_id)
        if run is None:
            return None, [], since_id

        new_events = (
            session.query(AgentEvent)
            .filter(AgentEvent.run_id == run_id, AgentEvent.id > since_id)
            .order_by(AgentEvent.id)
            .all()
        )
        events_data = [
            {
                "id": e.id,
                "agent_name": e.agent_name,
                "status": e.status.value,
                "input_summary": e.input_summary,
                "output_summary": e.output_summary,
                "duration_ms": e.duration_ms,
                "timestamp": e.timestamp.isoformat(),
            }
            for e in new_events
        ]
        new_since_id = events_data[-1]["id"] if events_data else since_id
        return run.status.value, events_data, new_since_id


async def _event_stream(run_id: str, request: Request) -> AsyncIterator[str]:
    since_id = 0

    while True:
        if await request.is_disconnected():
            return

        status, events_data, since_id = await run_in_threadpool(_poll, run_id, since_id)

        if status is None:
            yield _sse("error", {"detail": "run not found"})
            return

        for ev in events_data:
            yield _sse("agent_event", ev)

        if status in TERMINAL_STATUSES:
            yield _sse("run_status", {"status": status})
            return

        await asyncio.sleep(POLL_INTERVAL_SECONDS)


@router.get("/{run_id}/stream")
async def stream_run(run_id: str, request: Request) -> StreamingResponse:
    return StreamingResponse(
        _event_stream(run_id, request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            # Disable proxy buffering (nginx and similar) so events flush immediately.
            "X-Accel-Buffering": "no",
        },
    )
