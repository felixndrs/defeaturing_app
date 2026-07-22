"""Group loose faces into connected feature clusters.

A pocket is five faces (a floor and four walls) that share edges; a fillet is a
single face. Grouping removed faces by shared edges turns the flat 'removed'
list into candidate features the detectors can classify one cluster at a time.
"""

from __future__ import annotations

from ..domain.models import BBox, Face, GeometryModel
from . import vec


def cluster_faces(faces: list[Face], model: GeometryModel) -> list[list[Face]]:
    """Connected components of `faces`, where two faces connect if they share an
    edge in `model`."""
    face_ids = {f.id for f in faces}
    by_id = {f.id: f for f in faces}

    # Adjacency via shared edges, restricted to the given face set.
    adj: dict[str, set[str]] = {fid: set() for fid in face_ids}
    for edge in model.edges:
        members = [fid for fid in edge.face_ids if fid in face_ids]
        for a in members:
            for b in members:
                if a != b:
                    adj[a].add(b)

    seen: set[str] = set()
    clusters: list[list[Face]] = []
    for fid in face_ids:
        if fid in seen:
            continue
        stack = [fid]
        component: list[Face] = []
        while stack:
            cur = stack.pop()
            if cur in seen:
                continue
            seen.add(cur)
            component.append(by_id[cur])
            stack.extend(adj[cur] - seen)
        clusters.append(component)
    return clusters


def cluster_bbox(faces: list[Face]) -> BBox | None:
    return BBox.union([f.bbox for f in faces])


def cluster_centroid(faces: list[Face]) -> vec.Vec3:
    """Area-weighted centroid of a face cluster."""
    total = sum(f.area for f in faces) or 1.0
    cx = sum(f.centroid[0] * f.area for f in faces) / total
    cy = sum(f.centroid[1] * f.area for f in faces) / total
    cz = sum(f.centroid[2] * f.area for f in faces) / total
    return (cx, cy, cz)
