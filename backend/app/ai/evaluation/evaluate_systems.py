import os
import pandas as pd
import numpy as np
from datetime import datetime, timezone
import yaml
from ..features.models import FeatureVector, FeatureValue
from ..detection.rules.engine import RuleEvaluator
from ..detection.anomaly.isolation_forest import IsolationForestDetector
from ..detection.fusion.engine import RiskFusionEngine

# Basic thresholds for simulator variables
BASELINE_THRESHOLDS = {
    "hydrocarbon_norm_GD-SIM": {"warning": 0.015, "critical": 0.02},
    "h2s_norm_H2S-SIM": {"warning": 10.0, "critical": 15.0},
    "oxygen_norm_O2-SIM": {"warning_min": 0.195, "critical_min": 0.190},
    "pressure_norm_PT-SIM": {"warning_max": 30.0, "critical_max": 35.0},
    "temperature_norm_TT-SIM": {"warning_max": 55.0, "critical_max": 65.0},
    "vibration_norm_VIB-SIM": {"warning_max": 0.5, "critical_max": 0.8}
}

def evaluate_baseline(row: pd.Series) -> list:
    results = []
    for col, th in BASELINE_THRESHOLDS.items():
        if col in row and pd.notna(row[col]):
            val = row[col]
            if "warning_min" in th:
                if val < th.get("critical_min", -9999):
                    results.append({"sensor": col, "level": "CRITICAL"})
                elif val < th.get("warning_min", -9999):
                    results.append({"sensor": col, "level": "WARNING"})
            else:
                crit_val = th.get("critical_max") or th.get("critical")
                warn_val = th.get("warning_max") or th.get("warning")
                if crit_val is not None and val > crit_val:
                    results.append({"sensor": col, "level": "CRITICAL"})
                elif warn_val is not None and val > warn_val:
                    results.append({"sensor": col, "level": "WARNING"})
    return results

from ..detection.rules.engine import RuleLoader

def main():
    print("Initializing models...")
    rules = RuleLoader.load("backend/app/ai/config/risk_rules.yaml")
    rule_evaluator = RuleEvaluator(rules)
    anomaly_detector = IsolationForestDetector(config={"n_estimators": 50})
    
    # Train anomaly detector on normal data
    print("Training anomaly detector on normal data...")
    normal_df = pd.read_parquet("data/processed/normal_features.parquet")
    feature_cols = [c for c in normal_df.columns if c not in ["timestamp", "zone_id", "scenario_id", "label"]]
    anomaly_detector.fit(normal_df, feature_cols)
    
    fusion_engine = RiskFusionEngine("backend/app/ai/config/risk_scoring.yaml")
    
    out_dir = "evaluation"
    os.makedirs(out_dir, exist_ok=True)
    
    all_results = []
    
    scenarios = [f for f in os.listdir("data/processed") if f.endswith(".parquet")]
    
    for scenario_file in scenarios:
        scenario = scenario_file.replace("_features.parquet", "")
        print(f"Evaluating scenario: {scenario}...")
        df = pd.read_parquet(os.path.join("data/processed", scenario_file))
        
        # Reset fusion state per scenario to prevent hysteresis leakage
        fusion_engine = RiskFusionEngine("backend/app/ai/config/risk_scoring.yaml")
        
        for _, row in df.iterrows():
            ts = pd.to_datetime(row["timestamp"])
            zone_id = row["zone_id"]
            label = row["label"]
            
            # Construct feature vector
            fv = FeatureVector(timestamp=ts, zone_id=zone_id)
            for col in df.columns:
                if col not in ["timestamp", "zone_id", "scenario_id", "label"]:
                    fv.features[col] = FeatureValue(name=col, value=float(row[col]), timestamp=ts, zone_id=zone_id)
            # Aliases for rules
            if "max_hydrocarbon_lel_pct" not in fv.features:
                fv.features["max_hydrocarbon_lel_pct"] = FeatureValue(name="max_hydrocarbon_lel_pct", value=fv.features.get("hydrocarbon_norm_GD-SIM", FeatureValue(name="", value=0.0, timestamp=ts, zone_id=zone_id)).value, timestamp=ts, zone_id=zone_id)
            if "h2s_ppm" not in fv.features:
                fv.features["h2s_ppm"] = FeatureValue(name="h2s_ppm", value=fv.features.get("h2s_norm_H2S-SIM", FeatureValue(name="", value=0.0, timestamp=ts, zone_id=zone_id)).value, timestamp=ts, zone_id=zone_id)
            if "ventilation_status" not in fv.features:
                fv.features["ventilation_status"] = FeatureValue(name="ventilation_status", value=fv.features.get("ventilation_health_norm_VENT-SIM", FeatureValue(name="", value=1.0, timestamp=ts, zone_id=zone_id)).value, timestamp=ts, zone_id=zone_id)
            if "pump_vibration" not in fv.features:
                fv.features["pump_vibration"] = FeatureValue(name="pump_vibration", value=fv.features.get("vibration_norm_VIB-SIM", FeatureValue(name="", value=0.0, timestamp=ts, zone_id=zone_id)).value, timestamp=ts, zone_id=zone_id)
            if "confined_space_permit" not in fv.features:
                fv.features["confined_space_permit"] = FeatureValue(name="confined_space_permit", value=1.0 if "confined" in scenario else 0.0, timestamp=ts, zone_id=zone_id)
            if "leak_detected" not in fv.features:
                fv.features["leak_detected"] = FeatureValue(name="leak_detected", value=1.0 if fv.features["max_hydrocarbon_lel_pct"].value > 10.0 else 0.0, timestamp=ts, zone_id=zone_id)

            
            # 1. Baseline
            base_res = evaluate_baseline(row)
            baseline_triggered = len(base_res) > 0
            
            # 2. Rules
            rule_res = rule_evaluator.evaluate(fv)
            rules_score = sum(r.score_contribution for r in rule_res.triggered_rules)
            
            # 3. Anomaly
            anomaly_res = anomaly_detector.predict(fv)
            
            # 4. Fusion
            # We mock the baseline result objects for the fusion engine
            from ..detection.baseline.models import BaselineResult
            mock_base_results = []
            for r in base_res:
                mock_base_results.append(BaselineResult(
                    alarm_triggered=True, alarm_level=r["level"], sensor=r["sensor"], value=1.0,
                    threshold=1.0, detection_time=ts.isoformat(), zone=zone_id, equipment=None, data_quality="VALID"
                ))
                
            fusion_res = fusion_engine.fuse(fv, rule_res, anomaly_res, mock_base_results)
            
            all_results.append({
                "timestamp": ts.isoformat(),
                "scenario": scenario,
                "zone_id": zone_id,
                "label": label,
                "baseline_triggered": int(baseline_triggered),
                "rules_score": rules_score,
                "anomaly_score": anomaly_res.normalized_score if anomaly_res else 0.0,
                "fusion_score": fusion_res.overall_risk_score,
                "lead_time_vs_baseline": fusion_res.lead_time_vs_baseline,
                "primary_hazard": fusion_res.primary_hazard
            })
            
    res_df = pd.DataFrame(all_results)
    res_df.to_csv(f"{out_dir}/event_level_predictions.csv", index=False)
    print("Saved event_level_predictions.csv")

if __name__ == "__main__":
    main()
