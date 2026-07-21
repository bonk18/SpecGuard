# Feature Engineering Pipeline

> **Module**: `backend.app.ai.features`
> **Purpose**: Transform normalized plant state snapshots into ML-ready and rule-engine-ready feature vectors.

## Overview

The feature engineering pipeline is designed to be deterministic, stateless (with respect to anything outside its rolling window buffer), and safe from future-data leakage. It extracts 10 specific groups of features designed to detect compound industrial risks.

The pipeline exposes two primary interfaces:
- `FeaturePipeline`: For offline, batch-processing of historical data or evaluation.
- `StreamingFeaturePipeline`: For real-time execution, maintaining an in-memory deque buffer to provide O(1) feature vector generation as new events arrive.

## Feature Groups

1. **Raw Normalized Features**: Sensor values min-max normalized based on boundaries from the master asset model. Also includes counts for workers and active permits.
2. **Rolling Statistical Features**: Smoothing over 30s, 60s, 300s, and 600s windows. Features include rolling mean, providing noise-resistant baselines.
3. **Trend Features**: First derivative (`slope`) to detect rapid accumulation of gas, dropping pressure, or increasing temperature.
4. **Cross-Sensor Features**: Captures physical relationships like Pressure/Flow ratios (indicating blockages) and Gas/Oxygen reduction mismatches.
5. **Equipment Health**: Degradation scores normalized from internal equipment state models.
6. **Permit Features**: Includes boolean indicators like `hot_work_active` and cross-references like `isolation_incomplete` (maintenance ongoing without isolation).
7. **Maintenance & Isolation**: Tracks active maintenance states.
8. **Worker Exposure**: Features capturing the number of workers in the zone, providing the exposure multiplier for risk assessment.
9. **Geospatial Features**: (Planned for graph expansion) Utilizing the zone adjacency maps for downstream/upstream propagation.
10. **Data Quality Features**: Counts of stale sensors to reduce confidence dynamically without arbitrarily raising hazard severity.

## Metadata Registry

Every generated feature registers itself dynamically with the `FeatureRegistry`. This provides a runtime dictionary mapping feature names to their configurations, source types, and safety relevance, ensuring 100% explainability.

## Testing & Safety

- Unit tests ensure exact parity between `FeaturePipeline.transform(batch)` and sequential `StreamingFeaturePipeline.update(single)`.
- The `history` list passed to extractors is strictly capped at `current_timestamp` to prevent future leakage.
