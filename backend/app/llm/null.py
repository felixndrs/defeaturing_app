"""Deterministic offline provider.

Produces plausible, fully reproducible assessments with no API call, so tests
and local development cost nothing and never flake. Risk is a simple function of
feature type; the rationale cites the actual evidence so the report still reads
sensibly.

Every text is produced in both UI languages, matching what the Claude provider
returns -- the app's language switch must work without a second model call.
"""

from __future__ import annotations

from .. import i18n
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

# Second sentence of the rationale, keyed by risk. Both languages say the same
# thing: what removing this geometry does to the simulation result.
_RISK_NOTE = {
    RiskLevel.LOW: (
        "Kleine Verrundungen haben kaum Einfluss auf die globale Steifigkeit; "
        "eine Verfälschung des Simulationsergebnisses ist nicht zu erwarten.",
        "Small blends barely affect global stiffness; no distortion of the "
        "simulation result is expected.",
    ),
    RiskLevel.MEDIUM: (
        "Moderater Einfluss; beibehalten, falls in diesem Bereich Spannungen "
        "ausgewertet werden.",
        "Moderate effect; keep it if stresses are evaluated in this region.",
    ),
    RiskLevel.HIGH: (
        "Lasttragend oder unklassifiziert; das Entfernen kann das "
        "Simulationsergebnis deutlich verfälschen. Vor der Übernahme prüfen.",
        "Load-bearing or unclassified; removing it may distort the simulation "
        "result significantly. Review before accepting.",
    ),
}


@register_provider
class NullProvider(LLMProvider):
    name = "null"

    def assess(self, request: AssessmentRequest) -> AssessmentResponse:
        per_feature = {}
        for fe in request.features:
            risk = _RISK.get(fe.feature_type, RiskLevel.MEDIUM)
            note_de, note_en = _RISK_NOTE[risk]
            per_feature[fe.feature_id] = Assessment(
                rationale=(
                    f"Erkannt als {i18n.feature_type(fe.feature_type, 'de').lower()} "
                    f"({_params(fe.parameters, 'de') or 'keine Parameter'}). {note_de}"
                ),
                rationale_en=(
                    f"Detected as {i18n.feature_type(fe.feature_type, 'en').lower()} "
                    f"({_params(fe.parameters, 'en') or 'no parameters'}). {note_en}"
                ),
                risk=risk,
                confidence=fe.detector_confidence,
                cited_evidence_ids=[e["id"] for e in fe.evidence],
                provider=self.name,
            )

        n = len(request.features)
        high = sum(1 for a in per_feature.values() if a.risk is RiskLevel.HIGH)
        summary = (
            f"{n} Geometrieänderung(en) erkannt. {high} davon bergen ein hohes Risiko, "
            "das Ergebnis einer FE-Simulation zu verfälschen, und sollten vor der "
            "Übernahme geprüft werden."
        )
        summary_en = (
            f"{n} geometry change(s) detected. {high} of them carry a high risk of "
            "distorting the result of an FE simulation and should be reviewed before "
            "being accepted."
        )
        return AssessmentResponse(summary=summary, summary_en=summary_en, per_feature=per_feature)


def _params(parameters: dict, lang: i18n.Lang) -> str:
    """`Radius 5, Tiefe 20` -- readable in the rationale, in the report's language."""
    return ", ".join(
        f"{i18n.parameter(k, lang)} {_fmt(v)}"
        for k, v in parameters.items()
        if v is not None and not isinstance(v, (list, tuple))
    )


def _fmt(v) -> str:
    if isinstance(v, float):
        return f"{v:.3g}"
    return str(v)
