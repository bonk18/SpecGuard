import pytest
from datetime import datetime, timezone, timedelta
from pathlib import Path
import yaml

from ..detection.rules.models import CompoundRuleDef, RuleCondition, EscalationCondition
from ..detection.rules.engine import RuleEvaluator, RuleLoader, RuleValidator, TemporalRuleState
from ..features.models import FeatureVector, FeatureValue

@pytest.fixture
def sample_rules_yaml(tmp_path):
    rules = {
        "rules": [
            {
                "rule_id": "CR-001",
                "name": "Hot Work Test",
                "description": "Test",
                "hazard_type": "FIRE",
                "severity": "HIGH",
                "base_score": 50,
                "applicable_zones": ["ZONE_A", "ZONE_B"],
                "conditions": {
                    "all": [
                        {"feature": "hot_work_active", "operator": "eq", "value": 1.0},
                        {"feature": "hydrocarbon_lel", "operator": "gte", "value": 10.0}
                    ]
                },
                "escalation": [
                    {
                        "when": {"feature": "worker_count", "operator": "gt", "value": 2},
                        "score_delta": 25.0
                    }
                ],
                "cooldown_seconds": 60
            },
            {
                "rule_id": "CR-002",
                "name": "Adjacent Zone Risk",
                "description": "Test",
                "hazard_type": "FIRE",
                "severity": "HIGH",
                "base_score": 40,
                "applicable_zones": ["ALL"],
                "conditions": {
                    "any": [
                        {"feature": "adjacent_risk", "operator": "gt", "value": 50.0},
                        {"feature": "leak_detected", "operator": "eq", "value": 1.0}
                    ]
                }
            }
        ]
    }
    file_path = tmp_path / "test_rules.yaml"
    with open(file_path, "w") as f:
        yaml.dump(rules, f)
    return str(file_path)

def test_load_and_validate_rules(sample_rules_yaml):
    rules = RuleLoader.load(sample_rules_yaml)
    assert len(rules) == 2
    RuleValidator.validate(rules)

def test_evaluate_rule_trigger():
    rules = [
        CompoundRuleDef(
            rule_id="R1", name="R1", description="desc", hazard_type="FIRE",
            applicable_zones=["ALL"], severity="HIGH", base_score=10,
            conditions={"all": [RuleCondition(feature="f1", operator="gt", value=5)]}
        )
    ]
    evaluator = RuleEvaluator(rules)
    
    now = datetime.now(timezone.utc)
    fv = FeatureVector(timestamp=now, zone_id="Z1")
    fv.features["f1"] = FeatureValue(name="f1", value=10, timestamp=now, zone_id="Z1")
    
    result = evaluator.evaluate(fv)
    assert len(result.triggered_rules) == 1
    assert result.triggered_rules[0].rule_id == "R1"
    assert result.triggered_rules[0].score_contribution == 10

def test_missing_data():
    rules = [
        CompoundRuleDef(
            rule_id="R1", name="R1", description="desc", hazard_type="FIRE",
            applicable_zones=["ALL"], severity="HIGH", base_score=10,
            conditions={"all": [RuleCondition(feature="f1", operator="gt", value=5)]}
        )
    ]
    evaluator = RuleEvaluator(rules)
    now = datetime.now(timezone.utc)
    fv = FeatureVector(timestamp=now, zone_id="Z1") # f1 is missing
    
    result = evaluator.evaluate(fv)
    assert len(result.triggered_rules) == 0

def test_escalation():
    rules = [
        CompoundRuleDef(
            rule_id="R1", name="R1", description="desc", hazard_type="FIRE",
            applicable_zones=["ALL"], severity="HIGH", base_score=10,
            conditions={"all": [RuleCondition(feature="f1", operator="gt", value=5)]},
            escalation=[EscalationCondition(when=RuleCondition(feature="workers", operator="gt", value=0), score_delta=20)]
        )
    ]
    evaluator = RuleEvaluator(rules)
    now = datetime.now(timezone.utc)
    fv = FeatureVector(timestamp=now, zone_id="Z1")
    fv.features["f1"] = FeatureValue(name="f1", value=10, timestamp=now, zone_id="Z1")
    fv.features["workers"] = FeatureValue(name="workers", value=5, timestamp=now, zone_id="Z1")
    
    result = evaluator.evaluate(fv)
    assert len(result.triggered_rules) == 1
    assert result.triggered_rules[0].score_contribution == 30 # 10 base + 20 escalation

def test_cooldown():
    rules = [
        CompoundRuleDef(
            rule_id="R1", name="R1", description="desc", hazard_type="FIRE",
            applicable_zones=["ALL"], severity="HIGH", base_score=10,
            cooldown_seconds=60,
            conditions={"all": [RuleCondition(feature="f1", operator="gt", value=5)]}
        )
    ]
    evaluator = RuleEvaluator(rules)
    now = datetime.now(timezone.utc)
    fv = FeatureVector(timestamp=now, zone_id="Z1")
    fv.features["f1"] = FeatureValue(name="f1", value=10, timestamp=now, zone_id="Z1")
    
    # First evaluation triggers
    res1 = evaluator.evaluate(fv)
    assert len(res1.triggered_rules) == 1
    
    # Second evaluation immediately after does not trigger due to cooldown
    fv.timestamp = now + timedelta(seconds=30)
    res2 = evaluator.evaluate(fv)
    assert len(res2.triggered_rules) == 0
    
    # Third evaluation after cooldown triggers
    fv.timestamp = now + timedelta(seconds=61)
    res3 = evaluator.evaluate(fv)
    assert len(res3.triggered_rules) == 1

def test_invalid_yaml(tmp_path):
    invalid_file = tmp_path / "invalid.yaml"
    invalid_file.write_text("rules:\n  - invalid_yaml: [}")
    with pytest.raises((ValueError, yaml.YAMLError)):
        RuleLoader.load(str(invalid_file))

def test_unsafe_expression():
    rules = [
        CompoundRuleDef(
            rule_id="R1", name="R1", description="desc", hazard_type="FIRE",
            applicable_zones=["ALL"], severity="HIGH", base_score=10,
            conditions={"all": [RuleCondition(feature="f1", operator="eval", value="import os; os.system('echo')")]}
        )
    ]
    with pytest.raises(ValueError):
        RuleValidator.validate(rules)

def test_duplicate_rules():
    rules = [
        CompoundRuleDef(
             rule_id="R1", name="R1", description="desc", hazard_type="FIRE", applicable_zones=["ALL"], severity="HIGH", base_score=10, conditions={}
        ),
        CompoundRuleDef(
             rule_id="R1", name="R2", description="desc", hazard_type="FIRE", applicable_zones=["ALL"], severity="HIGH", base_score=10, conditions={}
        )
    ]
    with pytest.raises(ValueError):
         RuleValidator.validate(rules)
