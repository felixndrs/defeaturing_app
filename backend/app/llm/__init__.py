"""LLM package.

Importing it registers the built-in providers. `assess_run` picks the provider
named by config, runs it over the run's features, and writes the assessments and
summary back onto the run in place.
"""

from __future__ import annotations

from ..config import get_settings
from ..domain.models import AnalysisRun, GeometryModel
from .base import (  # noqa: F401
    AssessmentRequest,
    FeatureEvidence,
    available_providers,
    get_provider,
)
from . import null  # noqa: F401  (registers NullProvider)

try:  # Claude provider needs the anthropic package; keep it optional.
    from . import claude  # noqa: F401
except Exception:  # pragma: no cover - anthropic always installed here
    pass


def assess_run(run: AnalysisRun, original: GeometryModel, defeatured: GeometryModel) -> None:
    """Run the configured LLM provider over `run` and attach assessments."""
    settings = get_settings()
    provider = get_provider(settings.llm_provider)

    features = [
        FeatureEvidence(
            feature_id=f.id,
            feature_type=f.type.value,
            detector_confidence=f.confidence,
            parameters=f.parameters,
            evidence=[
                {"id": e.id, "kind": e.kind, "description": e.description, "values": e.values}
                for e in f.evidence
            ],
        )
        for f in run.features
    ]
    stats = {
        "original_face_count": run.statistics.original_face_count,
        "defeatured_face_count": run.statistics.defeatured_face_count,
        "volume_original": run.statistics.volume_original,
        "volume_defeatured": run.statistics.volume_defeatured,
        "feature_counts": run.statistics.feature_counts,
    }

    result = provider.assess(AssessmentRequest(features=features, model_stats=stats))

    for feature in run.features:
        if (assessment := result.per_feature.get(feature.id)) is not None:
            feature.assessment = assessment
    run.llm_summary = result.summary
