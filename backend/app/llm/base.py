"""LLM provider contract and registry (the third extension point).

A provider turns evidence bundles into assessments. The registry lets the active
provider be chosen by config (claude | null | ...), and the null provider keeps
the whole pipeline runnable offline and free during development and tests.

Providers see *evidence only* -- measured numbers and the detector's proposed
type -- never the raw geometry. That keeps the assessment grounded and auditable:
it can cite evidence ids, and it cannot invent geometry it never saw.
"""

from __future__ import annotations

import abc
from dataclasses import dataclass, field

from ..domain.models import Assessment


@dataclass
class FeatureEvidence:
    feature_id: str
    feature_type: str
    detector_confidence: float
    parameters: dict
    evidence: list[dict]  # [{id, kind, description, values}]


@dataclass
class AssessmentRequest:
    features: list[FeatureEvidence]
    model_stats: dict = field(default_factory=dict)


@dataclass
class AssessmentResponse:
    summary: str
    per_feature: dict[str, Assessment]  # keyed by feature_id


class LLMProvider(abc.ABC):
    name: str

    @abc.abstractmethod
    def assess(self, request: AssessmentRequest) -> AssessmentResponse:
        ...


_PROVIDERS: dict[str, type[LLMProvider]] = {}


def register_provider(cls: type[LLMProvider]) -> type[LLMProvider]:
    _PROVIDERS[cls.name] = cls
    return cls


def get_provider(name: str) -> LLMProvider:
    if name not in _PROVIDERS:
        raise KeyError(
            f"Unknown LLM provider {name!r}. Available: {', '.join(sorted(_PROVIDERS))}"
        )
    return _PROVIDERS[name]()


def available_providers() -> list[str]:
    return sorted(_PROVIDERS)
