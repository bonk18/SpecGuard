import os
import sys
import json
import yaml

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../..')))

from backend.app.ai.features.registry import registry

def main():
    with open("evaluation/feature_rule_contract.json", "r") as f:
        contract = json.load(f)
        
    extracted_features = set(contract.get("extracted_features", []))
    
    with open("backend/app/ai/config/risk_rules.yaml", "r") as f:
        rule_config = yaml.safe_load(f)
        
    rules = rule_config.get("rules", [])
    
    total_enabled = 0
    reachable_rules = 0
    unreachable_rules = []
    rules_with_missing_features = []
    rules_with_invalid_types = []
    rules_with_impossible_conditions = []
    
    for r in rules:
        if not r.get("enabled", True):
            continue
            
        total_enabled += 1
        rule_id = r.get("rule_id", "UNKNOWN")
        is_reachable = True
        
        # 1. Missing features check
        conds = r.get("conditions", {}).get("all", []) + r.get("conditions", {}).get("any", [])
        for esc in r.get("escalation", []):
            if "when" in esc:
                conds.append(esc["when"])
                
        missing_in_this_rule = False
        for c in conds:
            if "feature" in c:
                if c["feature"] not in extracted_features:
                    missing_in_this_rule = True
                    is_reachable = False
                    
        if missing_in_this_rule:
            rules_with_missing_features.append(rule_id)
            
        # 2. Check for impossible conditions (e.g., worker_count < 0)
        impossible = False
        for c in conds:
            if "feature" in c and c["feature"] == "worker_count" and c.get("operator") == "lt" and c.get("value", 0) <= 0:
                impossible = True
            if "feature" in c and c.get("operator") == "eq" and type(c.get("value")) == str and c.get("value") not in ["ACTIVE", "INACTIVE"]:
                # simple dummy check
                pass
                
        if impossible:
            rules_with_impossible_conditions.append(rule_id)
            is_reachable = False
            
        # 3. Valid types check (basic)
        invalid_types = False
        for c in conds:
            # Check if operator expects numeric but gets string
            if c.get("operator") in ["gt", "lt", "gte", "lte"] and not isinstance(c.get("value"), (int, float)):
                invalid_types = True
        if invalid_types:
            rules_with_invalid_types.append(rule_id)
            is_reachable = False
            
        if not is_reachable:
            unreachable_rules.append(rule_id)
        else:
            reachable_rules += 1
            
    coverage_percent = (reachable_rules / total_enabled) * 100 if total_enabled > 0 else 0
    
    output = {
        "total_enabled_rules": total_enabled,
        "reachable_rules": reachable_rules,
        "unreachable_rules": list(set(unreachable_rules)),
        "rules_with_missing_features": list(set(rules_with_missing_features)),
        "rules_with_invalid_types": list(set(rules_with_invalid_types)),
        "rules_with_impossible_conditions": list(set(rules_with_impossible_conditions)),
        "coverage_percent": round(coverage_percent, 2)
    }
    
    with open("evaluation/rule_reachability.json", "w") as f:
        json.dump(output, f, indent=2)

if __name__ == "__main__":
    main()
