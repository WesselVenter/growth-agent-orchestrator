"""Shared trace object: records every agent call and handoff with timestamps.

In addition to the local in-memory record (still saved to trace.json), each
agent start and completion is mirrored to Postgres in real time as an
api.models.AgentEvent row, so a run's progress can be observed live rather
than only after the run finishes. DB writes are best-effort: if the api
package or a database connection isn't available (e.g. running a team test
script standalone, no DATABASE_URL configured), failures are logged and
swallowed rather than breaking the agent run.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_INPUT_OUTPUT_SUMMARY_LIMIT = 4000


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _truncate(text: str, limit: int = _INPUT_OUTPUT_SUMMARY_LIMIT) -> str:
    return text if len(text) <= limit else text[: limit - 1] + "…"


@dataclass
class ToolCallRecord:
    name: str
    input: dict[str, Any]


@dataclass
class AgentCallRecord:
    agent_name: str
    started_at: str
    ended_at: str
    duration_seconds: float
    input: str
    output: str
    tool_calls: list[ToolCallRecord] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "agent_name": self.agent_name,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "duration_seconds": self.duration_seconds,
            "input": self.input,
            "output": self.output,
            "tool_calls": [
                {"name": tc.name, "input": tc.input} for tc in self.tool_calls
            ],
        }


@dataclass
class HandoffRecord:
    from_agent: str
    to_agent: str
    reason: str
    timestamp: str = field(default_factory=now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "from_agent": self.from_agent,
            "to_agent": self.to_agent,
            "reason": self.reason,
            "timestamp": self.timestamp,
        }


class Trace:
    """Accumulates agent calls and handoffs for a single orchestrator run,
    and mirrors agent start/complete events to Postgres in real time."""

    def __init__(self, run_id: str | None = None) -> None:
        self.run_id = run_id or uuid.uuid4().hex[:8]
        self.started_at = now_iso()
        self.calls: list[AgentCallRecord] = []
        self.handoffs: list[HandoffRecord] = []

    def start_call(self, agent_name: str, user_input: str) -> None:
        """Call the moment an agent call begins (before the model call is
        made), so its 'started' state is visible in Postgres immediately."""
        self._write_agent_event(
            agent_name=agent_name,
            status="started",
            input_summary=_truncate(user_input),
            output_summary=None,
            duration_ms=None,
        )

    def log_call(self, record: AgentCallRecord) -> None:
        """Call once an agent call finishes: appends to the local record
        and mirrors a 'completed' AgentEvent to Postgres."""
        self.calls.append(record)
        self._write_agent_event(
            agent_name=record.agent_name,
            status="completed",
            input_summary=_truncate(record.input),
            output_summary=_truncate(record.output),
            duration_ms=round(record.duration_seconds * 1000),
        )

    def log_handoff(self, from_agent: str, to_agent: str, reason: str) -> None:
        self.handoffs.append(HandoffRecord(from_agent, to_agent, reason))

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "started_at": self.started_at,
            "calls": [c.to_dict() for c in self.calls],
            "handoffs": [h.to_dict() for h in self.handoffs],
        }

    def save(self, path: str | Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")

    def _write_agent_event(
        self,
        *,
        agent_name: str,
        status: str,
        input_summary: str | None,
        output_summary: str | None,
        duration_ms: int | None,
    ) -> None:
        try:
            from api.db import session_scope
            from api.models import AgentEvent
        except Exception:
            # api package / DB deps not installed or importable — local
            # trace still works standalone (e.g. team test scripts).
            return

        try:
            with session_scope() as session:
                session.add(
                    AgentEvent(
                        run_id=self.run_id,
                        agent_name=agent_name,
                        status=status,
                        input_summary=input_summary,
                        output_summary=output_summary,
                        duration_ms=duration_ms,
                    )
                )
        except Exception as exc:
            # Telemetry must never break an agent run.
            print(f"[trace] failed to write AgentEvent for {agent_name} ({status}): {exc}")
