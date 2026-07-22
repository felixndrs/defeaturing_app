from __future__ import annotations

from ...domain.enums import FeatureType
from ...domain.models import FeatureChange
from .base import Detector, FeatureCluster, build_feature, make_evidence, register_detector


@register_detector
class SlotDetector(Detector):
    """A subtractive cluster with two or more partial cylinders (rounded ends)
    joined by planar walls: an elongated slot."""

    name = "slot"
    feature_type = FeatureType.SLOT
    priority = 20

    def detect(self, cluster: FeatureCluster, ctx) -> FeatureChange | None:
        if cluster.subtractive is False:
            return None
        cylinders = cluster.cylinders
        if len(cylinders) < 2 or len(cluster.planes) < 1:
            return None

        radii = [c.surface_params.get("radius", 0.0) for c in cylinders]
        radius = sum(radii) / len(radii)
        bbox = cluster.bbox
        length = max(bbox.max[i] - bbox.min[i] for i in range(3)) if bbox else 0.0
        evidence = [
            make_evidence(
                "obround_walls",
                "Two rounded ends plus planar side walls form a slot.",
                {"end_count": len(cylinders), "wall_count": len(cluster.planes), "radius": radius},
            )
        ]
        params = {"width": 2 * radius, "radius": radius, "length": length}
        return build_feature(cluster, FeatureType.SLOT, self.name, params, evidence, confidence=0.8)
