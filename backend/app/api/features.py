from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..domain.enums import UserDecision
from ..domain.models import AnalysisRun, FeatureChange
from ..storage import db

router = APIRouter(prefix="/analysis/{run_id}/features", tags=["features"])


class DecisionUpdate(BaseModel):
    user_decision: UserDecision | None = None
    user_comment: str | None = None


@router.get("", response_model=list[FeatureChange])
def list_features(run_id: str) -> list[FeatureChange]:
    run = _load(run_id)
    return run.features


@router.patch("/{feature_id}", response_model=FeatureChange)
def update_feature(run_id: str, feature_id: str, update: DecisionUpdate) -> FeatureChange:
    run = _load(run_id)
    feature = next((f for f in run.features if f.id == feature_id), None)
    if feature is None:
        raise HTTPException(status_code=404, detail="Feature not found")

    if update.user_decision is not None:
        feature.user_decision = update.user_decision
    if update.user_comment is not None:
        feature.user_comment = update.user_comment

    db.save(run, parent_id=run.project_id)
    return feature


def _load(run_id: str) -> AnalysisRun:
    run = db.load(AnalysisRun, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return run
