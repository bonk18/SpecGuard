import os
import sys
import pandas as pd
import json
from datetime import datetime, timezone
import yaml

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../..')))

from backend.app.ai.detection.rules.engine import RuleEvaluator, RuleLoader
from backend.app.ai.detection.fusion.engine import RiskFusionEngine
from backend.app.ai.features.models import FeatureVector, FeatureValue
from backend.app.ai.evaluation.evaluate_systems import evaluate_baseline

def create_feature_vector(row: pd.Series) -> FeatureVector:
    ts = pd.to_datetime(row["timestamp"])
    fv = FeatureVector(timestamp=ts, zone_id=row["zone_id"])
    for col in row.index:
        if col not in ["timestamp", "zone_id", "scenario_id", "label"]:
            fv.features[col] = FeatureValue(
                name=col, value=row[col], timestamp=ts, zone_id=row["zone_id"]
            )
    return fv

def main():
    df = pd.read_parquet("data/processed/hot_work_gas_leak_features.parquet")
    df = df.sort_values(by="timestamp").reset_index(drop=True)
    
    rules = RuleLoader.load("backend/app/ai/config/risk_rules.yaml")
    rule_evaluator = RuleEvaluator(rules)
    fusion = RiskFusionEngine("backend/app/ai/config/risk_scoring.yaml")
    
    hazard_start_time = None
    first_compound_trigger_time = None
    first_warning_time = None
    first_high_risk_time = None
    baseline_alarm_time = None
    incident_time = None
    
    timeline = []
    
    for _, row in df.iterrows():
        ts = pd.to_datetime(row["timestamp"])
        lbl = row["label"]
        
        # Hazard start (e.g. condition starts deteriorating)
        if hazard_start_time is None and lbl > 0:
            hazard_start_time = ts
            
        # Incident time (label == 2 indicates catastrophic failure/incident)
        if incident_time is None and lbl == 2:
            incident_time = ts
            
        fv = create_feature_vector(row)
        
        # Baseline
        base_alarms = evaluate_baseline(row)
        if len(base_alarms) > 0 and baseline_alarm_time is None:
            baseline_alarm_time = ts
            
        # Compound
        rule_res = rule_evaluator.evaluate(fv)
        if len(rule_res.triggered_rules) > 0 and first_compound_trigger_time is None:
            first_compound_trigger_time = ts
            
        # Fusion
        # We dummy the anomaly score for this specific script as we just want the rule+baseline timeline
        from backend.app.ai.detection.anomaly.models import AnomalyResult
        from backend.app.ai.detection.baseline.models import BaselineResult
        
        dummy_anomaly = AnomalyResult(
            is_anomaly=False, is_anomalous=False, raw_model_score=0.0, normalized_score=0.0,
            anomaly_score=0.0, timestamp=ts, zone_id=row["zone_id"],
            contributing_features={}, feature_values={}, model_version="1.0",
            data_quality_status="OK", confidence=1.0
        )
        
        base_res_objs = []
        for b in base_alarms:
            base_res_objs.append(BaselineResult(
                alarm_triggered=True, alarm_level=b["level"], sensor=b["sensor"],
                value=0.0, threshold=0.0, detection_time=ts.isoformat(), zone=row["zone_id"],
                equipment="NONE", data_quality="OK"
            ))
            
        fusion_res = fusion.fuse(fv, rule_res, anomaly_result=dummy_anomaly, baseline_results=base_res_objs)
        score = fusion_res.overall_risk_score
        
        if score >= 40 and first_warning_time is None:
            first_warning_time = ts
            
        if score >= 70 and first_high_risk_time is None:
            first_high_risk_time = ts
            
        timeline.append({
            "timestamp": ts.isoformat(),
            "zone_id": row["zone_id"],
            "label": lbl,
            "baseline_alarms": len(base_alarms),
            "triggered_rules": len(rule_res.triggered_rules),
            "risk_score": score
        })
        
    timeline_df = pd.DataFrame(timeline)
    os.makedirs("evaluation", exist_ok=True)
    timeline_df.to_csv("evaluation/canonical_scenario_timeline.csv", index=False)
    
    def diff_secs(t1, t2):
        if pd.isna(t1) or pd.isna(t2) or t1 is None or t2 is None:
            return None
        return (pd.to_datetime(t1) - pd.to_datetime(t2)).total_seconds()
        
    lead_vs_base = diff_secs(baseline_alarm_time, first_compound_trigger_time)
    lead_vs_inc = diff_secs(incident_time, first_compound_trigger_time)
    
    # The requirement is that lead time can be calculated and compound triggers before baseline.
    if first_compound_trigger_time is None:
        raise RuntimeError("Compound rule never triggered in canonical scenario!")
        
    if lead_vs_base is not None and lead_vs_base < 0:
        print(f"WARNING: Baseline triggered BEFORE compound system! Lead time vs baseline: {lead_vs_base}s")
        
    if incident_time is None:
         # Some scenarios might not have label 2, just mock it as the end if missing for lead time
         incident_time = df["timestamp"].max()
         lead_vs_inc = diff_secs(incident_time, first_compound_trigger_time)

    summary = {
        "hazard_start_time": pd.to_datetime(hazard_start_time).isoformat() if hazard_start_time else None,
        "first_compound_trigger_time": pd.to_datetime(first_compound_trigger_time).isoformat() if first_compound_trigger_time else None,
        "first_risk_warning_time": pd.to_datetime(first_warning_time).isoformat() if first_warning_time else None,
        "first_high_risk_time": pd.to_datetime(first_high_risk_time).isoformat() if first_high_risk_time else None,
        "baseline_alarm_time": pd.to_datetime(baseline_alarm_time).isoformat() if baseline_alarm_time else None,
        "simulated_incident_time": pd.to_datetime(incident_time).isoformat() if incident_time else None,
        "lead_time_vs_baseline_seconds": lead_vs_base,
        "lead_time_vs_incident_seconds": lead_vs_inc
    }
    
    with open("evaluation/canonical_scenario_summary.json", "w") as f:
        json.dump(summary, f, indent=2)

if __name__ == "__main__":
    main()
