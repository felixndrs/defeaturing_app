"""Job execution.

Runs an analysis and persists the result. Deliberately backed by FastAPI's
BackgroundTasks and the DB, not Celery/Redis: the API contract (POST returns a
run id, GET polls status) is identical to a queue-backed version, so scaling out
later is a change confined to this module.
"""

from __future__ import annotations

import uuid

from ..analysis.pipeline import analyze
from ..config import get_settings
from ..domain.enums import ModelRole, RunStatus
from ..domain.models import AnalysisRun, GeometryModel, Project
from ..importers.step_importer import get_shape
from ..llm import assess_run
from ..storage import db, files


def _ensure_shape(model: GeometryModel, project_id: str):
    """Return the live OCC shape for a model, re-reading the STEP file if the
    in-process cache is cold (e.g. after a restart)."""
    shape = get_shape(model.id)
    if shape is not None:
        return shape
    from ..analysis.context import read_step_shape

    path = files.project_dir(project_id) / model.source_file
    return read_step_shape(path) if path.exists() else None


def create_run(project_id: str) -> AnalysisRun:
    """Create a pending run record so the client has an id to poll immediately."""
    run = AnalysisRun(id=uuid.uuid4().hex, project_id=project_id, status=RunStatus.PENDING)
    db.save(run, parent_id=project_id)
    return run


def execute_run(run_id: str, project_id: str) -> AnalysisRun:
    """Run the full analysis for a project and persist the result."""
    project = db.load(Project, project_id)
    original = db.load(GeometryModel, project.original_model_id) if project else None
    defeatured = db.load(GeometryModel, project.defeatured_model_id) if project else None

    if project is None or original is None or defeatured is None:
        run = AnalysisRun(id=run_id, project_id=project_id, status=RunStatus.FAILED,
                          error="Project or its models not found")
        db.save(run, parent_id=project_id)
        return run

    settings = get_settings()
    result = analyze(
        run_id,
        project_id,
        original,
        defeatured,
        original_shape=_ensure_shape(original, project_id),
        defeatured_shape=_ensure_shape(defeatured, project_id),
        area_rel_tol=settings.pairing_area_rel_tol,
    )

    if result.status is RunStatus.DONE:
        try:
            assess_run(result, original, defeatured)
        except Exception as exc:  # noqa: BLE001 - assessment must never fail the run
            result.error = f"assessment skipped: {type(exc).__name__}: {exc}"

    db.save(result, parent_id=project_id)
    return result
