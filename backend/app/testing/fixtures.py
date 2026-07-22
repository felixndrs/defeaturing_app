"""Original/defeatured fixture pairs with expected detector output.

`FIXTURES` is the single source of truth used by both the test suite and the
`generate_testdata` CLI, so the STEP files on disk and the assertions never
drift apart.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from OCP.TopoDS import TopoDS_Shape

from ..domain.enums import FeatureType
from . import bodies


@dataclass(frozen=True)
class Fixture:
    name: str
    description: str
    original: Callable[[], TopoDS_Shape]
    defeatured: Callable[[], TopoDS_Shape]
    #: Feature types the analysis is expected to report for this pair.
    expected_features: tuple[FeatureType, ...]
    #: Known-good parameter values, keyed by feature type, for assertions.
    expected_params: dict[FeatureType, dict[str, float]] = field(default_factory=dict)


FIXTURES: list[Fixture] = [
    Fixture(
        "fillet",
        "One vertical edge rounded (r=4).",
        bodies.with_fillet,
        bodies.base_box,
        (FeatureType.FILLET,),
        {FeatureType.FILLET: {"radius": bodies.FILLET_RADIUS}},
    ),
    Fixture(
        "chamfer",
        "One vertical edge chamfered (5 mm).",
        bodies.with_chamfer,
        bodies.base_box,
        (FeatureType.CHAMFER,),
        {FeatureType.CHAMFER: {"distance": bodies.CHAMFER_DIST}},
    ),
    Fixture(
        "hole",
        "One through hole (d=10) along Z.",
        bodies.with_hole,
        bodies.base_box,
        (FeatureType.HOLE,),
        {FeatureType.HOLE: {"diameter": bodies.HOLE_DIAMETER}},
    ),
    Fixture(
        "pocket",
        "One rectangular blind pocket (16x12x8).",
        bodies.with_pocket,
        bodies.base_box,
        (FeatureType.POCKET,),
        {FeatureType.POCKET: {"depth": bodies.POCKET["depth"]}},
    ),
    Fixture(
        "slot",
        "One rounded-end slot on the top face.",
        bodies.with_slot,
        bodies.base_box,
        (FeatureType.SLOT,),
        {FeatureType.SLOT: {"width": 2 * bodies.SLOT["radius"]}},
    ),
    Fixture(
        "boss",
        "One cylindrical boss protruding from the top.",
        bodies.with_boss,
        bodies.base_box,
        (FeatureType.BOSS,),
        {FeatureType.BOSS: {"diameter": bodies.BOSS["diameter"]}},
    ),
    Fixture(
        "rib",
        "One thin rib standing on the top face.",
        bodies.with_rib,
        bodies.base_box,
        (FeatureType.RIB,),
        {FeatureType.RIB: {"thickness": bodies.RIB["dy"]}},
    ),
    Fixture(
        "combined",
        "Realistic part: fillet + hole + pocket + boss together.",
        bodies.with_all_features,
        bodies.base_box,
        (FeatureType.FILLET, FeatureType.HOLE, FeatureType.POCKET, FeatureType.BOSS),
    ),
    Fixture(
        "unknown_moved_wall",
        "A planar wall moved 2 mm -- no named feature; must become 'unknown'.",
        bodies.base_box,
        bodies.moved_wall,
        (FeatureType.UNKNOWN,),
    ),
]


def by_name(name: str) -> Fixture:
    for fx in FIXTURES:
        if fx.name == name:
            return fx
    raise KeyError(name)
