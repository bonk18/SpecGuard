import pytest
from datetime import datetime, timezone, timedelta
from ..features.models import FeatureVector, FeatureValue
from ..detection.rules.models import RuleEngineResult, RuleResult
from ..detection.anomaly.models import AnomalyResult
from ..detection.baseline.models import BaselineResult
from ..detection.fusion.engine import RiskFusionEngine

@pytest.fixture
def engine():
    return RiskFusionEngine("backend/app/ai/config/risk_scoring.yaml")

def test_no_risk_state(engine):
    now = datetime.now(timezone.utc)
    fv = FeatureVector(timestamp=now, zone_id="Z1")
    
    rule_res = RuleEngineResult(timestamp=now.isoformat(), zone_id="Z1", triggered_rules=[])
    anomaly_res = None
    baseline_res = []
    
    assessment = engine.fuse(fv, rule_res, anomaly_res, baseline_res)
    assert assessment.overall_risk_score == 0.0
    assert assessment.severity == "NORMAL"
    assert assessment.primary_hazard == "NONE"
    assert assessment.confidence == 100.0
    
def test_rule_severity_floor(engine):
    now = datetime.now(timezone.utc)
    fv = FeatureVector(timestamp=now, zone_id="Z1")
    
    rule_res = RuleEngineResult(timestamp=now.isoformat(), zone_id="Z1", triggered_rules=[
        RuleResult(
            rule_id="R1", rule_name="R1", hazard_type="FLASH_FIRE", zone_id="Z1",
            score_contribution=85.0, severity="CRITICAL", confidence=1.0, trigger_timestamp=now.isoformat(),
            evidence={"hydrocarbon": 10.0}, missing_evidence=[], source_feature_values={}, 
            human_readable_explanation="", machine_readable_explanation="", escalation_factors=[]
        )
    ])
    
    assessment = engine.fuse(fv, rule_res, None, [])
    assert assessment.overall_risk_score >= 85.0
    assert assessment.severity == "CRITICAL"
    assert assessment.primary_hazard == "FLASH_FIRE"

def test_anomaly_contribution(engine):
    now = datetime.now(timezone.utc)
    fv = FeatureVector(timestamp=now, zone_id="Z1")
    
    rule_res = RuleEngineResult(timestamp=now.isoformat(), zone_id="Z1", triggered_rules=[])
    anomaly_res = AnomalyResult(
        raw_model_score=0.1, normalized_score=0.9, is_anomalous=True, model_version="1",
        feature_contributions=[], data_quality_status="VALID", confidence=0.8, top_deviating_features=[]
    )
    
    assessment = engine.fuse(fv, rule_res, anomaly_res, [])
    # Should assign a high anomaly contribution to UNKNOWN_STATE
    assert assessment.overall_risk_score == 20.0
    assert assessment.primary_hazard == "UNKNOWN_STATE"

def test_lead_time_calculation(engine):
    now = datetime.now(timezone.utc)
    fv1 = FeatureVector(timestamp=now, zone_id="Z1")
    rule_res1 = RuleEngineResult(timestamp=now.isoformat(), zone_id="Z1", triggered_rules=[
         RuleResult(
            rule_id="R1", rule_name="R1", hazard_type="FIRE", zone_id="Z1",
            score_contribution=45.0, severity="WARNING", confidence=1.0, trigger_timestamp=now.isoformat(),
            evidence={}, missing_evidence=[], source_feature_values={}, 
            human_readable_explanation="", machine_readable_explanation="", escalation_factors=[]
        )
    ])
    # Compound fires first
    ass1 = engine.fuse(fv1, rule_res1, None, [])
    assert ass1.lead_time_vs_baseline is None
    
    # 10 minutes later, baseline fires
    later = now + timedelta(minutes=10)
    fv2 = FeatureVector(timestamp=later, zone_id="Z1")
    rule_res2 = RuleEngineResult(timestamp=later.isoformat(), zone_id="Z1", triggered_rules=[])
    baseline_res = [BaselineResult(
        alarm_triggered=True, alarm_level="WARNING", sensor="S1", value=100.0,
        threshold=90.0, detection_time=later.isoformat(), zone="Z1", equipment=None, data_quality="VALID"
    )]
    
    ass2 = engine.fuse(fv2, rule_res2, None, baseline_res)
    assert ass2.baseline_alarm_status is True
    assert ass2.lead_time_vs_baseline == 600.0 # 10 minutes in seconds

def test_missing_data_confidence(engine):
    now = datetime.now(timezone.utc)
    fv = FeatureVector(timestamp=now, zone_id="Z1")
    rule_res = RuleEngineResult(timestamp=now.isoformat(), zone_id="Z1", triggered_rules=[
        RuleResult(
            rule_id="R1", rule_name="R1", hazard_type="FIRE", zone_id="Z1",
            score_contribution=50.0, severity="WARNING", confidence=1.0, trigger_timestamp=now.isoformat(),
            evidence={}, missing_evidence=["temp_sensor"], source_feature_values={}, 
            human_readable_explanation="", machine_readable_explanation="", escalation_factors=[]
        )
    ])
    assessment = engine.fuse(fv, rule_res, None, [])
    # Base is 100, missing sensor penalty is 15
    assert assessment.confidence == 85.0
