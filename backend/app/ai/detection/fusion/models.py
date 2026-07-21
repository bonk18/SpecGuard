from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any

class RiskAssessment(BaseModel):
    assessment_id: str
    timestamp: str
    zone_id: str
    overall_risk_score: float
    severity: str
    confidence: float
    primary_hazard: str
    secondary_hazards: List[str]
    hazard_scores: Dict[str, float]
    
    baseline_alarm_status: bool
    baseline_detection_time: Optional[str]
    compound_detection_time: Optional[str]
    
    lead_time_vs_baseline: Optional[float] # seconds
    lead_time_vs_incident: Optional[float] # seconds
    lead_time_category: Optional[str]
    lead_time_basis: Optional[str]
    
    triggered_rules: List[str]
    contribution_breakdown: Dict[str, float]
    evidence: Dict[str, Any]
    missing_evidence: List[str]
    data_quality_issues: List[str]
    explanation: str
    
    model_versions: Dict[str, str]
    configuration_version: str
