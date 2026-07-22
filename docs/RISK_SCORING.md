# Risk Scoring and Fusion Algorithm

> **Module**: `backend.app.ai.detection.fusion`
> **Purpose**: Produce the final explainable, calibrated risk assessment (0-100) by combining the deterministic compound rules, the unsupervised anomaly detection model, contextual modifiers, and single-sensor baseline data.

## Algorithm Hierarchy

The `RiskFusionEngine` is explicitly designed **not** to be a simple weighted average. It follows a safety-oriented hierarchical logic:

1. **Hazard-Specific Tracking**: Scores are calculated independently for primary hazards (e.g., `FLASH_FIRE`, `TOXIC_EXPOSURE`). The overall score is the maximum of the active hazards.
2. **Rule-Based Minimum Floors**: If a critical deterministic rule triggers, it imposes a hard floor on the hazard score (e.g., a score of 85).
3. **Contextual Modifiers**: Multipliers are applied based on situational context (e.g., `worker_present`, `active_hot_work`), capped by a maximum total modifier config.
4. **Anomaly Contribution**: The anomaly model acts as supplementary evidence, contributing +5 to +20 points depending on severity, rather than completely overriding deterministic rules.
5. **Duplicate Evidence Prevention**: All features used by rules or modifiers are mapped to "evidence families" (e.g., `gas`, `ventilation`, `permit`). If a rule has already claimed the `permit` family, generic permit modifiers are skipped.
6. **Decay and Hysteresis**: Risk scores persist and decay slowly over time to prevent rapid oscillation or "alarm chattering" at the threshold borders.

## Severity Levels
- **0–19**: NORMAL
- **20–39**: ADVISORY
- **40–59**: WARNING
- **60–79**: HIGH
- **80–100**: CRITICAL

## Confidence Calculation
A high risk score can have low confidence. Confidence starts at 100% and is penalized for:
- Missing sensors (-15)
- Stale sensor values (-10)

## Lead Time
The engine tracks the first time a compound risk triggers (>= WARNING) versus the first time a traditional independent baseline alarm triggers.
- `lead_time_vs_baseline` (seconds): Positive when the compound rule detects the hazard before the standard threshold is breached.

## Explainability
Deterministic explanations are dynamically generated outlining the primary hazard, severity, overall score, triggered rules, and baseline status. 

Example:
> "FLASH_FIRE risk is CRITICAL at 86/100. Triggered rules: CRR-001. Baseline alarms are active."
