from __future__ import annotations

import math

import pytest
from synthetic import make_box, make_box_with_fillet, make_box_with_hole

from app.domain.enums import ModelRole, SourceFormat, SurfaceKind
from app.importers import load_model

DX, DY, DZ = 40.0, 30.0, 20.0


def test_box_roundtrip_through_step(write_step):
    path = write_step(make_box(DX, DY, DZ), "box.step")
    model = load_model(path, ModelRole.ORIGINAL, "m1")

    assert model.source_format is SourceFormat.STEP
    assert len(model.solids) == 1
    assert len(model.faces) == 6
    assert len(model.edges) == 12
    assert model.volume == pytest.approx(DX * DY * DZ, rel=1e-6)
    assert all(f.surface_kind is SurfaceKind.PLANE for f in model.faces)


def test_face_ids_are_unique_and_stable_across_imports(write_step):
    path = write_step(make_box_with_fillet(3.0, DX, DY, DZ), "fillet.step")
    first = load_model(path, ModelRole.ORIGINAL, "a")
    second = load_model(path, ModelRole.ORIGINAL, "b")

    ids = [f.id for f in first.faces]
    assert len(set(ids)) == len(ids), "face ids must be unique within a model"
    # Stability is what lets a user decision survive a re-analysis of the file.
    assert {f.id for f in first.faces} == {f.id for f in second.faces}


def test_fillet_radius_is_recovered(write_step):
    radius = 3.0
    path = write_step(make_box_with_fillet(radius, DX, DY, DZ), "fillet.step")
    model = load_model(path, ModelRole.ORIGINAL, "m")

    # Filleting all edges of a box yields cylindrical edge blends and spherical
    # corner patches -- not tori. Detectors must not assume torus geometry.
    cylinders = [f for f in model.faces if f.surface_kind is SurfaceKind.CYLINDER]
    spheres = [f for f in model.faces if f.surface_kind is SurfaceKind.SPHERE]
    assert len(cylinders) == 12
    assert len(spheres) == 8
    assert all(f.surface_params["radius"] == pytest.approx(radius) for f in cylinders)


def test_hole_diameter_and_volume(write_step):
    diameter = 8.0
    path = write_step(make_box_with_hole(diameter, DX, DY, DZ), "hole.step")
    model = load_model(path, ModelRole.ORIGINAL, "m")

    cylinders = [f for f in model.faces if f.surface_kind is SurfaceKind.CYLINDER]
    assert len(cylinders) == 1
    assert cylinders[0].surface_params["radius"] == pytest.approx(diameter / 2)

    expected = DX * DY * DZ - math.pi * (diameter / 2) ** 2 * DZ
    assert model.volume == pytest.approx(expected, rel=1e-4)


def test_faces_and_edges_are_linked(write_step):
    path = write_step(make_box(DX, DY, DZ), "box.step")
    model = load_model(path, ModelRole.ORIGINAL, "m")

    assert all(len(f.edge_ids) == 4 for f in model.faces)
    # Every edge of a closed solid is shared by exactly two faces; this
    # adjacency is what the fillet and chamfer detectors reason over.
    assert all(len(e.face_ids) == 2 for e in model.edges)
    assert all(model.face_by_id(fid) is not None for e in model.edges for fid in e.face_ids)


def test_unsupported_extension_is_rejected(tmp_path):
    from app.importers import UnsupportedFormatError

    bogus = tmp_path / "model.xyz"
    bogus.write_text("not a cad file")
    with pytest.raises(UnsupportedFormatError):
        load_model(bogus, ModelRole.ORIGINAL, "m")
