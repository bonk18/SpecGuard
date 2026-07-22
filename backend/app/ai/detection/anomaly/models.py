from pydantic import BaseModel, Field
from typing import List, Dict, Optional

class FeatureContribution(BaseModel):
    feature_name: str
    contribution_score: float
    is_approximate: bool = True

class AnomalyResult(BaseModel):
    raw_model_score: float
    normalized_score: float  # 0 to 1
    is_anomalous: bool
    model_version: str
    feature_contributions: List[FeatureContribution] = Field(default_factory=list)
    data_quality_status: str
    confidence: float
    top_deviating_features: List[str] = Field(default_factory=list)
