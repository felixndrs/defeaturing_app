from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from ..domain.models import GeometryModel
from ..storage import db, files

router = APIRouter(prefix="/geometry", tags=["geometry"])


@router.get("/{model_id}.glb")
def get_geometry(model_id: str) -> FileResponse:
    """Serve the tessellated model as GLB, with one scene node per face id."""
    if db.load(GeometryModel, model_id) is None:
        raise HTTPException(status_code=404, detail="Model not found")

    path = files.geometry_path(model_id)
    if not path.exists():
        # The GLB is written at import time; a missing file means the artifact
        # was cleared. Rebuilding needs the OCC shape, which we do not persist.
        raise HTTPException(status_code=409, detail="Geometry artifact missing; re-import the model")

    return FileResponse(path, media_type="model/gltf-binary", filename=f"{model_id}.glb")
