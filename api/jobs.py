"""Background job runner: executes orchestration.run's pipeline for a goal
as a background task, tracking progress in Postgres via the Run and Report
tables.

Usage:
    from api.jobs import start_background_job

    run_id = start_background_job("find 10 leads in the legal sector, Gauteng")
    # run_id is available immediately; the goal keeps running on a thread.
    # Poll the `runs` table (or `agent_events` for live progress) for status.

    # Or run synchronously (e.g. from a script, or a worker process that's
    # already off the request thread):
    from api.jobs import run_goal_job
    run_id = run_goal_job("find 10 leads in the legal sector, Gauteng")
"""

from __future__ import annotations

import threading
import traceback
from datetime import datetime, timezone

from api.db import session_scope
from api.models import Report, Run, RunStatus
from orchestration.run import run as run_orchestrator
from orchestration.trace import Trace


def run_goal_job(goal: str) -> str:
    """Run the full orchestrator for `goal` synchronously, tracking status
    in Postgres as it goes. Returns the run_id (the Run row's primary key
    and the Trace's run_id) once the run has finished (or raises, after
    marking the Run failed)."""
    trace = Trace()
    run_id = trace.run_id

    with session_scope() as session:
        session.add(Run(id=run_id, goal=goal, status=RunStatus.pending))

    _execute(goal, trace)
    return run_id


def start_background_job(goal: str) -> str:
    """Kick off run_goal_job's work on a background thread and return the
    run_id immediately, before the run has finished. Progress can be
    observed live via the `runs`/`agent_events` tables as the orchestrator
    executes."""
    trace = Trace()
    run_id = trace.run_id

    with session_scope() as session:
        session.add(Run(id=run_id, goal=goal, status=RunStatus.pending))

    def _target() -> None:
        try:
            _execute(goal, trace)
        except Exception:
            pass  # already logged and reflected in Run.status by _execute

    threading.Thread(target=_target, daemon=True, name=f"run-{run_id}").start()
    return run_id


def _execute(goal: str, trace: Trace) -> None:
    """Shared by run_goal_job and start_background_job: transitions the Run
    row through running -> complete/failed, saving the Report on success."""
    run_id = trace.run_id
    _set_status(run_id, RunStatus.running)

    try:
        report, trace = run_orchestrator(goal, trace=trace)
    except Exception:
        print(f"[jobs] run {run_id} failed:\n{traceback.format_exc()}")
        _set_status(run_id, RunStatus.failed, completed=True)
        raise

    with session_scope() as session:
        session.add(Report(run_id=run_id, markdown_content=report))

    _set_status(run_id, RunStatus.complete, completed=True)


def _set_status(run_id: str, status: RunStatus, completed: bool = False) -> None:
    with session_scope() as session:
        db_run = session.get(Run, run_id)
        if db_run is None:
            return
        db_run.status = status
        if completed:
            db_run.completed_at = datetime.now(timezone.utc)
