from __future__ import annotations

from ...domain.enums import FeatureType
from ...domain.models import FeatureChange
from .base import FeatureCluster, build_feature, make_evidence


def build_unknown(cluster: FeatureCluster) -> FeatureChange:
    """Catch-all for clusters no detector claimed.

    Not registered like the others: the pipeline calls it explicitly on every
    leftover cluster so that the guarantee 'no geometry change is lost' holds by
    construction. It records the raw shape signature as evidence for the LLM and
    the report.
    """
    bbox = cluster.bbox
    evidence = [
        make_evidence(
            "unclassified_change",
            "Geometry change that matched no known feature pattern.",
            {
                "face_count": len(cluster.faces),
                "surface_kinds": cluster.kind_counts,
                "added" if cluster.added else "removed": True,
                "subtractive": cluster.subtractive if cluster.subtractive is not None else "unknown",
            },
        )
    ]
    return build_feature(
        cluster,
        FeatureType.UNKNOWN,
        detector="unknown",
        parameters={"surface_kinds": cluster.kind_counts},
        evidence=evidence,
        confidence=0.3,
    )
