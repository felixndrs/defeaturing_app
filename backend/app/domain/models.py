"""Internal data model shared by every stage of the application.

This module is the contract between importers, analysis stages, detectors, the
LLM layer and reporting. It deliberately contains no OpenCascade types so that
importers for meshes (STL) or FEM decks can produce the same structures later.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, PrivateAttr

from .enums import (
    ChangeStatus,
    FeatureType,
    ModelRole,
    RiskLevel,
    RunStatus,
    SourceFormat,
    StageStatus,
    SurfaceKind,
    UserDecision,
)

Vec3 = tuple[float, float, float]


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Base(BaseModel):
    model_config = ConfigDict(populate_by_name=True)


class BBox(Base):
    min: Vec3
    max: Vec3

    @property
    def center(self) -> Vec3:
        return tuple((a + b) / 2 for a, b in zip(self.min, self.max))  # type: ignore[return-value]

    @property
    def diagonal(self) -> float:
        return sum((b - a) ** 2 for a, b in zip(self.min, self.max)) ** 0.5

    @classmethod
    def union(cls, boxes: list["BBox"]) -> "BBox | None":
        if not boxes:
            return None
        mins = [min(b.min[i] for b in boxes) for i in range(3)]
        maxs = [max(b.max[i] for b in boxes) for i in range(3)]
        return cls(min=tuple(mins), max=tuple(maxs))  # type: ignore[arg-type]


# --------------------------------------------------------------------------
# Geometry
# --------------------------------------------------------------------------


class Face(Base):
    """One face of a solid, described by format-independent properties.

    `id` is stable for a given import of a given file: it is derived from the
    face's geometric fingerprint, not from OCC's in-memory ordering, so that
    re-importing the same file yields the same ids.
    """

    id: str
    surface_kind: SurfaceKind
    area: float
    centroid: Vec3
    normal: Vec3 | None = None
    bbox: BBox
    # Analytic parameters of the underlying surface: radius, axis, half_angle...
    surface_params: dict[str, Any] = Field(default_factory=dict)
    edge_ids: list[str] = Field(default_factory=list)
    solid_index: int = 0


class Edge(Base):
    id: str
    length: float
    curve_kind: str
    bbox: BBox
    # Faces sharing this edge; the key input for tangency/adjacency reasoning.
    face_ids: list[str] = Field(default_factory=list)


class Solid(Base):
    index: int
    volume: float
    area: float
    bbox: BBox
    face_ids: list[str] = Field(default_factory=list)


class GeometryModel(Base):
    """A fully imported model, independent of its source format."""

    id: str
    role: ModelRole
    source_format: SourceFormat
    source_file: str
    solids: list[Solid] = Field(default_factory=list)
    faces: list[Face] = Field(default_factory=list)
    edges: list[Edge] = Field(default_factory=list)
    bbox: BBox
    volume: float
    area: float
    imported_at: datetime = Field(default_factory=_now)

    # Lookup caches. Rebuilt on demand; callers that mutate faces/edges after
    # import must call invalidate_indices().
    _face_index: dict[str, Face] | None = PrivateAttr(default=None)
    _edge_index: dict[str, Edge] | None = PrivateAttr(default=None)

    def face_by_id(self, face_id: str) -> Face | None:
        if self._face_index is None:
            self._face_index = {f.id: f for f in self.faces}
        return self._face_index.get(face_id)

    def edge_by_id(self, edge_id: str) -> Edge | None:
        if self._edge_index is None:
            self._edge_index = {e.id: e for e in self.edges}
        return self._edge_index.get(edge_id)

    def invalidate_indices(self) -> None:
        self._face_index = None
        self._edge_index = None


# --------------------------------------------------------------------------
# Evidence and detected changes
# --------------------------------------------------------------------------


class Evidence(Base):
    """A single measured fact supporting a classification.

    Evidence carries numbers, not prose conclusions: it is what the LLM is
    allowed to reason over and what the report cites, so it must be traceable
    back to a concrete measurement in a named stage.
    """

    id: str
    kind: str
    description: str
    values: dict[str, float | int | str | bool] = Field(default_factory=dict)
    source_stage: str


class GeometryRefs(Base):
    original_face_ids: list[str] = Field(default_factory=list)
    defeatured_face_ids: list[str] = Field(default_factory=list)


class Assessment(Base):
    """LLM judgement about a single feature change."""

    rationale: str
    risk: RiskLevel
    confidence: float = Field(ge=0.0, le=1.0)
    cited_evidence_ids: list[str] = Field(default_factory=list)
    provider: str
    model: str | None = None


class FeatureChange(Base):
    id: str
    type: FeatureType
    status: ChangeStatus
    detector: str
    parameters: dict[str, Any] = Field(default_factory=dict)
    evidence: list[Evidence] = Field(default_factory=list)
    # Detector-side confidence, distinct from the LLM's confidence.
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    geometry_refs: GeometryRefs = Field(default_factory=GeometryRefs)
    bbox: BBox | None = None
    centroid: Vec3 | None = None
    volume_delta: float | None = None

    assessment: Assessment | None = None
    user_decision: UserDecision = UserDecision.UNDECIDED
    user_comment: str = ""

    @property
    def label(self) -> str:
        return f"{self.type.value}-{self.id[:8]}"


# --------------------------------------------------------------------------
# Analysis run
# --------------------------------------------------------------------------


class StageResult(Base):
    name: str
    status: StageStatus = StageStatus.PENDING
    duration_s: float | None = None
    message: str = ""
    stats: dict[str, Any] = Field(default_factory=dict)


class RunStatistics(Base):
    original_face_count: int = 0
    defeatured_face_count: int = 0
    paired_face_count: int = 0
    unpaired_original_face_count: int = 0
    unpaired_defeatured_face_count: int = 0
    volume_original: float = 0.0
    volume_defeatured: float = 0.0
    feature_counts: dict[str, int] = Field(default_factory=dict)
    unknown_count: int = 0

    @property
    def volume_delta(self) -> float:
        return self.volume_defeatured - self.volume_original

    @property
    def volume_delta_rel(self) -> float:
        if self.volume_original == 0:
            return 0.0
        return self.volume_delta / self.volume_original


class Project(Base):
    id: str
    name: str
    original_model_id: str | None = None
    defeatured_model_id: str | None = None
    created_at: datetime = Field(default_factory=_now)


class AnalysisRun(Base):
    id: str
    project_id: str
    status: RunStatus = RunStatus.PENDING
    stages: list[StageResult] = Field(default_factory=list)
    features: list[FeatureChange] = Field(default_factory=list)
    statistics: RunStatistics = Field(default_factory=RunStatistics)
    llm_summary: str = ""
    error: str = ""
    created_at: datetime = Field(default_factory=_now)
    finished_at: datetime | None = None

    @property
    def progress(self) -> float:
        if not self.stages:
            return 0.0
        done = sum(1 for s in self.stages if s.status in (StageStatus.DONE, StageStatus.SKIPPED))
        return done / len(self.stages)
