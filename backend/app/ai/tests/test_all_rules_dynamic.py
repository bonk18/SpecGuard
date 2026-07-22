
import pytest
from datetime import datetime, timezone
from ..detection.rules.models import CompoundRuleDef, RuleCondition
from ..detection.rules.engine import RuleEvaluator, RuleLoader
from ..features.models import FeatureVector, FeatureValue
import json

@pytest.fixture
def real_rules():
    return RuleLoader.load("backend/app/ai/config/risk_rules.yaml")

def generate_feature_value(op, val):
    if op == "eq": return val
    if op == "neq": return val + 1 if isinstance(val, (int, float)) else not val
    if op == "gt": return val + 1.0
    if op == "gte": return val
    if op == "lt": return val - 1.0
    if op == "lte": return val
    return val

def generate_negative_feature_value(op, val):
    if op == "eq": return val + 1 if isinstance(val, (int, float)) else 0.0
    if op == "neq": return val
    if op == "gt": return val - 1.0
    if op == "gte": return val - 1.0
    if op == "lt": return val + 1.0
    if op == "lte": return val + 1.0
    return val


def test_all_rules_coverage(real_rules):
    # Requirement: Generate evaluation/rule_test_coverage.json
    now = datetime.now(timezone.utc)
    
    covered_positive = 0
    covered_negative = 0
    
    for rule in real_rules:
        if not rule.enabled:
            continue
            
        # 1. Positive case
        fv_pos = FeatureVector(timestamp=now, zone_id="ZONE_ALL")
        
        # Populate features to make it trigger
        conds = rule.conditions.get("all", []) + rule.conditions.get("any", [])
        for c in conds:
            v = generate_feature_value(c.operator, c.value)
            fv_pos.features[c.feature] = FeatureValue(name=c.feature, value=v, timestamp=now, zone_id="ZONE_ALL")
            
        evaluator = RuleEvaluator([rule])
        res = evaluator.evaluate(fv_pos)
        
        if len(res.triggered_rules) > 0:
            covered_positive += 1
            
        # 2. Negative case (miss one 'all' condition or all 'any' conditions)
        fv_neg = FeatureVector(timestamp=now, zone_id="ZONE_ALL")
        all_conds = rule.conditions.get("all", [])
        if all_conds:
            for i, c in enumerate(all_conds):
                if i == 0:
                    v = generate_negative_feature_value(c.operator, c.value)
                else:
                    v = generate_feature_value(c.operator, c.value)
                fv_neg.features[c.feature] = FeatureValue(name=c.feature, value=v, timestamp=now, zone_id="ZONE_ALL")
        else:
            any_conds = rule.conditions.get("any", [])
            for c in any_conds:
                v = generate_negative_feature_value(c.operator, c.value)
                fv_neg.features[c.feature] = FeatureValue(name=c.feature, value=v, timestamp=now, zone_id="ZONE_ALL")
                
        res_neg = evaluator.evaluate(fv_neg)
        if len(res_neg.triggered_rules) == 0:
            covered_negative += 1
            
    total = len([r for r in real_rules if r.enabled])
    
    with open("evaluation/rule_test_coverage.json", "w") as f:
        json.dump({
            "total_enabled_rules": total,
            "rules_with_positive_tests": covered_positive,
            "rules_with_negative_tests": covered_negative,
            "coverage_percent": 100.0 if covered_positive == total and covered_negative == total else 0.0
        }, f, indent=2)
        
    assert covered_positive == total
    assert covered_negative == total
