"""Synthetic CAD bodies with known ground truth.

Each builder constructs an OCC solid whose feature parameters (fillet radius,
hole diameter, pocket depth, ...) are fixed by construction, so tests can assert
that the detectors recover exactly those numbers. The same builders feed the
`generate_testdata` CLI that writes STEP pairs into testdata/.

Convention: the *original* carries the detail, the *defeatured* model has it
removed -- the real defeaturing direction. A pair therefore isolates one feature
type, which keeps the ground truth unambiguous.
"""

from __future__ import annotations

from OCP.BRepAlgoAPI import BRepAlgoAPI_Cut, BRepAlgoAPI_Fuse
from OCP.BRepBuilderAPI import BRepBuilderAPI_Transform
from OCP.BRepFilletAPI import BRepFilletAPI_MakeChamfer, BRepFilletAPI_MakeFillet
from OCP.BRepGProp import BRepGProp
from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox, BRepPrimAPI_MakeCylinder
from OCP.gp import gp_Ax2, gp_Dir, gp_Pnt, gp_Trsf, gp_Vec
from OCP.GProp import GProp_GProps
from OCP.TopAbs import TopAbs_EDGE
from OCP.TopExp import TopExp_Explorer
from OCP.TopoDS import TopoDS, TopoDS_Edge, TopoDS_Shape

# Base block shared by every fixture. Chosen so features sit comfortably inside.
DX, DY, DZ = 60.0, 40.0, 20.0


# --------------------------------------------------------------------------
# Primitives and helpers
# --------------------------------------------------------------------------


def base_box(dx: float = DX, dy: float = DY, dz: float = DZ) -> TopoDS_Shape:
    return BRepPrimAPI_MakeBox(dx, dy, dz).Shape()


def _box_at(x: float, y: float, z: float, dx: float, dy: float, dz: float) -> TopoDS_Shape:
    return BRepPrimAPI_MakeBox(gp_Pnt(x, y, z), dx, dy, dz).Shape()


def _cyl(x: float, y: float, z: float, radius: float, height: float, axis=(0, 0, 1)) -> TopoDS_Shape:
    ax = gp_Ax2(gp_Pnt(x, y, z), gp_Dir(*axis))
    return BRepPrimAPI_MakeCylinder(ax, radius, height).Shape()


def _cut(a: TopoDS_Shape, b: TopoDS_Shape) -> TopoDS_Shape:
    op = BRepAlgoAPI_Cut(a, b)
    op.Build()
    return op.Shape()


def _fuse(a: TopoDS_Shape, b: TopoDS_Shape) -> TopoDS_Shape:
    op = BRepAlgoAPI_Fuse(a, b)
    op.Build()
    return op.Shape()


def _translate(shape: TopoDS_Shape, dx: float, dy: float, dz: float) -> TopoDS_Shape:
    trsf = gp_Trsf()
    trsf.SetTranslation(gp_Vec(dx, dy, dz))
    return BRepBuilderAPI_Transform(shape, trsf, True).Shape()


def _edge_centroid(edge: TopoDS_Edge) -> tuple[float, float, float]:
    props = GProp_GProps()
    BRepGProp.LinearProperties_s(edge, props)
    c = props.CentreOfMass()
    return c.X(), c.Y(), c.Z()


def _edge_length(edge: TopoDS_Edge) -> float:
    props = GProp_GProps()
    BRepGProp.LinearProperties_s(edge, props)
    return props.Mass()


def _vertical_edge_near(shape: TopoDS_Shape, x: float, y: float, dz: float = DZ) -> TopoDS_Edge:
    """The Z-parallel edge of a box whose XY position is closest to (x, y)."""
    best: TopoDS_Edge | None = None
    best_d = float("inf")
    exp = TopExp_Explorer(shape, TopAbs_EDGE)
    while exp.More():
        edge = TopoDS.Edge_s(exp.Current())
        cx, cy, cz = _edge_centroid(edge)
        # A vertical edge spans the full height and sits at mid height.
        if abs(_edge_length(edge) - dz) < 1e-6 and abs(cz - dz / 2) < 1e-6:
            d = (cx - x) ** 2 + (cy - y) ** 2
            if d < best_d:
                best_d, best = d, edge
        exp.Next()
    if best is None:
        raise RuntimeError("no vertical edge found")
    return best


def _obround_cutter(x0: float, x1: float, y: float, radius: float, z_top: float, depth: float):
    """Rounded-end slot cutter: a box capped by two half cylinders."""
    z0 = z_top - depth
    body = _box_at(x0, y - radius, z0, x1 - x0, 2 * radius, depth + 1.0)
    c0 = _cyl(x0, y, z0, radius, depth + 1.0)
    c1 = _cyl(x1, y, z0, radius, depth + 1.0)
    return _fuse(_fuse(body, c0), c1)


# --------------------------------------------------------------------------
# Feature builders (original = with feature)
# --------------------------------------------------------------------------

FILLET_RADIUS = 4.0
CHAMFER_DIST = 5.0
HOLE_DIAMETER = 10.0
POCKET = dict(dx=16.0, dy=12.0, depth=8.0, cx=30.0, cy=20.0)
SLOT = dict(x0=40.0, x1=52.0, y=20.0, radius=4.0, depth=6.0)
BOSS = dict(x=45.0, y=10.0, diameter=10.0, height=8.0)
RIB = dict(dx=30.0, dy=3.0, height=10.0, cx=30.0, cy=30.0)


def with_fillet() -> TopoDS_Shape:
    box = base_box()
    mk = BRepFilletAPI_MakeFillet(box)
    mk.Add(FILLET_RADIUS, _vertical_edge_near(box, 0.0, 0.0))
    mk.Build()
    return mk.Shape()


def with_chamfer() -> TopoDS_Shape:
    box = base_box()
    mk = BRepFilletAPI_MakeChamfer(box)
    mk.Add(CHAMFER_DIST, _vertical_edge_near(box, DX, 0.0))
    mk.Build()
    return mk.Shape()


def with_hole() -> TopoDS_Shape:
    drill = _cyl(15.0, 20.0, -1.0, HOLE_DIAMETER / 2, DZ + 2.0)
    return _cut(base_box(), drill)


def with_pocket() -> TopoDS_Shape:
    p = POCKET
    cutter = _box_at(p["cx"] - p["dx"] / 2, p["cy"] - p["dy"] / 2, DZ - p["depth"], p["dx"], p["dy"], p["depth"] + 1.0)
    return _cut(base_box(), cutter)


def with_slot() -> TopoDS_Shape:
    s = SLOT
    return _cut(base_box(), _obround_cutter(s["x0"], s["x1"], s["y"], s["radius"], DZ, s["depth"]))


def with_boss() -> TopoDS_Shape:
    b = BOSS
    return _fuse(base_box(), _cyl(b["x"], b["y"], DZ, b["diameter"] / 2, b["height"]))


def with_rib() -> TopoDS_Shape:
    r = RIB
    rib = _box_at(r["cx"] - r["dx"] / 2, r["cy"] - r["dy"] / 2, DZ, r["dx"], r["dy"], r["height"])
    return _fuse(base_box(), rib)


def with_all_features() -> TopoDS_Shape:
    """Realistic multi-feature part: fillet + hole + pocket + boss at once."""
    shape = base_box()
    # Fillet first (operates on the pristine box edge), then cut/fuse the rest.
    mk = BRepFilletAPI_MakeFillet(shape)
    mk.Add(FILLET_RADIUS, _vertical_edge_near(shape, 0.0, 0.0))
    mk.Build()
    shape = mk.Shape()
    shape = _cut(shape, _cyl(15.0, 20.0, -1.0, HOLE_DIAMETER / 2, DZ + 2.0))
    p = POCKET
    shape = _cut(shape, _box_at(p["cx"] - p["dx"] / 2, p["cy"] - p["dy"] / 2, DZ - p["depth"], p["dx"], p["dy"], p["depth"] + 1.0))
    b = BOSS
    shape = _fuse(shape, _cyl(b["x"], b["y"], DZ, b["diameter"] / 2, b["height"]))
    return shape


def moved_wall() -> TopoDS_Shape:
    """A plain box shortened in X: a planar face has moved, matching no named
    feature. Exercises the 'nothing is lost' path -- must surface as unknown."""
    return base_box(dx=DX - 2.0)
