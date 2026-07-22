from __future__ import annotations

import numpy as np
import trimesh
from OCP.BRep import BRep_Tool
from OCP.BRepMesh import BRepMesh_IncrementalMesh
from OCP.TopAbs import TopAbs_REVERSED
from OCP.TopLoc import TopLoc_Location
from OCP.TopoDS import TopoDS_Face, TopoDS_Shape

# Chord deflection as a fraction of the model's bounding-box diagonal. Small
# enough that cylinders and fillets look round, large enough to stay fast.
DEFLECTION_REL = 0.002
ANGULAR_DEFLECTION = 0.35


def ensure_mesh(shape: TopoDS_Shape, diagonal: float) -> None:
    """Triangulate every face of `shape` in place (idempotent per shape)."""
    deflection = max(diagonal * DEFLECTION_REL, 1e-4)
    BRepMesh_IncrementalMesh(shape, deflection, False, ANGULAR_DEFLECTION, True)


def triangulate_face(face: TopoDS_Face) -> tuple[np.ndarray, np.ndarray] | None:
    """Return (vertices Nx3, triangles Mx3) for one face, or None if unmeshed.

    Triangles are wound so their normal points out of the solid, honouring the
    face orientation, so lighting in the viewer is correct without a normal pass.
    """
    location = TopLoc_Location()
    tri = BRep_Tool.Triangulation_s(face, location)
    if tri is None:
        return None

    trsf = location.Transformation()
    n_nodes = tri.NbNodes()
    vertices = np.empty((n_nodes, 3), dtype=np.float32)
    for i in range(1, n_nodes + 1):
        p = tri.Node(i).Transformed(trsf)
        vertices[i - 1] = (p.X(), p.Y(), p.Z())

    reversed_face = face.Orientation() == TopAbs_REVERSED
    n_tris = tri.NbTriangles()
    triangles = np.empty((n_tris, 3), dtype=np.int64)
    for i in range(1, n_tris + 1):
        a, b, c = tri.Triangle(i).Get()  # 1-indexed node ids
        if reversed_face:
            b, c = c, b
        triangles[i - 1] = (a - 1, b - 1, c - 1)

    return vertices, triangles


def assemble_glb(face_meshes: list[tuple[str, np.ndarray, np.ndarray]]) -> bytes:
    """Build a GLB whose every scene node is named by its face id.

    One node per face keeps face identity all the way into three.js, where a ray
    hit yields `object.name == face_id`. Fine for MVP model sizes; a merged
    buffer with draw-range groups is the scaling path later.
    """
    scene = trimesh.Scene()
    for face_id, vertices, triangles in face_meshes:
        if len(triangles) == 0:
            continue
        mesh = trimesh.Trimesh(vertices=vertices, faces=triangles, process=False)
        scene.add_geometry(mesh, geom_name=face_id, node_name=face_id)
    if not scene.geometry:
        # Degenerate but valid: an empty scene still exports.
        scene.add_geometry(trimesh.Trimesh())
    return scene.export(file_type="glb")
