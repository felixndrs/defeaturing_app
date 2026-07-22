"""Claude-backed assessment provider.

Uses the Anthropic SDK with structured outputs (messages.parse) so the response
validates against a schema before it ever reaches the report. A failed or
malformed call raises; the caller (tasks.worker) treats assessment as optional
and never lets it fail the analysis run.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

from ..config import get_settings
from ..domain.enums import RiskLevel
from ..domain.models import Assessment
from .base import AssessmentRequest, AssessmentResponse, LLMProvider, register_provider
from .prompts import SYSTEM, build_user_message


class _FeatureAssessment(BaseModel):
    feature_id: str
    risk: Literal["low", "medium", "high"]
    confidence: float
    rationale: str
    cited_evidence_ids: list[str]


class _RunAssessment(BaseModel):
    summary: str
    features: list[_FeatureAssessment]


@register_provider
class ClaudeProvider(LLMProvider):
    name = "claude"

    def assess(self, request: AssessmentRequest) -> AssessmentResponse:
        import anthropic

        settings = get_settings()
        client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

        response = client.messages.parse(
            model=settings.llm_model,
            max_tokens=16000,
            system=SYSTEM,
            messages=[{"role": "user", "content": build_user_message(request)}],
            output_format=_RunAssessment,
        )
        parsed: _RunAssessment = response.parsed_output

        per_feature: dict[str, Assessment] = {}
        for fa in parsed.features:
            per_feature[fa.feature_id] = Assessment(
                rationale=fa.rationale,
                risk=RiskLevel(fa.risk),
                confidence=max(0.0, min(1.0, fa.confidence)),
                cited_evidence_ids=fa.cited_evidence_ids,
                provider=self.name,
                model=settings.llm_model,
            )
        return AssessmentResponse(summary=parsed.summary, per_feature=per_feature)
