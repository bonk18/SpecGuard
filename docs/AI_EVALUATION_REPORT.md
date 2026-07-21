# AI Evaluation Report: SpecGuard Compound-Risk Detection

## 1. Executive Summary
*(To be completed after metrics)*

## 2. Methodology & Scenarios
We simulated a digital twin environment of a petroleum refinery, specifically observing "ZONE_A". 
We evaluated 7 distinct scenarios, splitting the "normal" scenario for training unsupervised models, and reserving the rest for testing:
1. Normal Operations (baseline, no anomalies)
2. Single Gas Leak
3. Ventilation Failure
4. Pump Failure
5. Hot Work with Concurrent Gas Leak (compound risk)
6. Confined Space Entry
7. Explosion Risk (multiple failure cascades)

The scenarios span various lengths and combine independent hazard types (fire, toxic, mechanical). 

## 3. Systems Evaluated
A. **Baseline (Single-Sensor)**: Traditional alarms using the API limits for warning and critical levels. Evaluates independently.
B. **Deterministic Rules Engine**: Compound-risk detection utilizing the `risk_rules.yaml` ruleset.
C. **Unsupervised Anomaly Detector**: Isolation Forest model tracking multivariable temporal deviation.
D. **Rules + Anomaly**: Combination of rule triggering and anomaly detection score.
E. **Full Risk-Fusion**: The comprehensive intelligence fusion combining rules, anomalies, and contextual hazard scores.

## 4. Primary Metrics
*(To be completed after metrics run)*
- **False-Negative Rate (FNR)**:
- **Compound-Risk Recall**:
- **Mean Detection Lead Time**:
- **False Alarms per Simulated Hour**:

## 5. System Comparison & Results
*(To be completed after metrics run)*

## 6. Ablation Study
*(To be completed after metrics run)*

## 7. Selected Configuration
*(To be completed after metrics run)*

## 8. Hot Work + Gas Leak Deep Dive
*(To be completed after timeline generation)*

## 9. False Positives Analysis
*(To be completed after metrics run)*

## 10. System Limitations
- **Offline Batch Dependency**: The anomaly model is currently trained offline on batched Parquet files. For a live deployment, online learning or scheduled retraining is required.
- **Rule Completeness**: The system relies on human-crafted heuristics for compound risk. Edge cases outside the ruleset rely solely on the anomaly detector, which cannot label the *type* of hazard.
- **Data Quality Sensitivity**: If sensor dropouts occur synchronously, the anomaly detector may trigger false alarms.

## 11. Failures Encountered
- Parquet saving issues due to missing `pyarrow` engine inside the conda environment required an emergency install.
- Pydantic validation errors for domain models during feature assembly revealed mismatched arguments between the raw data ingestion mapping and the canonical plant-state domain models. This highlighted the importance of robust schema validation at the perimeter.

## 12. Hardware / Latency Notes
- Feature extraction and validation runs extremely quickly. 
- Pandas operations over 1,500 row datasets take <1s to process locally.
- Inference latency for the Isolation Forest + Rule Engine pipeline is negligible on modern hardware.

## 13. Future Work
- Integration with live Historian databases and the CCTV stream for computer-vision driven `WorkerEvent` logs.
- Introduction of a graph-based reasoning system to map propagation across multiple zones.
- Online training loops for the anomaly detector to adapt to long-term drift.
