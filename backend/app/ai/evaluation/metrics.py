import pandas as pd
import numpy as np
import json
import os

def calculate_metrics(df: pd.DataFrame, sys_col: str, truth_col: str = "label"):
    # Timepoint metrics
    TP = ((df[sys_col] == 1) & (df[truth_col] == 1)).sum()
    TN = ((df[sys_col] == 0) & (df[truth_col] == 0)).sum()
    FP = ((df[sys_col] == 1) & (df[truth_col] == 0)).sum()
    FN = ((df[sys_col] == 0) & (df[truth_col] == 1)).sum()
    
    precision = TP / (TP + FP) if (TP + FP) > 0 else 0.0
    recall = TP / (TP + FN) if (TP + FN) > 0 else 0.0
    fpr = FP / (FP + TN) if (FP + TN) > 0 else 0.0
    fnr = FN / (FN + TP) if (FN + TP) > 0 else 0.0
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
    
    # False alarms per hour (assuming 1 row = 1 second)
    total_hours = len(df) / 3600
    fa_per_hour = FP / total_hours if total_hours > 0 else 0.0
    
    # Scenario level metrics
    scenario_recall_sum = 0
    scenario_total = 0
    mean_lead_time = []
    
    for scenario, group in df.groupby("scenario"):
        # If normal, just skip recall
        if scenario == "normal":
            continue
            
        scenario_total += 1
        # Did it trigger an alarm at all during this scenario when label=1?
        if group[(group[truth_col] == 1) & (group[sys_col] == 1)].shape[0] > 0:
            scenario_recall_sum += 1
            
        # Lead time computation
        # For simplicity, if system triggers before baseline, we give it a positive lead time
        # Baseline trigger time:
        base_triggers = group[(group[truth_col] == 1) & (group["baseline_triggered"] == 1)]
        if not base_triggers.empty:
            base_time = pd.to_datetime(base_triggers.iloc[0]["timestamp"])
            sys_triggers = group[(group[truth_col] == 1) & (group[sys_col] == 1)]
            if not sys_triggers.empty:
                sys_time = pd.to_datetime(sys_triggers.iloc[0]["timestamp"])
                lead = (base_time - sys_time).total_seconds()
                mean_lead_time.append(lead)

    scenario_recall = scenario_recall_sum / scenario_total if scenario_total > 0 else 0.0
    
    return {
        "precision": float(precision),
        "recall": float(recall),
        "f1": float(f1),
        "fpr": float(fpr),
        "fnr": float(fnr),
        "fa_per_hour": float(fa_per_hour),
        "scenario_recall": float(scenario_recall),
        "mean_lead_time_sec": float(np.mean(mean_lead_time)) if mean_lead_time else 0.0,
        "median_lead_time_sec": float(np.median(mean_lead_time)) if mean_lead_time else 0.0
    }

def main():
    print("Loading predictions...")
    if not os.path.exists("evaluation/event_level_predictions.csv"):
        print("Error: run evaluate_systems.py first.")
        return
        
    df = pd.read_csv("evaluation/event_level_predictions.csv")
    
    # Define systems
    df["sys_baseline"] = df["baseline_triggered"]
    df["sys_rules"] = (df["rules_score"] >= 40.0).astype(int)
    df["sys_anomaly"] = (df["anomaly_score"] >= 0.55).astype(int)
    df["sys_rules_anomaly"] = ((df["rules_score"] >= 40.0) | (df["anomaly_score"] >= 0.55)).astype(int)
    df["sys_fusion"] = (df["fusion_score"] >= 40.0).astype(int)
    
    systems = {
        "Baseline": "sys_baseline",
        "Rules Only": "sys_rules",
        "Anomaly Only": "sys_anomaly",
        "Rules + Anomaly": "sys_rules_anomaly",
        "Full Fusion": "sys_fusion"
    }
    
    results = {}
    for name, col in systems.items():
        print(f"Calculating metrics for {name}...")
        results[name] = calculate_metrics(df, col)
        
    with open("evaluation/metrics_summary.json", "w") as f:
        json.dump(results, f, indent=4)
        
    metrics_df = pd.DataFrame(results).T
    metrics_df.index.name = "System"
    metrics_df.to_csv("evaluation/metrics_summary.csv")
        
    print("\n--- RESULTS ---")
    for name, mets in results.items():
        print(f"\n{name}:")
        for k, v in mets.items():
            print(f"  {k}: {v:.4f}")
            
if __name__ == "__main__":
    main()
