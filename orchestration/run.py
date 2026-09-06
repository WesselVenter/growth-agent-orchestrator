"""Entrypoint: goal in -> Router selects teams -> teams run -> report out.

Runs the Router to decide which teams a goal needs, hands that to the
Coordinator to execute in dependency order (Research feeds Content; Lead Gen
feeds Sales), and saves the final report + full trace to a timestamped
folder under runs/.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from agents.coordinator import Coordinator
from orchestration.router import route
from orchestration.trace import Trace

RUNS_DIR = Path(__file__).resolve().parent.parent / "runs"


def run(goal: str, trace: Trace | None = None) -> tuple[str, Trace]:
    """Run the full orchestrator on a goal. Returns (report, trace).

    Pass an existing `trace` (e.g. from api.jobs, which needs the Trace's
    run_id to exist as a Run row in Postgres before any agent starts
    writing AgentEvents against it) to reuse it instead of creating a new
    one.
    """
    trace = trace or Trace()

    teams = route(goal)
    trace.log_handoff("router", "coordinator", f"teams selected for goal: {', '.join(teams)}")

    coordinator = Coordinator()
    report = coordinator.run(goal, teams, trace)
    return report, trace


def run_and_save(goal: str) -> Path:
    """Run the orchestrator and save goal/report/trace under a timestamped
    runs/<timestamp>_<run_id>/ folder. Returns that folder's path."""
    report, trace = run(goal)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    run_dir = RUNS_DIR / f"{timestamp}_{trace.run_id}"
    run_dir.mkdir(parents=True, exist_ok=True)

    (run_dir / "goal.txt").write_text(goal, encoding="utf-8")
    (run_dir / "report.md").write_text(report, encoding="utf-8")
    trace.save(run_dir / "trace.json")

    return run_dir
