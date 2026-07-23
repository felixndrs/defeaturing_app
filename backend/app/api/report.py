from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from ..domain.models import AnalysisRun, GeometryModel, Project
from ..reporting import html_bundle, pdf, screenshots
from ..storage import db

router = APIRouter(prefix="/report", tags=["report"])


def _load_run_project_models(run_id: str) -> tuple[AnalysisRun, Project, GeometryModel, GeometryModel]:
    run = db.load(AnalysisRun, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")
    project = db.load(Project, run.project_id)
    if project is None or not project.original_model_id or not project.defeatured_model_id:
        raise HTTPException(status_code=409, detail="Project models missing")
    original = db.load(GeometryModel, project.original_model_id)
    defeatured = db.load(GeometryModel, project.defeatured_model_id)
    if original is None or defeatured is None:
        raise HTTPException(status_code=409, detail="Models missing")
    return run, project, original, defeatured


@router.get("/{run_id}/pdf")
def get_pdf(run_id: str) -> FileResponse:
    run, project, original, defeatured = _load_run_project_models(run_id)

    for feature in run.features:
        try:
            screenshots.render_feature_views(run.id, feature, original, defeatured)
        except Exception:
            # A rendering failure must not block the report; the PDF simply
            # omits images for that feature.
            continue

    path = pdf.build_report(run, project)
    return FileResponse(path, media_type="application/pdf", filename=f"report_{run_id}.pdf")


@router.get("/{run_id}/bundle")
def get_bundle(run_id: str) -> FileResponse:
    run, project, original, defeatured = _load_run_project_models(run_id)
    path = html_bundle.build_bundle(run, project, original, defeatured)
    return FileResponse(path, media_type="application/zip", filename=f"review_bundle_{run_id}.zip")
