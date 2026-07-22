from __future__ import annotations

from pathlib import Path

from OCP.IFSelect import IFSelect_ReturnStatus
from OCP.STEPControl import STEPControl_Reader
from OCP.TopoDS import TopoDS_Shape

from ..domain.enums import ModelRole, SourceFormat
from ..domain.models import BBox, Edge, Face, GeometryModel, Solid
from .base import ImportError_, Importer
from .occ_utils import (
    bounding_box,
    curve_kind,
    edge_length,
    face_area_centroid,
    face_normal,
    geometric_id,
    is_degenerate,
    iter_edges,
    iter_faces,
    iter_solids,
    solid_volume_area,
    surface_kind_and_params,
)
from .registry import register_importer

# Cache of imported OCC shapes, keyed by model id. The analysis stages need the
# live TopoDS_Shape, which cannot be serialised into the domain model.
_SHAPE_CACHE: dict[str, TopoDS_Shape] = {}


def get_shape(model_id: str) -> TopoDS_Shape | None:
    return _SHAPE_CACHE.get(model_id)


def cache_shape(model_id: str, shape: TopoDS_Shape) -> None:
    _SHAPE_CACHE[model_id] = shape


@register_importer
class StepImporter(Importer):
    name = "STEP"
    source_format = SourceFormat.STEP
    extensions = (".step", ".stp")

    def load(self, path: Path, role: ModelRole, model_id: str) -> GeometryModel:
        shape = self._read_shape(path)
        cache_shape(model_id, shape)
        return build_model(shape, path, role, model_id, SourceFormat.STEP)

    def _read_shape(self, path: Path) -> TopoDS_Shape:
        reader = STEPControl_Reader()
        status = reader.ReadFile(str(path))
        if status != IFSelect_ReturnStatus.IFSelect_RetDone:
            raise ImportError_(f"OpenCascade could not read {path.name} (status {status})")
        reader.TransferRoots()
        shape = reader.OneShape()
        if shape.IsNull():
            raise ImportError_(f"{path.name} contains no transferable geometry")
        return shape


def build_model(
    shape: TopoDS_Shape,
    path: Path,
    role: ModelRole,
    model_id: str,
    source_format: SourceFormat,
) -> GeometryModel:
    """Traverse an OCC shape into the internal data model.

    Shared with the synthetic test-body builder, so keep it free of STEP
    specifics.
    """
    faces: list[Face] = []
    face_id_by_hash: dict[int, str] = {}

    for occ_face in iter_faces(shape):
        area, centroid = face_area_centroid(occ_face)
        kind, params = surface_kind_and_params(occ_face)
        fid = geometric_id("f", kind.value, area, centroid)
        # Two faces can share a geometric id only if they are truly congruent;
        # disambiguate the rare collision so ids stay unique within a model.
        if fid in {f.id for f in faces}:
            fid = geometric_id("f", kind.value, area, centroid, len(faces))
        face_id_by_hash[hash(occ_face)] = fid
        faces.append(
            Face(
                id=fid,
                surface_kind=kind,
                area=area,
                centroid=centroid,
                normal=face_normal(occ_face),
                bbox=bounding_box(occ_face),
                surface_params=params,
            )
        )

    face_by_id = {f.id: f for f in faces}

    edges: list[Edge] = []
    seen_edges: set[str] = set()
    for occ_edge in iter_edges(shape):
        if is_degenerate(occ_edge):
            continue
        length = edge_length(occ_edge)
        ebox = bounding_box(occ_edge)
        eid = geometric_id("e", curve_kind(occ_edge), length, ebox.min, ebox.max)
        if eid in seen_edges:
            continue
        seen_edges.add(eid)
        edges.append(Edge(id=eid, length=length, curve_kind=curve_kind(occ_edge), bbox=ebox))

    _link_faces_and_edges(shape, faces, edges, face_id_by_hash)

    solids: list[Solid] = []
    total_volume = 0.0
    for index, occ_solid in enumerate(iter_solids(shape)):
        volume, area = solid_volume_area(occ_solid)
        total_volume += volume
        solid_face_ids = []
        for occ_face in iter_faces(occ_solid):
            fid = face_id_by_hash.get(hash(occ_face))
            if fid:
                solid_face_ids.append(fid)
                if (face := face_by_id.get(fid)) is not None:
                    face.solid_index = index
        solids.append(
            Solid(
                index=index,
                volume=volume,
                area=area,
                bbox=bounding_box(occ_solid),
                face_ids=solid_face_ids,
            )
        )

    return GeometryModel(
        id=model_id,
        role=role,
        source_format=source_format,
        source_file=path.name,
        solids=solids,
        faces=faces,
        edges=edges,
        bbox=bounding_box(shape),
        volume=total_volume,
        area=sum(f.area for f in faces),
    )


def _link_faces_and_edges(
    shape: TopoDS_Shape,
    faces: list[Face],
    edges: list[Edge],
    face_id_by_hash: dict[int, str],
) -> None:
    """Populate Face.edge_ids and Edge.face_ids.

    Face adjacency via shared edges is what lets the fillet and chamfer
    detectors reason about tangency, so this link is load bearing rather than
    decorative.
    """
    edge_by_id = {e.id: e for e in edges}
    face_by_id = {f.id: f for f in faces}

    for occ_face in iter_faces(shape):
        fid = face_id_by_hash.get(hash(occ_face))
        if fid is None:
            continue
        for occ_edge in iter_edges(occ_face):
            if is_degenerate(occ_edge):
                continue
            ebox = bounding_box(occ_edge)
            eid = geometric_id(
                "e", curve_kind(occ_edge), edge_length(occ_edge), ebox.min, ebox.max
            )
            edge = edge_by_id.get(eid)
            if edge is None:
                continue
            if fid not in edge.face_ids:
                edge.face_ids.append(fid)
            face = face_by_id[fid]
            if eid not in face.edge_ids:
                face.edge_ids.append(eid)
