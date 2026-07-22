"""Thin helpers around OpenCascade (OCP bindings).

Everything that touches OCC types lives in this module and in the analysis
package, so that the rest of the application stays format agnostic. Keeping the
imports here also makes it cheap to see what parts of OCCT the project relies on.
"""

from __future__ import annotations

import hashlib
from typing import Any, Iterator

from OCP.BRep import BRep_Tool
from OCP.BRepAdaptor import BRepAdaptor_Curve, BRepAdaptor_Surface
from OCP.BRepGProp import BRepGProp
from OCP.Bnd import Bnd_Box
from OCP.BRepBndLib import BRepBndLib
from OCP.GeomAbs import GeomAbs_CurveType, GeomAbs_SurfaceType
from OCP.gp import gp_Pnt
from OCP.GProp import GProp_GProps
from OCP.TopAbs import TopAbs_FACE, TopAbs_EDGE, TopAbs_SOLID, TopAbs_ShapeEnum
from OCP.TopExp import TopExp_Explorer
from OCP.TopoDS import TopoDS, TopoDS_Edge, TopoDS_Face, TopoDS_Shape, TopoDS_Solid

from ..domain.enums import SurfaceKind
from ..domain.models import BBox, Vec3

_SURFACE_KIND = {
    GeomAbs_SurfaceType.GeomAbs_Plane: SurfaceKind.PLANE,
    GeomAbs_SurfaceType.GeomAbs_Cylinder: SurfaceKind.CYLINDER,
    GeomAbs_SurfaceType.GeomAbs_Cone: SurfaceKind.CONE,
    GeomAbs_SurfaceType.GeomAbs_Sphere: SurfaceKind.SPHERE,
    GeomAbs_SurfaceType.GeomAbs_Torus: SurfaceKind.TORUS,
    GeomAbs_SurfaceType.GeomAbs_BezierSurface: SurfaceKind.BEZIER,
    GeomAbs_SurfaceType.GeomAbs_BSplineSurface: SurfaceKind.BSPLINE,
    GeomAbs_SurfaceType.GeomAbs_SurfaceOfRevolution: SurfaceKind.REVOLUTION,
    GeomAbs_SurfaceType.GeomAbs_SurfaceOfExtrusion: SurfaceKind.EXTRUSION,
    GeomAbs_SurfaceType.GeomAbs_OffsetSurface: SurfaceKind.OFFSET,
}

_CURVE_KIND = {
    GeomAbs_CurveType.GeomAbs_Line: "line",
    GeomAbs_CurveType.GeomAbs_Circle: "circle",
    GeomAbs_CurveType.GeomAbs_Ellipse: "ellipse",
    GeomAbs_CurveType.GeomAbs_Hyperbola: "hyperbola",
    GeomAbs_CurveType.GeomAbs_Parabola: "parabola",
    GeomAbs_CurveType.GeomAbs_BezierCurve: "bezier",
    GeomAbs_CurveType.GeomAbs_BSplineCurve: "bspline",
}


# --------------------------------------------------------------------------
# Traversal
# --------------------------------------------------------------------------


def _explore(shape: TopoDS_Shape, kind: TopAbs_ShapeEnum) -> Iterator[TopoDS_Shape]:
    exp = TopExp_Explorer(shape, kind)
    while exp.More():
        yield exp.Current()
        exp.Next()


def iter_faces(shape: TopoDS_Shape) -> Iterator[TopoDS_Face]:
    for s in _explore(shape, TopAbs_FACE):
        yield TopoDS.Face_s(s)


def iter_edges(shape: TopoDS_Shape) -> Iterator[TopoDS_Edge]:
    for s in _explore(shape, TopAbs_EDGE):
        yield TopoDS.Edge_s(s)


def iter_solids(shape: TopoDS_Shape) -> Iterator[TopoDS_Solid]:
    for s in _explore(shape, TopAbs_SOLID):
        yield TopoDS.Solid_s(s)


# --------------------------------------------------------------------------
# Measurements
# --------------------------------------------------------------------------


def _pnt(p: gp_Pnt) -> Vec3:
    return (p.X(), p.Y(), p.Z())


def face_area_centroid(face: TopoDS_Face) -> tuple[float, Vec3]:
    props = GProp_GProps()
    BRepGProp.SurfaceProperties_s(face, props)
    return props.Mass(), _pnt(props.CentreOfMass())


def edge_length(edge: TopoDS_Edge) -> float:
    props = GProp_GProps()
    BRepGProp.LinearProperties_s(edge, props)
    return props.Mass()


def solid_volume_area(solid: TopoDS_Shape) -> tuple[float, float]:
    vprops = GProp_GProps()
    BRepGProp.VolumeProperties_s(solid, vprops)
    sprops = GProp_GProps()
    BRepGProp.SurfaceProperties_s(solid, sprops)
    return abs(vprops.Mass()), sprops.Mass()


def bounding_box(shape: TopoDS_Shape, tolerance: float = 1e-6) -> BBox:
    box = Bnd_Box()
    BRepBndLib.Add_s(shape, box, True)
    box.SetGap(tolerance)
    xmin, ymin, zmin, xmax, ymax, zmax = box.Get()
    return BBox(min=(xmin, ymin, zmin), max=(xmax, ymax, zmax))


# --------------------------------------------------------------------------
# Surface / curve classification
# --------------------------------------------------------------------------


def surface_kind_and_params(face: TopoDS_Face) -> tuple[SurfaceKind, dict[str, Any]]:
    """Classify a face and extract the analytic parameters detectors rely on.

    The parameters (radius, axis, half angle) are what makes fillet/hole/chamfer
    recognition possible without any heuristics on the tessellation.
    """
    adaptor = BRepAdaptor_Surface(face)
    occ_type = adaptor.GetType()
    kind = _SURFACE_KIND.get(occ_type, SurfaceKind.OTHER)
    params: dict[str, Any] = {}

    if kind is SurfaceKind.PLANE:
        pln = adaptor.Plane()
        params["origin"] = _pnt(pln.Location())
        params["axis"] = _dir(pln.Axis().Direction())
    elif kind is SurfaceKind.CYLINDER:
        cyl = adaptor.Cylinder()
        params["radius"] = cyl.Radius()
        params["axis"] = _dir(cyl.Axis().Direction())
        params["axis_location"] = _pnt(cyl.Axis().Location())
    elif kind is SurfaceKind.CONE:
        cone = adaptor.Cone()
        params["radius"] = cone.RefRadius()
        params["half_angle"] = cone.SemiAngle()
        params["axis"] = _dir(cone.Axis().Direction())
        params["axis_location"] = _pnt(cone.Axis().Location())
    elif kind is SurfaceKind.SPHERE:
        sph = adaptor.Sphere()
        params["radius"] = sph.Radius()
        params["center"] = _pnt(sph.Location())
    elif kind is SurfaceKind.TORUS:
        tor = adaptor.Torus()
        # minor_radius is the fillet radius when the torus is a rolling ball blend
        params["major_radius"] = tor.MajorRadius()
        params["minor_radius"] = tor.MinorRadius()
        params["axis"] = _dir(tor.Axis().Direction())
        params["axis_location"] = _pnt(tor.Axis().Location())

    # Parameter-space extent, used to tell a full cylinder (a through hole)
    # from a partial one (a rounded corner).
    params["u_period"] = adaptor.LastUParameter() - adaptor.FirstUParameter()
    params["v_period"] = adaptor.LastVParameter() - adaptor.FirstVParameter()
    params["u_closed"] = bool(adaptor.IsUClosed())
    params["v_closed"] = bool(adaptor.IsVClosed())
    return kind, params


def _dir(direction) -> Vec3:
    return (direction.X(), direction.Y(), direction.Z())


def face_normal(face: TopoDS_Face) -> Vec3 | None:
    """Outward normal at the parametric mid point, honouring face orientation."""
    from OCP.BRepLProp import BRepLProp_SLProps
    from OCP.TopAbs import TopAbs_REVERSED

    adaptor = BRepAdaptor_Surface(face)
    u = (adaptor.FirstUParameter() + adaptor.LastUParameter()) / 2
    v = (adaptor.FirstVParameter() + adaptor.LastVParameter()) / 2
    props = BRepLProp_SLProps(adaptor, u, v, 1, 1e-6)
    if not props.IsNormalDefined():
        return None
    n = props.Normal()
    sign = -1.0 if face.Orientation() == TopAbs_REVERSED else 1.0
    return (n.X() * sign, n.Y() * sign, n.Z() * sign)


def curve_kind(edge: TopoDS_Edge) -> str:
    curve = BRepAdaptor_Curve(edge)
    return _CURVE_KIND.get(curve.GetType(), "other")


def is_degenerate(edge: TopoDS_Edge) -> bool:
    return bool(BRep_Tool.Degenerated_s(edge))


# --------------------------------------------------------------------------
# Stable identity
# --------------------------------------------------------------------------


def geometric_id(prefix: str, *parts: Any, precision: int = 6) -> str:
    """Content-derived id, stable across re-imports of the same file.

    OCC hands out faces in traversal order, which is not guaranteed to be
    reproducible. Deriving ids from rounded geometry instead means user
    decisions recorded against a face survive a re-analysis of the same file.
    """
    tokens = []
    for part in parts:
        if isinstance(part, (tuple, list)):
            tokens.extend(f"{float(x):.{precision}g}" for x in part)
        elif isinstance(part, float):
            tokens.append(f"{part:.{precision}g}")
        else:
            tokens.append(str(part))
    digest = hashlib.sha1("|".join(tokens).encode()).hexdigest()[:16]
    return f"{prefix}_{digest}"
