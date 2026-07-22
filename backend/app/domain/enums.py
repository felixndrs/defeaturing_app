from enum import StrEnum


class SourceFormat(StrEnum):
    STEP = "step"
    STL = "stl"
    OPTISTRUCT = "optistruct"


class ModelRole(StrEnum):
    ORIGINAL = "original"
    DEFEATURED = "defeatured"


class SurfaceKind(StrEnum):
    """Analytic surface type of a face, from BRepAdaptor_Surface."""

    PLANE = "plane"
    CYLINDER = "cylinder"
    CONE = "cone"
    SPHERE = "sphere"
    TORUS = "torus"
    BSPLINE = "bspline"
    BEZIER = "bezier"
    REVOLUTION = "revolution"
    EXTRUSION = "extrusion"
    OFFSET = "offset"
    OTHER = "other"


class FeatureType(StrEnum):
    """Recognised defeaturing feature types.

    Open by design: new detectors add members here without any schema change,
    and UNKNOWN guarantees that no geometry change is ever dropped.
    """

    FILLET = "fillet"
    CHAMFER = "chamfer"
    HOLE = "hole"
    SLOT = "slot"
    POCKET = "pocket"
    BOSS = "boss"
    RIB = "rib"
    SIMPLIFIED_FACE = "simplified_face"
    MERGED_FACE = "merged_face"
    UNKNOWN = "unknown"


class ChangeStatus(StrEnum):
    REMOVED = "removed"
    ADDED = "added"
    MODIFIED = "modified"


class UserDecision(StrEnum):
    UNDECIDED = "undecided"
    ACCEPT = "accept"
    REJECT = "reject"


class RiskLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class RunStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"


class StageStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    SKIPPED = "skipped"
    FAILED = "failed"
