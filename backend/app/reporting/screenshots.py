"""Offscreen renders of a feature: Original, Defeatured, and Overlay.

Loads the same GLB the 3D viewer uses (one node per face id), so a screenshot
and the browser view are guaranteed to agree. All three images share one camera
pose -- computed from the feature's bounding box -- so a reviewer can flip
between them in the PDF without the geometry appearing to jump.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pyvista as pv
import trimesh

from ..domain.models import FeatureChange, GeometryModel
from ..storage import files

pv.OFF_SCREEN = True

HIGHLIGHT_COLOR = "#f59e0b"
BASE_COLOR = "#8b93a1"
WINDOW_SIZE = (640, 480)


def _load_polydata(model_id: str) -> tuple[pv.PolyData, dict[str, np.ndarray]]:
    """Return the whole model as one PolyData plus a per-face-id cell mask."""
    scene = trimesh.load(files.geometry_path(model_id), file_type="glb")
    meshes: list[pv.PolyData] = []
    masks: dict[str, tuple[int, int]] = {}
    offset = 0
    for name, geom in scene.geometry.items():
        n_faces = len(geom.faces)
        if n_faces == 0:
            continue
        pd = pv.wrap(geom)
        meshes.append(pd)
        masks[name] = (offset, offset + n_faces)
        offset += n_faces
    combined = meshes[0].merge(meshes[1:]) if len(meshes) > 1 else meshes[0]
    return combined, masks


def _camera_pose(bbox_min: np.ndarray, bbox_max: np.ndarray) -> dict:
    center = (bbox_min + bbox_max) / 2
    diag = float(np.linalg.norm(bbox_max - bbox_min)) or 1.0
    eye = center + np.array([1.0, -1.2, 0.9]) * diag * 1.4
    return {"position": tuple(eye), "focal_point": tuple(center), "viewup": (0, 0, 1)}


def _render(
    model_id: str, highlight_ids: set[str], bbox_min: np.ndarray, bbox_max: np.ndarray
) -> np.ndarray:
    mesh, masks = _load_polydata(model_id)
    plotter = pv.Plotter(off_screen=True, window_size=WINDOW_SIZE)
    plotter.set_background("white")
    plotter.add_mesh(mesh, color=BASE_COLOR, smooth_shading=True)

    for fid in highlight_ids:
        span = masks.get(fid)
        if span is None:
            continue
        start, end = span
        sub = mesh.extract_cells(np.arange(start, end))
        plotter.add_mesh(sub, color=HIGHLIGHT_COLOR, smooth_shading=True)

    cam = _camera_pose(bbox_min, bbox_max)
    plotter.camera.position = cam["position"]
    plotter.camera.focal_point = cam["focal_point"]
    plotter.camera.up = cam["viewup"]
    img = plotter.screenshot(return_img=True)
    plotter.close()
    return img


def render_feature_views(
    run_id: str,
    feature: FeatureChange,
    original: GeometryModel,
    defeatured: GeometryModel,
) -> dict[str, Path]:
    """Render original/defeatured/overlay PNGs for one feature; return their paths."""
    bbox = feature.bbox or original.bbox
    bmin = np.array(bbox.min)
    bmax = np.array(bbox.max)
    # Pad so the highlighted geometry isn't flush with the frame edge.
    pad = max(float(np.linalg.norm(bmax - bmin)) * 0.25, 1.0)
    bmin, bmax = bmin - pad, bmax + pad

    original_img = _render(
        original.id, set(feature.geometry_refs.original_face_ids), bmin, bmax
    )
    defeatured_img = _render(
        defeatured.id, set(feature.geometry_refs.defeatured_face_ids), bmin, bmax
    )

    paths = {}
    for view, img in (("original", original_img), ("defeatured", defeatured_img)):
        path = files.screenshot_path(run_id, feature.id, view)
        _write_png(path, img)
        paths[view] = path

    # The overlay is a plain alpha blend of the two renders -- cheap and
    # sufficient for the report; both share the same camera pose so it lines up.
    overlay = (original_img.astype(np.float32) * 0.5 + defeatured_img.astype(np.float32) * 0.5).astype(
        np.uint8
    )
    overlay_path = files.screenshot_path(run_id, feature.id, "overlay")
    _write_png(overlay_path, overlay)
    paths["overlay"] = overlay_path

    return paths


def _write_png(path: Path, img: np.ndarray) -> None:
    from PIL import Image

    path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(img).save(path)
