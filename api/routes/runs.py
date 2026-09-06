"""Routes: POST /runs, GET /runs, GET /runs/{id}."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from api.db import session_scope
from api.jobs import start_background_job
from api.models import Report, Run

router = APIRouter(prefix="/runs", tags=["runs"])


class CreateRunRequest(BaseModel):
    goal: str


class CreateRunResponse(BaseModel):
    run_id: str


class RunSummary(BaseModel):
    id: str
    goal: str
    status: str
    created_at: datetime
    completed_at: datetime | None


class RunDetail(RunSummary):
    report: str | None = None


@router.post("", response_model=CreateRunResponse)
def create_run(payload: CreateRunRequest) -> CreateRunResponse:
    """Create a Run and kick off orchestration in the background.

    Uses start_background_job (the daemon-thread path in api.jobs), which
    is designed for a long-lived host process — FastAPI, running under
    uvicorn, is exactly that, unlike a one-off script.
    """
    if not payload.goal.strip():
        raise HTTPException(status_code=400, detail="goal must not be empty")

    run_id = start_background_job(payload.goal)
    return CreateRunResponse(run_id=run_id)


@router.get("", response_model=list[RunSummary])
def list_runs(limit: int = 50) -> list[RunSummary]:
    with session_scope() as session:
        rows = session.query(Run).order_by(Run.created_at.desc()).limit(limit).all()
        return [
            RunSummary(
                id=r.id,
                goal=r.goal,
                status=r.status.value,
                created_at=r.created_at,
                completed_at=r.completed_at,
            )
            for r in rows
        ]


@router.get("/{run_id}", response_model=RunDetail)
def get_run(run_id: str) -> RunDetail:
    with session_scope() as session:
        run = session.get(Run, run_id)
        if run is None:
            raise HTTPException(status_code=404, detail="Run not found")

        report = session.query(Report).filter_by(run_id=run_id).first()
        return RunDetail(
            id=run.id,
            goal=run.goal,
            status=run.status.value,
            created_at=run.created_at,
            completed_at=run.completed_at,
            report=report.markdown_content if report else None,
        )
