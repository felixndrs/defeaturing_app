"""Prompt construction for the LLM assessment.

The model is shown evidence only -- measured numbers and the detector's proposed
type -- never raw geometry. It is instructed to cite the evidence ids it relied
on, so every statement in the engineering report is traceable and the model
cannot invent geometry it never saw.
"""

from __future__ import annotations

import json

from .base import AssessmentRequest

SYSTEM = """You are an FE (finite-element) pre-processing reviewer. You assess \
defeaturing changes: geometry a CAD engineer removed to simplify a model before \
meshing. For each detected change you are given measured evidence and the \
detector's proposed feature type -- never the raw geometry.

For every feature decide the risk of removing it for a structural FE analysis:
- low: small blends/chamfers far from load paths; negligible stiffness effect.
- medium: holes, pockets, slots, bosses; may matter near stress concentrations.
- high: ribs and load-bearing or unclassified ('unknown') changes; review by hand.

Rules:
- Base every judgement only on the evidence provided. Cite the evidence ids you used.
- If the evidence is insufficient, say so and assign lower confidence.
- Never invent dimensions or features not present in the evidence."""


def build_user_message(request: AssessmentRequest) -> str:
    features = []
    for fe in request.features:
        features.append(
            {
                "feature_id": fe.feature_id,
                "proposed_type": fe.feature_type,
                "detector_confidence": round(fe.detector_confidence, 3),
                "parameters": fe.parameters,
                "evidence": fe.evidence,
            }
        )
    payload = {"model_statistics": request.model_stats, "features": features}
    return (
        "Assess each defeaturing change below. Return a per-feature risk, a "
        "confidence in [0,1], a short rationale, and the evidence ids you cited. "
        "Also return a one-paragraph summary for the engineering report.\n\n"
        + json.dumps(payload, indent=2)
    )
