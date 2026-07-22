"""Face pairing between the original and defeatured models.

Faces are matched by the *underlying surface* (a plane's equation, a cylinder's
axis and radius), not by area or centroid. This is the key idea: defeaturing a
hole leaves the surrounding top face on the same plane but with a different area,
so a surface-based match keeps them paired and flags the area change, while the
hole's cylindrical wall has no counterpart and surfaces as removed geometry.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..domain.enums import SurfaceKind
from ..domain.models import Face, GeometryModel
from . import vec

Signature = tuple


def _round(x: float, ndigits: int = 3) -> float:
    return round(x, ndigits)


def _round_vec(v: vec.Vec3, ndigits: int = 3) -> tuple:
    return (round(v[0], ndigits), round(v[1], ndigits), round(v[2], ndigits))


def surface_signature(face: Face, ndigits: int = 3) -> Signature:
    """A hashable key identifying the surface a face lies on.

    Two faces on the same plane or the same cylinder share a signature even if
    their trimmed extents differ.
    """
    k = face.surface_kind
    p = face.surface_params

    if k is SurfaceKind.PLANE and "axis" in p and "origin" in p:
        n = vec.canonical_dir(p["axis"])
        offset = vec.dot(p["origin"], n)
        return ("plane", _round_vec(n, ndigits), _round(offset, ndigits))

    if k in (SurfaceKind.CYLINDER, SurfaceKind.CONE) and "axis" in p:
        n = vec.canonical_dir(p["axis"])
        foot = vec.point_line_foot((0.0, 0.0, 0.0), p.get("axis_location", (0, 0, 0)), n)
        radius = p.get("radius", 0.0)
        return (k.value, _round_vec(n, ndigits), _round_vec(foot, ndigits), _round(radius, ndigits))

    if k is SurfaceKind.SPHERE and "center" in p:
        return ("sphere", _round_vec(p["center"], ndigits), _round(p.get("radius", 0.0), ndigits))

    if k is SurfaceKind.TORUS and "axis_location" in p:
        n = vec.canonical_dir(p["axis"])
        return (
            "torus",
            _round_vec(n, ndigits),
            _round_vec(p["axis_location"], ndigits),
            _round(p.get("major_radius", 0.0), ndigits),
            _round(p.get("minor_radius", 0.0), ndigits),
        )

    # Free-form surfaces have no analytic signature; fall back to a coarse
    # positional key so identical untouched faces still pair.
    return (k.value, _round_vec(face.centroid, 1), _round(face.area, 1))


@dataclass
class PairingResult:
    #: (original_face, defeatured_face) pairs on the same surface.
    matched: list[tuple[Face, Face]] = field(default_factory=list)
    #: Subset of `matched` whose area changed beyond tolerance -- host faces
    #: where a feature was cut away.
    modified: list[tuple[Face, Face]] = field(default_factory=list)
    #: Original faces with no surface counterpart -- removed detail.
    removed: list[Face] = field(default_factory=list)
    #: Defeatured faces with no counterpart -- added/rebuilt faces.
    added: list[Face] = field(default_factory=list)


def pair_faces(
    original: GeometryModel, defeatured: GeometryModel, area_rel_tol: float = 1e-3
) -> PairingResult:
    result = PairingResult()

    deft_by_sig: dict[Signature, list[Face]] = {}
    for f in defeatured.faces:
        deft_by_sig.setdefault(surface_signature(f), []).append(f)

    used: set[str] = set()
    for of in original.faces:
        sig = surface_signature(of)
        candidates = [c for c in deft_by_sig.get(sig, []) if c.id not in used]
        if not candidates:
            result.removed.append(of)
            continue
        # Same surface can carry several faces; take the nearest by centroid.
        df = min(candidates, key=lambda c: vec.dist(of.centroid, c.centroid))
        used.add(df.id)
        result.matched.append((of, df))
        denom = max(of.area, df.area, 1e-9)
        if abs(of.area - df.area) / denom > area_rel_tol:
            result.modified.append((of, df))

    for f in defeatured.faces:
        if f.id not in used:
            result.added.append(f)

    return result
