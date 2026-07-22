import argparse
import yaml
import pandas as pd
from ..detection.anomaly.isolation_forest import IsolationForestDetector

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="Path to normal snapshots parquet")
    parser.add_argument("--config", required=True, help="Path to model config")
    parser.add_argument("--output", required=True, help="Path to save model")
    args = parser.parse_args()

    # Load config
    with open(args.config, "r") as f:
        config = yaml.safe_load(f)

    # Load data
    df = pd.read_parquet(args.input)
    
    # Preprocessing: drop non-feature columns
    exclude_cols = ["timestamp", "zone_id", "scenario_id", "incident_time", "label"]
    feature_cols = [c for c in df.columns if c not in exclude_cols]

    # Train
    detector = IsolationForestDetector(config)
    print(f"Training on {len(df)} samples with {len(feature_cols)} features...")
    detector.fit(df, feature_cols)

    # Save
    detector.save(args.output)
    print(f"Model saved to {args.output}")

if __name__ == "__main__":
    main()
