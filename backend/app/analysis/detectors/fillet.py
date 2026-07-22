from __future__ import annotations

from ...domain.enums import FeatureType, SurfaceKind
from ...domain.models import FeatureChange
from .base import Detector, FeatureCluster, build_feature, make_evidence, register_detector


@register_detector
class FilletDetector(Detector):
    """A subtractive cluster of partial (non-closed) rolling surfaces: an edge
    blend. Rounding a box edge yields cylindrical patches (and spherical corners
    where three meet), never a full cylinder -- that distinguishes it from a hole.
    """

    name = "fillet"
    feature_type = FeatureType.FILLET
    priority = 40

    def detect(self, cluster: FeatureCluster, ctx) -> FeatureChange | None:
        if cluster.subtractive is False:
            return None
        if cluster.planes:
            return None
        if cluster.closed_cylinders():
            return None
        rolling = cluster.cylinders + cluster.of_kind(SurfaceKind.TORUS) + cluster.of_kind(SurfaceKind.SPHERE)
        if not rolling or rolling != cluster.faces:
            return None

        radius = _radius_of(rolling[0])
        evidence = [
            make_evidence(
                "tangent_blend",
                "Partial cylindrical/toroidal patch tangent to its neighbours: a rounded edge.",
                {"radius": radius, "patch_count": len(rolling), "closed": False},
            )
        ]
        params = {"radius": radius, "patch_count": len(rolling)}
        return build_feature(cluster, FeatureType.FILLET, self.name, params, evidence, confidence=0.88)


def _radius_of(face) -> float:
    p = face.surface_params
    if face.surface_kind is SurfaceKind.TORUS:
        return p.get("minor_radius", 0.0)
    return p.get("radius", 0.0)
