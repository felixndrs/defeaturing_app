from __future__ import annotations

from pathlib import Path

from OCP.IFSelect import IFSelect_ReturnStatus
from OCP.Interface import Interface_Static
from OCP.STEPControl import STEPControl_AsIs, STEPControl_Writer
from OCP.TopoDS import TopoDS_Shape


def write_step(shape: TopoDS_Shape, path: Path) -> Path:
    """Write an OCC shape to a STEP file (AP214)."""
    Interface_Static.SetCVal_s("write.step.schema", "AP214")
    writer = STEPControl_Writer()
    writer.Transfer(shape, STEPControl_AsIs)
    status = writer.Write(str(path))
    if status != IFSelect_ReturnStatus.IFSelect_RetDone:
        raise RuntimeError(f"failed to write {path} (status {status})")
    return path
