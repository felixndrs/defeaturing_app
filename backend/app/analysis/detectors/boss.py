from __future__ import annotations

import math

from ...domain.enums import FeatureType
from ...domain.models import FeatureChange
from .base import Detector, FeatureCluster, build_feature, make_evidence, register_detector


@register_detector
class BossDetector(Detector):
    """An additive cluster built around a full cylinder: a cylindrical boss."""

    name = "boss"
    feature_type = FeatureType.BOSS
    priority = 15

    def detect(self, cluster: FeatureCluster, ctx) -> FeatureChange | None:
        if cluster.subtractive is True:
            return None
        closed = cluster.closed_cylinders()
        if len(closed) != 1:
            return None

        cyl = closed[0]
        radius = cyl.surface_params.get("radius", 0.0)
        height = cyl.area / (2 * math.pi * radius) if radius else 0.0
        evidence = [
            make_evidence(
                "additive_cylinder",
                "Removed material forms a full cylindrical wall protruding from the body.",
                {"radius": radius, "height": height, "additive": True},
            )
        ]
        params = {"diameter": 2 * radius, "radius": radius, "height": height}
        return build_feature(cluster, FeatureType.BOSS, self.name, params, evidence, confidence=0.85)
