"""Detector contract and registry (the second extension point).

A detector inspects one candidate cluster and either claims it as a feature or
declines. Adding a feature type is a new module here plus @register_detector --
the pipeline and everything downstream are untouched. Detectors run in ascending
`priority`; the first to claim a cluster wins, and whatever no detector claims is
swept up as `unknown`, so no geometry change is ever dropped.
"""

from __future__ import annotations

import abc
import uuid
from dataclasses import dataclass, field

from ...domain.enums import ChangeStatus, FeatureType, SurfaceKind
from ...domain.models import BBox, Evidence, Face, FeatureChange, GeometryRefs
from .. import clustering, vec


@dataclass
class FeatureCluster:
    """A connected group of loose faces offered to the detectors."""

    faces: list[Face]
    #: True when the faces come from the defeatured model (added material).
    added: bool
    #: True subtractive (hole/pocket/fillet...), False additive (boss/rib),
    #: None when undetermined. Filled by the pipeline before detection.
    subtractive: bool | None = None

    @property
    def centroid(self) -> vec.Vec3:
        return clustering.cluster_centroid(self.faces)

    @property
    def bbox(self) -> BBox | None:
        return clustering.cluster_bbox(self.faces)

    def of_kind(self, kind: SurfaceKind) -> list[Face]:
        return [f for f in self.faces if f.surface_kind is kind]

    @property
    def cylinders(self) -> list[Face]:
        return self.of_kind(SurfaceKind.CYLINDER)

    @property
    def planes(self) -> list[Face]:
        return self.of_kind(SurfaceKind.PLANE)

    def closed_cylinders(self) -> list[Face]:
        return [c for c in self.cylinders if _is_closed(c)]

    @property
    def kind_counts(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for f in self.faces:
            counts[f.surface_kind.value] = counts.get(f.surface_kind.value, 0) + 1
        return counts


def _is_closed(cyl: Face) -> bool:
    p = cyl.surface_params
    if p.get("u_closed"):
        return True
    from math import pi

    return p.get("u_period", 0.0) >= 2 * pi * 0.98


class Detector(abc.ABC):
    name: str
    feature_type: FeatureType
    priority: int = 100

    @abc.abstractmethod
    def detect(self, cluster: FeatureCluster, ctx) -> FeatureChange | None:
        ...


_DETECTORS: list[Detector] = []


def register_detector(cls: type[Detector]) -> type[Detector]:
    _DETECTORS.append(cls())
    _DETECTORS.sort(key=lambda d: d.priority)
    return cls


def available_detectors() -> list[Detector]:
    return list(_DETECTORS)


# --------------------------------------------------------------------------
# Construction helpers shared by detectors
# --------------------------------------------------------------------------


def make_evidence(kind: str, description: str, values: dict, stage: str = "detection") -> Evidence:
    return Evidence(
        id=f"ev_{uuid.uuid4().hex[:10]}",
        kind=kind,
        description=description,
        values=values,
        source_stage=stage,
    )


def build_feature(
    cluster: FeatureCluster,
    feature_type: FeatureType,
    detector: str,
    parameters: dict,
    evidence: list[Evidence],
    confidence: float,
) -> FeatureChange:
    face_ids = [f.id for f in cluster.faces]
    refs = (
        GeometryRefs(defeatured_face_ids=face_ids)
        if cluster.added
        else GeometryRefs(original_face_ids=face_ids)
    )
    return FeatureChange(
        id=f"ft_{uuid.uuid4().hex[:12]}",
        type=feature_type,
        status=ChangeStatus.ADDED if cluster.added else ChangeStatus.REMOVED,
        detector=detector,
        parameters=parameters,
        evidence=evidence,
        confidence=confidence,
        geometry_refs=refs,
        bbox=cluster.bbox,
        centroid=cluster.centroid,
    )
