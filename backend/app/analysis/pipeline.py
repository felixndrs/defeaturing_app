"""Analysis pipeline: original + defeatured models in, an AnalysisRun out.

Stages run in sequence and record their own progress, so the API can report a
percentage while a long model is processed. Each stage is a plain function of
the run state, which keeps them individually testable and makes adding a stage
(boolean analysis, mesh reconstruction) a local change.
"""

from __future__ import annotations

import time
from datetime import datetime, timezone

from ..domain.enums import FeatureType, RunStatus, StageStatus
from ..domain.models import AnalysisRun, GeometryModel, RunStatistics, StageResult
from . import clustering
from .context import AnalysisContext
from .detectors import FeatureCluster, available_detectors, build_unknown
from .pairing import pair_faces


def analyze(
    run_id: str,
    project_id: str,
    original: GeometryModel,
    defeatured: GeometryModel,
    original_shape=None,
    defeatured_shape=None,
    area_rel_tol: float = 1e-3,
) -> AnalysisRun:
    run = AnalysisRun(id=run_id, project_id=project_id, status=RunStatus.RUNNING)
    ctx = AnalysisContext(
        original=original,
        defeatured=defeatured,
        original_shape=original_shape,
        defeatured_shape=defeatured_shape,
    )

    try:
        pairing = _stage(run, "pairing", lambda: pair_faces(original, defeatured, area_rel_tol))
        clusters = _stage(run, "clustering", lambda: _make_clusters(pairing, ctx))
        features = _stage(run, "detection", lambda: _detect(clusters, ctx))
        run.features = features
        _stage(run, "statistics", lambda: _statistics(run, original, defeatured, pairing))
        run.status = RunStatus.DONE
    except Exception as exc:  # noqa: BLE001 - surface any stage failure to the client
        run.status = RunStatus.FAILED
        run.error = f"{type(exc).__name__}: {exc}"
    finally:
        run.finished_at = datetime.now(timezone.utc)
    return run


def _stage(run: AnalysisRun, name: str, fn):
    stage = StageResult(name=name, status=StageStatus.RUNNING)
    run.stages.append(stage)
    t0 = time.perf_counter()
    try:
        result = fn()
        stage.status = StageStatus.DONE
        return result
    except Exception as exc:  # noqa: BLE001
        stage.status = StageStatus.FAILED
        stage.message = f"{type(exc).__name__}: {exc}"
        raise
    finally:
        stage.duration_s = round(time.perf_counter() - t0, 4)


def _make_clusters(pairing, ctx: AnalysisContext) -> list[FeatureCluster]:
    clusters: list[FeatureCluster] = []

    removed_groups = clustering.cluster_faces(pairing.removed, ctx.original)
    for faces in removed_groups:
        cluster = FeatureCluster(faces=faces, added=False)
        sub = ctx.region_is_subtractive(faces)
        if sub is None:
            # No live solid to probe; fall back to the global volume change.
            sub = ctx.defeatured.volume >= ctx.original.volume
        cluster.subtractive = sub
        clusters.append(cluster)

    added_groups = clustering.cluster_faces(pairing.added, ctx.defeatured)
    for faces in added_groups:
        # Faces present only in the defeatured model are added material, so from
        # the detectors' point of view they are not a subtractive feature.
        clusters.append(FeatureCluster(faces=faces, added=True, subtractive=False))

    return clusters


def _detect(clusters: list[FeatureCluster], ctx: AnalysisContext):
    detectors = available_detectors()
    features = []
    for cluster in clusters:
        claimed = None
        for detector in detectors:
            claimed = detector.detect(cluster, ctx)
            if claimed is not None:
                break
        features.append(claimed if claimed is not None else build_unknown(cluster))
    return features


def _statistics(run: AnalysisRun, original, defeatured, pairing) -> None:
    counts: dict[str, int] = {}
    for f in run.features:
        counts[f.type.value] = counts.get(f.type.value, 0) + 1

    run.statistics = RunStatistics(
        original_face_count=len(original.faces),
        defeatured_face_count=len(defeatured.faces),
        paired_face_count=len(pairing.matched),
        unpaired_original_face_count=len(pairing.removed),
        unpaired_defeatured_face_count=len(pairing.added),
        volume_original=original.volume,
        volume_defeatured=defeatured.volume,
        feature_counts=counts,
        unknown_count=counts.get(FeatureType.UNKNOWN.value, 0),
    )
