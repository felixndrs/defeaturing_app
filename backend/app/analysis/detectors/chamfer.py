from __future__ import annotations

import math

from ...domain.enums import FeatureType
from ...domain.models import FeatureChange
from .base import Detector, FeatureCluster, build_feature, make_evidence, register_detector


@register_detector
class ChamferDetector(Detector):
    """A subtractive single planar face bridging what is a sharp edge in the
    defeatured model: a chamfer."""

    name = "chamfer"
    feature_type = FeatureType.CHAMFER
    priority = 50

    def detect(self, cluster: FeatureCluster, ctx) -> FeatureChange | None:
        if cluster.subtractive is False:
            return None
        if cluster.cylinders or len(cluster.planes) != 1 or len(cluster.faces) != 1:
            return None

        face = cluster.planes[0]
        # The chamfer face's short edges span the chamfer width w = d*sqrt(2) for
        # a symmetric chamfer on a 90 deg edge; recover the leg distance from the
        # shortest bounding edge.
        edge_lengths = [
            e.length
            for eid in face.edge_ids
            if (e := cluster_model_edge(ctx, eid)) is not None
        ]
        width = min(edge_lengths) if edge_lengths else 0.0
        distance = width / math.sqrt(2)
        evidence = [
            make_evidence(
                "planar_bevel",
                "A single planar face replacing a sharp edge -- a chamfer.",
                {"face_area": face.area, "short_edge": width, "leg_distance": distance},
            )
        ]
        params = {"distance": distance, "width": width}
        return build_feature(cluster, FeatureType.CHAMFER, self.name, params, evidence, confidence=0.72)


def cluster_model_edge(ctx, edge_id):
    return ctx.original.edge_by_id(edge_id)
