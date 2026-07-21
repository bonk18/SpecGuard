from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any

class RuleCondition(BaseModel):
    feature: str
    operator: str  # eq, neq, gt, gte, lt, lte, in, not_in
    value: Any

class EscalationCondition(BaseModel):
    when: RuleCondition
    score_delta: float

class CompoundRuleDef(BaseModel):
    rule_id: str
    name: str
    description: str
    hazard_type: str
    applicable_zones: List[str]
    severity: str
    base_score: float
    confidence: float = 1.0
    minimum_data_quality: str = "VALID"
    conditions: Dict[str, List[RuleCondition]] = Field(default_factory=dict)
    escalation: List[EscalationCondition] = Field(default_factory=list)
    cooldown_seconds: int = 300
    enabled: bool = True

class RuleResult(BaseModel):
    rule_id: str
    rule_name: str
    hazard_type: str
    zone_id: str
    score_contribution: float
    severity: str
    confidence: float
    trigger_timestamp: str
    evidence: Dict[str, Any]
    missing_evidence: List[str]
    source_feature_values: Dict[str, Any]
    human_readable_explanation: str
    machine_readable_explanation: str
    escalation_factors: List[str]

class RuleEngineResult(BaseModel):
    timestamp: str
    zone_id: str
    triggered_rules: List[RuleResult]
