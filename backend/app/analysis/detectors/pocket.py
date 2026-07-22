from __future__ import annotations

from ...domain.enums import FeatureType
from ...domain.models import FeatureChange
from .base import Detector, FeatureCluster, build_feature, make_evidence, register_detector


@register_detector
class PocketDetector(Detector):
    """A subtractive cluster of planar faces (a floor plus walls) with no
    cylinders: a rectangular pocket."""

    name = "pocket"
    feature_type = FeatureType.POCKET
    priority = 30

    def detect(self, cluster: FeatureCluster, ctx) -> FeatureChange | None:
        if cluster.subtractive is False:
            return None
        if cluster.cylinders:
            return None
        planes = cluster.planes
        # A floor and at least three walls; fewer is a chamfer or a single face.
        if len(planes) < 4:
            return None

        bbox = cluster.bbox
        extents = sorted(bbox.max[i] - bbox.min[i] for i in range(3)) if bbox else [0, 0, 0]
        depth = extents[0]  # shallowest extent is the pocket depth
        evidence = [
            make_evidence(
                "planar_cavity",
                "A planar floor enclosed by planar walls, cut into the body.",
                {"face_count": len(planes), "depth": depth,
                 "footprint": [extents[1], extents[2]]},
            )
        ]
        params = {"depth": depth, "width": extents[1], "length": extents[2]}
        return build_feature(cluster, FeatureType.POCKET, self.name, params, evidence, confidence=0.72)
