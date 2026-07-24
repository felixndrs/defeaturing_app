"""Deterministic offline provider.

Produces plausible, fully reproducible assessments with no API call, so tests
and local development cost nothing and never flake. Risk is a simple function of
feature type; the rationale cites the actual evidence so the report still reads
sensibly.
"""

from __future__ import annotations

from ..domain.enums import RiskLevel
from ..domain.models import Assessment
from .base import AssessmentRequest, AssessmentResponse, LLMProvider, register_provider

# How much removing each feature type typically matters for an FE analysis.
_RISK = {
    "hole": RiskLevel.MEDIUM,
    "pocket": RiskLevel.MEDIUM,
    "slot": RiskLevel.MEDIUM,
    "boss": RiskLevel.MEDIUM,
    "rib": RiskLevel.HIGH,       # ribs carry load; removing one can change stiffness
    "fillet": RiskLevel.LOW,
    "chamfer": RiskLevel.LOW,
    "simplified_face": RiskLevel.LOW,
    "merged_face": RiskLevel.LOW,
    "unknown": RiskLevel.HIGH,   # unclassified change: review by hand
}


@register_provider
class NullProvider(LLMProvider):
    name = "null"

    def assess(self, request: AssessmentRequest) -> AssessmentResponse:
        per_feature = {}
        for fe in request.features:
            risk = _RISK.get(fe.feature_type, RiskLevel.MEDIUM)
            params = ", ".join(f"{k}={_fmt(v)}" for k, v in fe.parameters.items() if v is not None)
            rationale = (
                f"Erkannt als {fe.feature_type} ({params or 'keine Parameter'}). "
                f"{'Kleine Verrundungen haben kaum Einfluss auf die globale Steifigkeit.' if risk is RiskLevel.LOW else ''}"
                f"{'Lasttragend oder unklassifiziert; vor dem Verwerfen prüfen.' if risk is RiskLevel.HIGH else ''}"
                f"{'Moderater Einfluss; beibehalten, falls nahe an Spannungskonzentrationen.' if risk is RiskLevel.MEDIUM else ''}"
            ).strip()
            per_feature[fe.feature_id] = Assessment(
                rationale=rationale,
                risk=risk,
                confidence=fe.detector_confidence,
                cited_evidence_ids=[e["id"] for e in fe.evidence],
                provider=self.name,
            )

        n = len(request.features)
        high = sum(1 for a in per_feature.values() if a.risk is RiskLevel.HIGH)
        summary = (
            f"{n} Geometrieänderung(en) erkannt. "
            f"{high} als hohes Risiko eingestuft und sollten vor der Übernahme geprüft werden."
        )
        return AssessmentResponse(summary=summary, per_feature=per_feature)


def _fmt(v) -> str:
    if isinstance(v, float):
        return f"{v:.3g}"
    return str(v)
