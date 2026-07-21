# AI Gap Analysis

## Critical Blockers
### 1. Missing Extractors for Rule Engine Variables
- **Requirement**: The rule engine must evaluate valid extracted features based on real plant conditions.
- **Current State**: `risk_rules.yaml` references features like `adjacent_zone_risk`, `maintenance_overdue`, and `esd_bypassed`, which are not currently implemented by `pipeline.py` or any extractors.
- **Why it matters**: Severe rules (e.g., Confined Space violations, fire propagation) will silently fail to trigger, rendering the AI functionally blind to these hazards.
- **Exact files involved**: `backend/app/ai/features/extractors/extractors.py`, `backend/app/ai/config/risk_rules.yaml`.
- **Recommended implementation**: Add a `GeospatialExtractor` and a `MaintenanceExtractor` to parse plant topology and maintenance records.
- **Estimated effort**: 1-2 days.
- **Dependencies**: Asset topology schema.
- **Acceptance criteria**: Rules using these features trigger successfully in tests.

## High Priority
### 1. Incomplete Evaluation Plotting & Artifacts
- **Requirement**: Evaluation must output visual plots (timelines, PR curves) and ablation/false-alarm CSV files.
- **Current State**: Evaluation generates `event_level_predictions.csv` and a JSON summary. All plotting, confusion matrices, and ablation data generation are missing.
- **Why it matters**: Without these visual artifacts, the data scientists cannot tune the AI effectively or explain the baseline vs. compound advantage to stakeholders.
- **Exact files involved**: `backend/app/ai/evaluation/metrics.py`.
- **Recommended implementation**: Add matplotlib/seaborn code to output PNG plots and pandas code to slice ablation test results.
- **Estimated effort**: 1 day.
- **Dependencies**: None.
- **Acceptance criteria**: 4+ PNG plots and 5+ CSV artifacts exist in `evaluation/`.

## Medium Priority
### 1. Data Fingerprinting & Version Persistence
- **Requirement**: Anomaly detector must persist data fingerprint, metadata, and version logic.
- **Current State**: `isolation_forest.py` only saves the `model`, `scaler`, and `features` list using joblib.
- **Why it matters**: Mismatched feature vectors during inference could corrupt predictions, and model auditing in production becomes impossible without a fingerprint.
- **Exact files involved**: `backend/app/ai/detection/anomaly/isolation_forest.py`.
- **Recommended implementation**: Implement a `metadata.json` save block inside `save()` encompassing hash/fingerprint of training data.
- **Estimated effort**: 4 hours.
- **Dependencies**: None.
- **Acceptance criteria**: `metadata.json` is saved on `.save()` and checked on `.load()`.

## Low Priority
### 1. Advanced Risk Fusion Logic
- **Requirement**: Score cap at 100, severity overrides, diminishing returns, and independent corroboration.
- **Current State**: Implements contextual modifiers and linear decay, but lacks diminishing returns, cooldown periods, and explicit independent corroboration math.
- **Why it matters**: The overall risk score may behave linearly rather than exponentially/logarithmically, creating edge cases where a moderate threat is overrated.
- **Exact files involved**: `backend/app/ai/detection/fusion/engine.py`.
- **Recommended implementation**: Introduce logarithmic scaling for modifiers and a hard cooldown dictionary in `TemporalRiskState`.
- **Estimated effort**: 1 day.
- **Dependencies**: None.
- **Acceptance criteria**: Unit tests for diminishing returns and cooldowns pass.

## Optional Enhancements
### 1. Supervised Model Interface
- **Requirement**: Optional supervised model if labeled data is sufficient.
- **Current State**: Not implemented (only rules + unsupervised anomaly detection exist).
- **Why it matters**: Could provide a safety net for hazards missed by human rules.
- **Exact files involved**: `backend/app/ai/detection/supervised/`
- **Recommended implementation**: Placeholder wrapper for LightGBM or XGBoost.
- **Estimated effort**: 3 days.
