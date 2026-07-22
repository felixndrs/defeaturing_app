from __future__ import annotations

import math

from ...domain.enums import FeatureType
from ...domain.models import FeatureChange
from .base import Detector, FeatureCluster, build_feature, make_evidence, register_detector


@register_detector
class HoleDetector(Detector):
    """A subtractive cluster whose defining face is a full (closed) cylinder."""

    name = "hole"
    feature_type = FeatureType.HOLE
    priority = 10

    def detect(self, cluster: FeatureCluster, ctx) -> FeatureChange | None:
        if cluster.subtractive is False:
            return None
        closed = cluster.closed_cylinders()
        if len(closed) != 1 or len(cluster.cylinders) != 1:
            return None

        cyl = closed[0]
        radius = cyl.surface_params.get("radius", 0.0)
        # Lateral area = 2*pi*r*h, so the through length follows without needing
        # the parametric extent.
        depth = cyl.area / (2 * math.pi * radius) if radius else 0.0
        axis = cyl.surface_params.get("axis")

        evidence = [
            make_evidence(
                "closed_cylinder",
                "Removed face is a full cylindrical wall (360 deg), the signature of a hole.",
                {"radius": radius, "lateral_area": cyl.area, "u_closed": True},
            ),
            make_evidence(
                "depth_from_area",
                "Through length derived from lateral area / circumference.",
                {"depth": depth},
            ),
        ]
        params = {"diameter": 2 * radius, "radius": radius, "depth": depth, "axis": list(axis) if axis else None}
        return build_feature(cluster, FeatureType.HOLE, self.name, params, evidence, confidence=0.92)
