"""Shared analysis context.

Carries both domain models and, when available, their live OCC shapes so the
few genuinely 3D checks (is this region material that was added or removed?) can
use OpenCascade's solid classifier. Everything else works off the domain model.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from ..domain.models import Face, GeometryModel
from . import vec


def read_step_shape(path: Path):
    """Re-read an OCC shape from a STEP file (used when the cache is cold)."""
    from ..importers.step_importer import StepImporter

    return StepImporter()._read_shape(path)


class SolidRegion:
    """Point-in-solid queries against one shape, built once and reused."""

    def __init__(self, shape) -> None:
        from OCP.BRepClass3d import BRepClass3d_SolidClassifier

        self._clf = BRepClass3d_SolidClassifier(shape)

    def contains(self, point: vec.Vec3, tol: float = 1e-6) -> bool:
        from OCP.gp import gp_Pnt
        from OCP.TopAbs import TopAbs_IN

        self._clf.Perform(gp_Pnt(*point), tol)
        return self._clf.State() == TopAbs_IN


@dataclass
class AnalysisContext:
    original: GeometryModel
    defeatured: GeometryModel
    original_shape: object | None = None
    defeatured_shape: object | None = None
    _defeatured_region: SolidRegion | None = field(default=None, repr=False)
    _original_region: SolidRegion | None = field(default=None, repr=False)

    @property
    def diagonal(self) -> float:
        return max(self.original.bbox.diagonal, self.defeatured.bbox.diagonal)

    @property
    def defeatured_region(self) -> SolidRegion | None:
        if self._defeatured_region is None and self.defeatured_shape is not None:
            self._defeatured_region = SolidRegion(self.defeatured_shape)
        return self._defeatured_region

    def region_is_subtractive(self, faces: list[Face]) -> bool | None:
        """True if the cluster of removed faces was material removed from the
        original (hole/pocket/fillet/chamfer/slot), False if it was material
        present in the original but absent from the defeatured (boss/rib).

        Works by stepping a hair off each face along its outward normal and
        asking whether that point is inside the defeatured solid. Returns None
        when the OCC shape is unavailable, so callers can fall back.
        """
        region = self.defeatured_region
        if region is None:
            return None
        eps = self.diagonal * 1e-3
        inside = 0
        outside = 0
        for face in faces:
            if face.normal is None:
                continue
            probe = vec.add(face.centroid, vec.scale(vec.normalize(face.normal), eps))
            if region.contains(probe):
                inside += 1
            else:
                outside += 1
        if inside == outside == 0:
            return None
        return inside >= outside
