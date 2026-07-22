import operator
import yaml
from datetime import datetime, timezone
from typing import Dict, List, Any
from .models import CompoundRuleDef, RuleResult, RuleEngineResult, RuleCondition
from ...features.models import FeatureVector

# Safe operator registry
OPERATORS = {
    "eq": operator.eq,
    "neq": operator.ne,
    "gt": operator.gt,
    "gte": operator.ge,
    "lt": operator.lt,
    "lte": operator.le,
    "in": lambda a, b: a in b if isinstance(b, (list, tuple, set, str)) else False,
    "not_in": lambda a, b: a not in b if isinstance(b, (list, tuple, set, str)) else True,
}

class TemporalRuleState:
    def __init__(self):
        self.last_triggered: Dict[str, datetime] = {}

class RuleLoader:
    @staticmethod
    def load(yaml_path: str) -> List[CompoundRuleDef]:
        with open(yaml_path, "r") as f:
            data = yaml.safe_load(f)
        if not data or "rules" not in data:
             raise ValueError("Invalid YAML: missing 'rules' key")
        return [CompoundRuleDef(**r) for r in data["rules"]]

class RuleValidator:
    @staticmethod
    def validate(rules: List[CompoundRuleDef]):
        rule_ids = set()
        for rule in rules:
            if rule.rule_id in rule_ids:
                raise ValueError(f"Duplicate rule_id: {rule.rule_id}")
            rule_ids.add(rule.rule_id)
            
            # Check operators
            for cond_group in rule.conditions.values():
                for cond in cond_group:
                    if cond.operator not in OPERATORS:
                        raise ValueError(f"Invalid operator '{cond.operator}' in rule {rule.rule_id}")
            for esc in rule.escalation:
                if esc.when.operator not in OPERATORS:
                     raise ValueError(f"Invalid operator '{esc.when.operator}' in rule {rule.rule_id} escalation")

class RuleEvaluator:
    def __init__(self, rules: List[CompoundRuleDef]):
        RuleValidator.validate(rules)
        self.rules = [r for r in rules if r.enabled]
        self.state = TemporalRuleState()

    def _eval_condition(self, cond: RuleCondition, feature_vector: FeatureVector) -> bool:
        if cond.feature not in feature_vector.features:
            return False
        val = feature_vector.features[cond.feature].value
        op_func = OPERATORS.get(cond.operator)
        return op_func(val, cond.value)

    def evaluate(self, feature_vector: FeatureVector) -> RuleEngineResult:
        triggered = []
        now = feature_vector.timestamp
        zone = feature_vector.zone_id

        for rule in self.rules:
            if zone not in rule.applicable_zones and "ALL" not in rule.applicable_zones:
                continue

            state_key = f"{zone}:{rule.rule_id}"
            if state_key in self.state.last_triggered:
                last_t = self.state.last_triggered[state_key]
                if (now - last_t).total_seconds() < rule.cooldown_seconds:
                    continue

            all_conds = rule.conditions.get("all", [])
            any_conds = rule.conditions.get("any", [])
            not_conds = rule.conditions.get("not", [])

            evidence = {}
            missing = []

            # all
            passed_all = True
            for c in all_conds:
                if c.feature not in feature_vector.features:
                    missing.append(c.feature)
                    passed_all = False
                elif not self._eval_condition(c, feature_vector):
                    passed_all = False
                else:
                    evidence[c.feature] = feature_vector.features[c.feature].value

            if not passed_all:
                continue

            # any
            passed_any = len(any_conds) == 0
            for c in any_conds:
                if c.feature not in feature_vector.features:
                    missing.append(c.feature)
                    continue
                if self._eval_condition(c, feature_vector):
                    passed_any = True
                    evidence[c.feature] = feature_vector.features[c.feature].value
                    break

            if not passed_any:
                continue

            # not
            passed_not = True
            for c in not_conds:
                if c.feature in feature_vector.features and self._eval_condition(c, feature_vector):
                    passed_not = False
                    evidence[c.feature] = feature_vector.features[c.feature].value
                    break

            if not passed_not:
                continue

            # escalation
            score = rule.base_score
            escalation_factors = []
            for esc in rule.escalation:
                if esc.when.feature in feature_vector.features and self._eval_condition(esc.when, feature_vector):
                    score += esc.score_delta
                    escalation_factors.append(esc.when.feature)
                    evidence[esc.when.feature] = feature_vector.features[esc.when.feature].value

            # explanations
            hr_exp = f"{rule.rule_id} triggered because conditions met in {zone}. Evidence: "
            hr_exp += ", ".join([f"{k} is {v}" for k, v in evidence.items()])
            
            mr_exp = {
                "rule_id": rule.rule_id,
                "zone_id": zone,
                "matched_conditions": list(evidence.keys()),
                "escalations": escalation_factors
            }

            result = RuleResult(
                rule_id=rule.rule_id,
                rule_name=rule.name,
                hazard_type=rule.hazard_type,
                zone_id=zone,
                score_contribution=score,
                severity=rule.severity,
                confidence=rule.confidence,
                trigger_timestamp=now.isoformat(),
                evidence=evidence,
                missing_evidence=missing,
                source_feature_values=evidence,
                human_readable_explanation=hr_exp,
                machine_readable_explanation=str(mr_exp),
                escalation_factors=escalation_factors
            )
            triggered.append(result)
            self.state.last_triggered[state_key] = now

        return RuleEngineResult(
            timestamp=now.isoformat(),
            zone_id=zone,
            triggered_rules=triggered
        )
