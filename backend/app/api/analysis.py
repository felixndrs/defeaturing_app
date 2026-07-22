from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel

from ..domain.models import AnalysisRun, Project
from ..storage import db
from ..tasks import worker

router = APIRouter(prefix="/analysis", tags=["analysis"])


class StartRequest(BaseModel):
    project_id: str


class RunSummary(BaseModel):
    id: str
    project_id: str
    status: str
    progress: float
    feature_count: int
    error: str = ""

    @classmethod
    def of(cls, run: AnalysisRun) -> "RunSummary":
        return cls(
            id=run.id,
            project_id=run.project_id,
            status=run.status.value,
            progress=run.progress,
            feature_count=len(run.features),
            error=run.error,
        )


@router.post("", status_code=202, response_model=RunSummary)
def start_analysis(body: StartRequest, background: BackgroundTasks) -> RunSummary:
    if db.load(Project, body.project_id) is None:
        raise HTTPException(status_code=404, detail="Project not found")
    run = worker.create_run(body.project_id)
    background.add_task(worker.execute_run, run.id, body.project_id)
    return RunSummary.of(run)


@router.get("/{run_id}", response_model=AnalysisRun)
def get_run(run_id: str) -> AnalysisRun:
    run = db.load(AnalysisRun, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return run


@router.get("", response_model=list[RunSummary])
def list_runs(project_id: str) -> list[RunSummary]:
    return [RunSummary.of(r) for r in db.load_all(AnalysisRun, parent_id=project_id)]
