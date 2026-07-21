# Baseline and Anomaly Models

> **Module**: `backend.app.ai.detection`
> **Purpose**: Implement the independent baseline threshold alarms and the unsupervised anomaly detection models to detect deviations outside deterministic rules.

## Part A: Single-Sensor Baseline

The `BaselineEvaluator` serves as the ground-truth comparator representing traditional DCS (Distributed Control System) alarming logic. 

**Characteristics**:
- **Independent**: Evaluates every sensor in complete isolation.
- **No Context**: Intentionally ignores cross-sensor relationships, active permits, maintenance states, or worker counts.
- **Thresholds**: Uses `warning_max`, `critical_max`, `warning_min`, and `critical_min` defined in the `sensor_mapping.yaml` config, falling back to absolute physical min/max if needed.

**Output**:
Generates a list of `BaselineResult` indicating `WARNING` or `CRITICAL` levels, the threshold breached, and the specific sensor ID.

## Part B: Unsupervised Anomaly Detection

To catch novel failures not codified in the 35 compound rules, the pipeline employs an `IsolationForestDetector`.

**Architecture**:
- **Model**: `sklearn.ensemble.IsolationForest`. Chosen for its robustness to high-dimensional continuous data and ability to train purely on "normal" operational data.
- **Preprocessing**: `StandardScaler` applied to all selected features. Excludes labels, ground truth IDs, and non-feature columns.
- **Training**: Trained exclusively on normal-operation periods. Supports saving to disk via `joblib`.
- **Explainability**: Since Isolation Forests do not natively provide per-feature exact importance for a single prediction, we implement an **approximate deviation-based explanation**. The absolute deviation of each scaled feature is computed, and features with the highest relative deviation are returned as the `top_deviating_features`.

**CLI Interfaces**:
- `python -m backend.app.ai.training.train_anomaly`
- `python -m backend.app.ai.training.evaluate_anomaly`

## Future Work (Phase 3 Fusion)
These two components (Baseline + Anomaly) along with the Deterministic Rules will be fused into a final 0-100 risk score in the upcoming Master Risk Pipeline.
