import argparse
import yaml
import pandas as pd
import numpy as np
from sklearn.metrics import classification_report, roc_auc_score
from ..detection.anomaly.isolation_forest import IsolationForestDetector

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True, help="Path to saved model")
    parser.add_argument("--input", required=True, help="Path to evaluation snapshots parquet")
    args = parser.parse_args()

    # Load model
    detector = IsolationForestDetector.load(args.model, config={})
    print(f"Loaded model trained on {len(detector.feature_names)} features.")

    # Load evaluation data
    df = pd.read_parquet(args.input)
    
    if "label" not in df.columns:
        print("No 'label' column found. Evaluating in unsupervised mode (cannot compute ROC/PR).")
        labels = None
    else:
        labels = df["label"].values

    # Extract required features, fill missing with 0
    X = np.zeros((len(df), len(detector.feature_names)))
    for i, col in enumerate(detector.feature_names):
        if col in df.columns:
            X[:, i] = df[col].values
            
    # Scale and Predict
    X_scaled = detector.scaler.transform(X)
    preds = detector.model.predict(X_scaled)
    # Predict returns 1 for inliers, -1 for outliers
    is_anomaly = (preds == -1).astype(int)
    
    raw_scores = detector.model.decision_function(X_scaled)

    if labels is not None:
        print("Classification Report:")
        print(classification_report(labels, is_anomaly))
        
        try:
            # For roc_auc, we want higher score for anomaly. 
            # raw_scores is lower for anomaly, so we negate it.
            auc = roc_auc_score(labels, -raw_scores)
            print(f"ROC-AUC: {auc:.4f}")
        except Exception as e:
            print(f"Could not compute ROC-AUC: {e}")
            
    # Add predictions back to dataframe for analysis
    df["is_anomaly_pred"] = is_anomaly
    df["anomaly_score"] = -raw_scores
    
    out_path = args.input.replace(".parquet", "_results.csv")
    df.to_csv(out_path, index=False)
    print(f"Saved predictions to {out_path}")

if __name__ == "__main__":
    main()
