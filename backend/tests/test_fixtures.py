from __future__ import annotations

import pytest

from app.domain.enums import ModelRole, SourceFormat
from app.importers.step_importer import build_model
from app.testing.fixtures import FIXTURES


@pytest.mark.parametrize("fx", FIXTURES, ids=[f.name for f in FIXTURES])
def test_fixture_pair_imports_and_differs(fx):
    """Every fixture must produce two valid, watertight solids that actually
    differ -- otherwise it teaches the detectors nothing."""
    from pathlib import Path

    original = build_model(
        fx.original(), Path(f"{fx.name}_o.step"), ModelRole.ORIGINAL, "o", SourceFormat.STEP
    )
    defeatured = build_model(
        fx.defeatured(), Path(f"{fx.name}_d.step"), ModelRole.DEFEATURED, "d", SourceFormat.STEP
    )

    assert len(original.solids) == 1
    assert len(defeatured.solids) == 1
    assert original.volume > 0 and defeatured.volume > 0

    # The pair must encode a real change: either the face count or the volume
    # moves. If neither does, the fixture is broken.
    face_changed = len(original.faces) != len(defeatured.faces)
    volume_changed = abs(original.volume - defeatured.volume) > 1e-6
    assert face_changed or volume_changed, "fixture original and defeatured are identical"


def test_material_removal_fixtures_lose_volume():
    """Fillet, chamfer, hole, pocket, slot remove material; boss and rib add it.
    Encodes the expected sign of the volume change per fixture family."""
    from pathlib import Path

    def vol(builder, name):
        return build_model(
            builder(), Path(name), ModelRole.ORIGINAL, name, SourceFormat.STEP
        ).volume

    from app.testing import bodies

    base = vol(bodies.base_box, "base")
    assert vol(bodies.with_hole, "hole") < base
    assert vol(bodies.with_pocket, "pocket") < base
    assert vol(bodies.with_slot, "slot") < base
    assert vol(bodies.with_fillet, "fillet") < base
    assert vol(bodies.with_chamfer, "chamfer") < base
    # Protrusions add material.
    assert vol(bodies.with_boss, "boss") > base
    assert vol(bodies.with_rib, "rib") > base
