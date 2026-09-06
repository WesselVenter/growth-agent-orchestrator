"""SQLAlchemy models for run history: Run, AgentEvent, Report."""

from __future__ import annotations

import enum
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class RunStatus(str, enum.Enum):
    pending = "pending"
    running = "running"
    complete = "complete"
    failed = "failed"


class AgentEventStatus(str, enum.Enum):
    started = "started"
    completed = "completed"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Run(Base):
    """One orchestrator invocation: a goal, its lifecycle status, and timing."""

    __tablename__ = "runs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    goal: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[RunStatus] = mapped_column(
        Enum(RunStatus, name="run_status"), nullable=False, default=RunStatus.pending
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    events: Mapped[list["AgentEvent"]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )
    report: Mapped["Report | None"] = relationship(
        back_populates="run", cascade="all, delete-orphan", uselist=False
    )


class AgentEvent(Base):
    """One agent lifecycle event (started or completed) within a Run.

    Written the moment an agent call begins and again the moment it ends,
    so a run's progress can be observed live rather than only after the
    fact via the local Trace/trace.json.
    """

    __tablename__ = "agent_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(String(64), ForeignKey("runs.id"), nullable=False, index=True)
    agent_name: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[AgentEventStatus] = mapped_column(
        Enum(AgentEventStatus, name="agent_event_status"), nullable=False
    )
    input_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    output_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )

    run: Mapped["Run"] = relationship(back_populates="events")


class Report(Base):
    """The final assembled Markdown report for a Run. One per Run."""

    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("runs.id"), nullable=False, unique=True
    )
    markdown_content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )

    run: Mapped["Run"] = relationship(back_populates="report")
