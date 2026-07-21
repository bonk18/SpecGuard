import yaml
from collections import Counter

def main():
    with open("backend/app/ai/config/risk_rules.yaml", "r") as f:
        config = yaml.safe_load(f)
    rules = config.get("rules", [])
    
    enabled = [r for r in rules if r.get("enabled", True)]
    disabled = [r for r in rules if not r.get("enabled", True)]
    
    categories = Counter(r.get("hazard_type", "Unknown") for r in rules)
    
    features = set()
    for r in rules:
        conds = r.get("conditions", {}).get("all", []) + r.get("conditions", {}).get("any", [])
        for c in conds:
            if "feature" in c:
                features.add(c["feature"])
                
    print("Total enabled rules:", len(enabled))
    print("Total disabled rules:", len(disabled))
    print("Hazard categories:", dict(categories))
    print("Features used:", list(features))
    
if __name__ == "__main__":
    main()
