from __future__ import annotations

from ...domain.enums import FeatureType
from ...domain.models import FeatureChange
from .base import Detector, FeatureCluster, build_feature, make_evidence, register_detector


@register_detector
class RibDetector(Detector):
    """An additive cluster of planar faces that is thin in one direction: a rib."""

    name = "rib"
    feature_type = FeatureType.RIB
    priority = 35

    def detect(self, cluster: FeatureCluster, ctx) -> FeatureChange | None:
        if cluster.subtractive is True:
            return None
        if cluster.cylinders:
            return None
        if len(cluster.planes) < 3:
            return None

        bbox = cluster.bbox
        extents = sorted(bbox.max[i] - bbox.min[i] for i in range(3)) if bbox else [0, 0, 0]
        thickness = extents[0]
        # A rib is markedly thinner than it is long/tall; guard against calling
        # a chunky additive block a rib.
        if extents[2] > 0 and thickness / extents[2] > 0.5:
            return None
        evidence = [
            make_evidence(
                "thin_additive_wall",
                "Thin planar protrusion: much longer and taller than it is thick.",
                {"thickness": thickness, "height": extents[1], "length": extents[2]},
            )
        ]
        params = {"thickness": thickness, "height": extents[1], "length": extents[2]}
        return build_feature(cluster, FeatureType.RIB, self.name, params, evidence, confidence=0.7)
