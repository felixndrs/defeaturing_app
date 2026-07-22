from __future__ import annotations

from pathlib import Path

import pytest

from app.analysis.pipeline import analyze
from app.domain.enums import FeatureType, ModelRole, RunStatus, SourceFormat
from app.importers.step_importer import build_model
from app.testing.fixtures import FIXTURES, by_name


def _run_fixture(fx):
    original_shape = fx.original()
    defeatured_shape = fx.defeatured()
    original = build_model(original_shape, Path("o.step"), ModelRole.ORIGINAL, "o", SourceFormat.STEP)
    defeatured = build_model(defeatured_shape, Path("d.step"), ModelRole.DEFEATURED, "d", SourceFormat.STEP)
    return analyze("run", "proj", original, defeatured, original_shape, defeatured_shape)


@pytest.mark.parametrize("fx", FIXTURES, ids=[f.name for f in FIXTURES])
def test_expected_feature_types_detected(fx):
    run = _run_fixture(fx)
    assert run.status is RunStatus.DONE, run.error
    detected = {f.type for f in run.features}
    for expected in fx.expected_features:
        assert expected in detected, (
            f"{fx.name}: expected {expected.value}, got {[f.type.value for f in run.features]}"
        )


@pytest.mark.parametrize("fx", FIXTURES, ids=[f.name for f in FIXTURES])
def test_nothing_is_lost(fx):
    """The core guarantee: every removed original face and every added
    defeatured face is accounted for by exactly one feature."""
    run = _run_fixture(fx)

    original_refs = [
        fid for f in run.features for fid in f.geometry_refs.original_face_ids
    ]
    defeatured_refs = [
        fid for f in run.features for fid in f.geometry_refs.defeatured_face_ids
    ]
    # No face is claimed twice.
    assert len(original_refs) == len(set(original_refs))
    assert len(defeatured_refs) == len(set(defeatured_refs))

    # The claimed faces are exactly the unpaired faces from the statistics.
    assert len(original_refs) == run.statistics.unpaired_original_face_count
    assert len(defeatured_refs) == run.statistics.unpaired_defeatured_face_count


def test_hole_diameter_recovered():
    run = _run_fixture(by_name("hole"))
    holes = [f for f in run.features if f.type is FeatureType.HOLE]
    assert len(holes) == 1
    assert holes[0].parameters["diameter"] == pytest.approx(10.0, abs=0.1)
    assert holes[0].parameters["depth"] == pytest.approx(20.0, abs=0.5)


def test_fillet_radius_recovered():
    run = _run_fixture(by_name("fillet"))
    fillets = [f for f in run.features if f.type is FeatureType.FILLET]
    assert len(fillets) == 1
    assert fillets[0].parameters["radius"] == pytest.approx(4.0, abs=0.1)


def test_chamfer_distance_recovered():
    run = _run_fixture(by_name("chamfer"))
    chamfers = [f for f in run.features if f.type is FeatureType.CHAMFER]
    assert len(chamfers) == 1
    assert chamfers[0].parameters["distance"] == pytest.approx(5.0, abs=0.5)


def test_boss_diameter_recovered():
    run = _run_fixture(by_name("boss"))
    bosses = [f for f in run.features if f.type is FeatureType.BOSS]
    assert len(bosses) == 1
    assert bosses[0].parameters["diameter"] == pytest.approx(10.0, abs=0.2)


def test_moved_wall_is_unknown_not_misclassified():
    run = _run_fixture(by_name("unknown_moved_wall"))
    types = {f.type for f in run.features}
    assert FeatureType.UNKNOWN in types
    # Must not be dressed up as a real feature.
    assert types == {FeatureType.UNKNOWN}


def test_combined_detects_all_four_features():
    run = _run_fixture(by_name("combined"))
    detected = {f.type for f in run.features}
    for expected in (FeatureType.FILLET, FeatureType.HOLE, FeatureType.POCKET, FeatureType.BOSS):
        assert expected in detected, [f.type.value for f in run.features]
