from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from ..domain.enums import ModelRole
from ..domain.models import GeometryModel, Project
from ..importers import UnsupportedFormatError, load_model, supported_extensions
from ..importers.base import ImportError_
from ..storage import db, files

router = APIRouter(prefix="/projects", tags=["projects"])


class ModelSummary(BaseModel):
    id: str
    role: ModelRole
    source_file: str
    source_format: str
    solid_count: int
    face_count: int
    edge_count: int
    volume: float
    area: float

    @classmethod
    def of(cls, m: GeometryModel) -> "ModelSummary":
        return cls(
            id=m.id,
            role=m.role,
            source_file=m.source_file,
            source_format=m.source_format.value,
            solid_count=len(m.solids),
            face_count=len(m.faces),
            edge_count=len(m.edges),
            volume=m.volume,
            area=m.area,
        )


class ProjectDetail(BaseModel):
    id: str
    name: str
    original: ModelSummary | None = None
    defeatured: ModelSummary | None = None


@router.get("/supported-formats")
def formats() -> dict[str, list[str]]:
    return {"extensions": supported_extensions()}


@router.post("", response_model=ProjectDetail, status_code=201)
async def create_project(
    name: str = Form(...),
    original: UploadFile = File(...),
    defeatured: UploadFile = File(...),
) -> ProjectDetail:
    project_id = uuid.uuid4().hex
    project = Project(id=project_id, name=name)

    summaries: dict[ModelRole, ModelSummary] = {}
    for role, upload in ((ModelRole.ORIGINAL, original), (ModelRole.DEFEATURED, defeatured)):
        path = files.save_upload(project_id, upload.filename or f"{role.value}.step", upload.file)
        model = _import(path, role)
        db.save(model, parent_id=project_id)
        summaries[role] = ModelSummary.of(model)
        if role is ModelRole.ORIGINAL:
            project.original_model_id = model.id
        else:
            project.defeatured_model_id = model.id

    db.save(project)
    return ProjectDetail(
        id=project.id,
        name=project.name,
        original=summaries[ModelRole.ORIGINAL],
        defeatured=summaries[ModelRole.DEFEATURED],
    )


def _import(path: Path, role: ModelRole) -> GeometryModel:
    model_id = uuid.uuid4().hex
    try:
        return load_model(path, role, model_id)
    except UnsupportedFormatError as exc:
        raise HTTPException(status_code=415, detail=str(exc)) from exc
    except ImportError_ as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("", response_model=list[ProjectDetail])
def list_projects() -> list[ProjectDetail]:
    return [_detail(p) for p in db.load_all(Project)]


@router.get("/{project_id}", response_model=ProjectDetail)
def get_project(project_id: str) -> ProjectDetail:
    project = db.load(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return _detail(project)


def _detail(project: Project) -> ProjectDetail:
    def summary(model_id: str | None) -> ModelSummary | None:
        if not model_id:
            return None
        model = db.load(GeometryModel, model_id)
        return ModelSummary.of(model) if model else None

    return ProjectDetail(
        id=project.id,
        name=project.name,
        original=summary(project.original_model_id),
        defeatured=summary(project.defeatured_model_id),
    )
