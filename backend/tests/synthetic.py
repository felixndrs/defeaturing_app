"""Backwards-compatible re-exports.

The canonical body builders now live in app.testing.bodies so that both the CLI
and the tests share one source of truth. These aliases keep older imports and
the box/fillet/hole helpers used by the importer tests working.
"""

from app.testing.bodies import base_box as make_box  # noqa: F401
from app.testing.bodies import (  # noqa: F401
    with_boss,
    with_chamfer,
    with_fillet,
    with_hole,
    with_pocket,
    with_rib,
    with_slot,
)


def make_box_with_fillet(radius: float = 3.0, dx: float = 40.0, dy: float = 30.0, dz: float = 20.0):
    """All-edge fillet on a custom-sized box, as the importer tests expect."""
    from OCP.BRepFilletAPI import BRepFilletAPI_MakeFillet
    from OCP.TopAbs import TopAbs_EDGE
    from OCP.TopExp import TopExp_Explorer
    from OCP.TopoDS import TopoDS

    box = make_box(dx, dy, dz)
    builder = BRepFilletAPI_MakeFillet(box)
    exp = TopExp_Explorer(box, TopAbs_EDGE)
    while exp.More():
        builder.Add(radius, TopoDS.Edge_s(exp.Current()))
        exp.Next()
    builder.Build()
    return builder.Shape()


def make_box_with_hole(diameter: float = 8.0, dx: float = 40.0, dy: float = 30.0, dz: float = 20.0):
    from OCP.BRepAlgoAPI import BRepAlgoAPI_Cut
    from OCP.BRepPrimAPI import BRepPrimAPI_MakeCylinder
    from OCP.gp import gp_Ax2, gp_Dir, gp_Pnt

    box = make_box(dx, dy, dz)
    axis = gp_Ax2(gp_Pnt(dx / 2, dy / 2, -1.0), gp_Dir(0, 0, 1))
    drill = BRepPrimAPI_MakeCylinder(axis, diameter / 2, dz + 2.0).Shape()
    cut = BRepAlgoAPI_Cut(box, drill)
    cut.Build()
    return cut.Shape()
