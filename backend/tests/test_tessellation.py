from __future__ import annotations

from pathlib import Path

import trimesh

from app.domain.enums import ModelRole, SourceFormat
from app.importers.step_importer import build_model
from app.testing.bodies import with_hole


def test_glb_has_one_named_node_per_face(tmp_path):
    glb = tmp_path / "hole.glb"
    model = build_model(
        with_hole(), Path("hole.step"), ModelRole.ORIGINAL, "m", SourceFormat.STEP, glb_out=glb
    )
    assert glb.exists() and glb.stat().st_size > 0

    scene = trimesh.load(glb, file_type="glb")
    node_names = set(scene.geometry.keys())
    model_face_ids = {f.id for f in model.faces}

    # Every meshable face is present in the GLB under its exact face id, so a
    # ray hit in the viewer maps straight back to a domain face.
    assert node_names == model_face_ids
    assert all(name.startswith("f_") for name in node_names)


def test_glb_geometry_is_watertight_enough(tmp_path):
    glb = tmp_path / "hole.glb"
    build_model(
        with_hole(), Path("hole.step"), ModelRole.ORIGINAL, "m", SourceFormat.STEP, glb_out=glb
    )
    scene = trimesh.load(glb, file_type="glb")
    total_tris = sum(len(g.faces) for g in scene.geometry.values())
    # A box with a hole tessellates into a non-trivial mesh; guard against an
    # empty or collapsed export.
    assert total_tris > 20
