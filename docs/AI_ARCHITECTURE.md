# SpecGuard — AI Architecture for Compound Industrial Risk Detection

> **Author**: AI Architecture Team  
> **Date**: 2026-07-20  
> **Version**: 1.0  
> **Status**: Proposed — awaiting team review  
> **Scope**: Modular AI pipeline for CDU-100 compound risk detection

---

## Design Principles

1. **Explainable**: Every risk score has a traceable chain of evidence
2. **Deterministic where safety-critical**: Rules always produce the same output for the same input — no stochastic risk assessments for critical hazards
3. **Configurable**: All thresholds, weights, and rules in external configuration files
4. **Testable**: Every layer independently testable with synthetic data
5. **Modular**: Clean layer boundaries — any layer can be replaced or disabled
6. **Framework-independent**: No dependency on FastAPI, databases, or frontends
7. **Dual-mode**: Works on batch CSV files and streaming event-by-event
8. **Fail-safe on missing data**: Missing sensors degrade gracefully, never silently suppress risk
9. **No LLM in the scoring loop**: The numerical risk score is computed deterministically
10. **Simplest effective method**: Rules → Trends → Isolation Forest → Supervised (in that priority order)

---

## System Overview

```
                    ┌─────────────────────────────────────────────┐
                    │           DATA SOURCES                       │
                    │  SCADA │ IoT Gas │ Equipment │ PTW │ Maint  │
                    │  Worker│ CCTV    │ Shift Log │ Scenario     │
                    └─────────┬───────────────────────────────────┘
                              │
                    ┌─────────▼───────────────────────────────────┐
                    │     A. INPUT ADAPTERS                        │
                    │  Parse, normalize, map IDs, type-cast        │
                    └─────────┬───────────────────────────────────┘
                              │
                    ┌─────────▼───────────────────────────────────┐
                    │     B. PLANT-STATE ASSEMBLER                 │
                    │  Unified snapshot per (zone, timestamp)      │
                    └─────────┬───────────────────────────────────┘
                              │
                    ┌─────────▼───────────────────────────────────┐
                    │     C. DATA VALIDATION                       │
                    │  Quality checks, gap detection, clamping     │
                    └─────────┬───────────────────────────────────┘
                              │
                    ┌─────────▼───────────────────────────────────┐
                    │     D. FEATURE ENGINEERING                   │
                    │  Rolling stats, rates, cross-sensor, permits │
                    └─────────┬───────────────────────────────────┘
                              │
                    ┌─────────▼───────────────────────────────────┐
                    │     E. RISK DETECTION (5 layers)             │
                    │  E1. Threshold Baseline                      │
                    │  E2. Compound Rule Engine (35 rules)         │
                    │  E3. Unsupervised Anomaly (Isolation Forest)  │
                    │  E4. Supervised Classifier (optional)         │
                    │  E5. Risk Fusion                             │
                    └─────────┬───────────────────────────────────┘
                              │
                    ┌─────────▼───────────────────────────────────┐
                    │     F. OUTPUT GENERATION                     │
                    │  Risk score, severity, explanation, evidence │
                    └─────────┬───────────────────────────────────┘
                              │
                    ┌─────────▼───────────────────────────────────┐
                    │     G. EVALUATION FRAMEWORK                  │
                    │  Metrics, calibration, ablation studies       │
                    └─────────────────────────────────────────────┘
```

---

## Layer A: Input Adapters

### Purpose
Consume heterogeneous data from the digital twin simulator (CSV/JSONL) and normalize it into a canonical internal representation.

### Adapter Registry

| Adapter | Source | Input Format | Output Type | Key Fields |
|---|---|---|---|---|
| `SCADAAdapter` | `scada.csv` or JSONL | Flat row | `SCADAReading` | 14 process variables + alarm states |
| `GasSensorAdapter` | `gas.csv` or JSONL | Flat row | `GasReading` | HC %LEL, H2S ppm, VOC ppm, O2 %, per zone |
| `EquipmentStateAdapter` | `equipment.csv` or JSONL | Flat row | `EquipmentSnapshot` | State, health, failure flags |
| `PermitAdapter` | `permits.csv` or JSONL | Flat row / event | `PermitState` | Active permits by type and zone |
| `MaintenanceAdapter` | `maintenance.csv` or JSONL | Flat row / event | `MaintenanceState` | Active activities, isolation status |
| `WorkerAdapter` | `workers.csv` or JSONL | Flat row / event | `WorkerSnapshot` | Zone, task, PPE, time-in-zone |
| `CCTVAdapter` | `cctv.csv` or JSONL | Event | `CCTVEvent` | Camera, zone, event type, confidence |
| `ShiftLogAdapter` | `shift_logs.csv` or JSONL | Sparse event | `ShiftLogEntry` | Severity, message, operator |
| `ScenarioAdapter` | JSONL metadata | Metadata | `ScenarioMetadata` | scenario_id, event_label (ground truth) |

### ID Mapping Layer

A critical sub-component that resolves the schema mismatches documented in the audit:

```python
@dataclass
class IDMapper:
    """Bidirectional mapping between simulator IDs and master model IDs."""
    
    zone_map: dict[str, str]         # "Zone_A" ↔ "ZONE_A"
    equipment_map: dict[str, str]    # "PMP-301" ↔ "P-101A"  
    worker_map: dict[str, str]       # "W001" ↔ "WRK-001"
    camera_map: dict[str, str]       # "CAM-C01" ↔ "CAM-104"
    sensor_map: dict[str, str]       # "pipeline_pressure" ↔ "PT-101"
    
    def to_canonical(self, domain: str, raw_id: str) -> str: ...
    def to_simulator(self, domain: str, canonical_id: str) -> str: ...
```

### Adapter Interface

```python
class BaseAdapter(Protocol):
    def parse_row(self, row: dict[str, Any]) -> DataRecord: ...
    def parse_batch(self, df: pd.DataFrame) -> list[DataRecord]: ...
    def validate_schema(self, row: dict[str, Any]) -> list[str]: ...  # Returns validation errors
```

---

## Layer B: Plant-State Assembler

### Purpose
Merge all adapter outputs into a single unified `PlantSnapshot` for each timestamp, organized by zone.

### Data Structure

```python
@dataclass
class ZoneSnapshot:
    """Complete state of a single zone at a single timestamp."""
    zone_id: str                          # Canonical zone ID (ZONE_A)
    timestamp: str                        # ISO 8601
    tick: int
    
    # Sensor readings (keyed by canonical sensor ID)
    scada_readings: dict[str, float]      # PT-101: 0.5, FT-101: 300.0, ...
    gas_readings: GasReading              # HC, H2S, VOC, O2
    
    # Alarm states
    active_alarms: dict[str, str]         # sensor_id → alarm level
    
    # Equipment in this zone
    equipment_states: dict[str, EquipmentSnapshot]
    
    # Human/organizational state
    workers_present: list[WorkerSnapshot]
    worker_count: int
    active_permits: list[PermitState]
    active_maintenance: list[MaintenanceState]
    
    # CCTV events (since last snapshot)
    cctv_events: list[CCTVEvent]
    
    # Shift context
    current_shift: str                    # "day" / "night"
    shift_elapsed_seconds: int

@dataclass
class PlantSnapshot:
    """Complete plant state at a single timestamp."""
    timestamp: str
    tick: int
    scenario_id: str                      # Ground truth (for training)
    event_label: str                      # Ground truth phase label
    
    zones: dict[str, ZoneSnapshot]        # zone_id → ZoneSnapshot
    
    # Plant-wide state
    esd_active: bool
    total_alarm_count: int
    shift_log: ShiftLogEntry | None
    
    # Cross-zone derived
    adjacent_zone_pairs: list[tuple[str, str]]  # For proximity checks
```

### Assembly Logic

1. Parse timestamp from input row
2. Distribute fields to appropriate zone based on sensor-zone mapping
3. Aggregate worker data per zone
4. Attach permit and maintenance state to zones
5. Carry forward stale readings with data quality flags
6. Return complete `PlantSnapshot`

---

## Layer C: Data Validation

### Purpose
Detect and flag data quality issues that could affect risk assessment. Never silently discard data — flag and continue.

### Validation Checks

| Check | Input | Logic | Output |
|---|---|---|---|
| **Missing values** | Any field = `None` or `NaN` | Count per sensor per window | `DataQualityFlag.MISSING` |
| **Duplicate timestamps** | Consecutive identical timestamps | Detect, keep last | `DataQualityFlag.DUPLICATE` |
| **Invalid sensor IDs** | Sensor ID not in master registry | Log warning, pass through | `DataQualityFlag.UNKNOWN_SENSOR` |
| **Invalid equipment refs** | Equipment ID not in registry | Log warning | `DataQualityFlag.UNKNOWN_EQUIPMENT` |
| **Stale readings** | Same value for N consecutive ticks | Configurable N (default: 60) | `DataQualityFlag.STALE` |
| **Out-of-order events** | Tick N followed by tick < N | Reorder or flag | `DataQualityFlag.OUT_OF_ORDER` |
| **Impossible values** | Pressure < 0, temperature < -273.15, %LEL > 100 | Domain-specific bounds | `DataQualityFlag.IMPOSSIBLE` |
| **Conflicting actuator states** | ESD active + pump running | Cross-check state consistency | `DataQualityFlag.CONFLICTING` |
| **Sensor dropout** | Quality = "BAD" | Track dropout rate per sensor | `DataQualityFlag.DROPOUT` |
| **Rate of change spike** | |Δvalue| > 10σ in 1 tick | Physical impossibility filter | `DataQualityFlag.SPIKE` |

### Output

```python
@dataclass
class ValidationResult:
    is_valid: bool
    flags: list[DataQualityFlag]
    missing_fraction: float           # 0.0 to 1.0
    stale_sensors: list[str]
    impossible_values: dict[str, float]
    conflicts: list[str]
```

The validation result is attached to the `PlantSnapshot` and propagated to the output as `data_quality_warnings`.

---

## Layer D: Feature Engineering

### Purpose
Transform raw sensor readings and state data into ML-ready feature vectors. Features are computed per zone per timestamp.

### Feature Categories

#### D.1 Current Values (Passthrough)
- All SCADA sensor readings
- All gas readings
- Equipment health values
- Binary states (ESD, permit active, pump running)

#### D.2 Rolling Statistics

| Feature | Windows | Per Sensor |
|---|---|---|
| Rolling mean | 30s, 60s, 300s, 900s | All continuous sensors |
| Rolling std | 30s, 60s, 300s, 900s | All continuous sensors |
| Rolling min | 60s, 300s | All continuous sensors |
| Rolling max | 60s, 300s | All continuous sensors |
| Rolling median | 300s | All continuous sensors |
| Z-score (current vs. rolling mean) | 300s | All continuous sensors |

#### D.3 Rate of Change

| Feature | Computation | Per Sensor |
|---|---|---|
| First derivative (velocity) | `(x[t] - x[t-1]) / dt` | All continuous |
| Smoothed derivative | `(x[t] - x[t-10]) / 10` | All continuous |
| Second derivative (acceleration) | `(dx[t] - dx[t-1]) / dt` | All continuous |
| Sign of derivative | `sign(dx)` | All continuous |
| Derivative streak | Consecutive ticks with same sign | All continuous |

#### D.4 Duration Features

| Feature | Computation |
|---|---|
| Time since last alarm | `tick - last_alarm_tick` per sensor |
| Time in current state | Equipment state duration |
| Time since shift start | `shift_elapsed_seconds` |
| Time since last shift change | Continuous counter |
| Worker time in zone | From worker event data |
| Permit active duration | `tick - permit.activated_tick` |
| Maintenance elapsed | `tick - maintenance.started_tick` |
| Time since last CCTV event | Per zone |

#### D.5 Cross-Sensor Features

| Feature | Computation | Domain Rationale |
|---|---|---|
| Pressure-flow ratio | `pressure / flow` per pipeline | Pump performance indicator |
| Temperature-pressure deviation | Residual from expected T-P curve | Phase change / leak indicator |
| Pump power vs. flow | `power / flow` | Bearing friction indicator |
| Vibration × temperature | `vibration * temperature` | Compound bearing stress |
| Gas concentration gradient | `HC[zone_A] - HC[zone_B]` | Leak source identification |
| Pressure differential across equipment | `P_upstream - P_downstream` | Blockage / leak detection |

#### D.6 Equipment Health Features

| Feature | Source |
|---|---|
| Bearing health | Pump state dict |
| Seal health | Pump state dict |
| Health decay rate | `(health[t-300] - health[t]) / 300` |
| Equipment age factor | Degradation rate × time |
| Failure proximity score | `max(0, 1 - health / failure_threshold)` |
| Standby availability | Standby pump running? |

#### D.7 Permit Features

| Feature | Computation |
|---|---|
| Hot work active in zone | Binary per zone |
| Confined space entry active | Binary per zone |
| Permit count in zone | Count of active permits |
| Permit type conflict potential | Hot work + gas > threshold |
| Gas test completed | Boolean from permit state |
| Permit duration remaining | `permit.duration - elapsed` |

#### D.8 Maintenance and Isolation Features

| Feature | Computation |
|---|---|
| Active maintenance in zone | Binary |
| Isolation complete | Boolean |
| Equipment under maintenance | List of equipment IDs |
| LOTO status | Derived from isolation status |
| Maintenance risk level | From maintenance task catalogue |
| Simultaneous maintenance count | Count across zones |

#### D.9 Worker Exposure Features

| Feature | Computation |
|---|---|
| Workers in zone | Count |
| Workers exceeding exposure limit | Count where `time_in_zone > MAX_ZONE_EXPOSURE * 0.8` |
| PPE non-compliance in zone | Count / fraction |
| Contractor present without gas monitor | Binary |
| Night shift manning level | Worker count vs. expected |
| Workers in adjacent hazardous zones | Count using adjacency graph |

#### D.10 Geospatial Proximity Features

| Feature | Computation |
|---|---|
| Hot work near gas source | Hot work zone adjacent to zone with HC > threshold |
| Worker near failed equipment | Worker in zone with failed equipment |
| Maintenance near active process | Maintenance zone with active permits |
| Emergency route accessible | Derived from zone accessibility model |

#### D.11 Data Quality Features

| Feature | Source |
|---|---|
| Missing sensor fraction | Validation result |
| Stale sensor count | Validation result |
| Dropout rate (rolling) | Count of dropouts in last 300s |
| Data age (staleness) | Max stale duration across sensors |
| Conflict count | Validation result |

### Feature Vector

```python
@dataclass
class FeatureVector:
    zone_id: str
    timestamp: str
    tick: int
    features: dict[str, float]          # Feature name → value
    feature_names: list[str]            # Ordered list for ML models
    data_quality: ValidationResult
    
    def to_numpy(self) -> np.ndarray:
        """Convert to ordered numpy array for ML models."""
        return np.array([self.features[name] for name in self.feature_names])
```

---

## Layer E: Risk Detection

### E1. Single-Sensor Threshold Baseline

**Purpose**: Detect simple threshold exceedances using the master asset model sensor specifications.

**Logic**: For each sensor at each tick:

```
if value >= critical_threshold:   → CRITICAL alarm
elif value >= warning_threshold:  → WARNING alarm  
elif value <= low_critical:       → CRITICAL alarm (low)
elif value <= low_warning:        → WARNING alarm (low)
else:                             → NORMAL
```

**Input**: Raw sensor values + `SensorSpec` from master asset model.

**Output**: `list[ThresholdAlert]` — sensor ID, alarm level, value, threshold.

**Properties**: Fully deterministic. Zero latency. High recall for single-sensor faults. High false alarm rate (by design — downstream layers filter).

---

### E2. Deterministic Compound-Rule Engine

**Purpose**: Implement all 35 compound risk rules from the master asset model as executable logic.

**Architecture**:

```python
@dataclass
class RuleCondition:
    """Single condition within a compound rule."""
    field: str                    # Feature or sensor name
    operator: str                 # ">", "<", ">=", "<=", "==", "in", "between"
    threshold: Any               # Numeric threshold or enum value
    description: str             # Human-readable description

@dataclass 
class CompoundRule:
    """A compound risk rule with multiple conditions."""
    rule_id: int                  # 1-35
    name: str
    conditions: list[RuleCondition]  # All must be True (AND logic)
    compound_risk: str            # Risk description
    severity: str                 # "Medium" | "High" | "Critical" | "Catastrophic"
    hazard_type: str              # "Explosion", "Toxic Exposure", etc.
    explanation: str              # Why this is dangerous
    applicable_zones: list[str]   # Zones where this rule applies
    
    def evaluate(self, snapshot: PlantSnapshot, features: FeatureVector) -> RuleResult | None:
        """Evaluate this rule against current state. Returns result if triggered."""
        ...

@dataclass
class RuleResult:
    rule_id: int
    triggered: bool
    severity: str
    confidence: float             # 0-1, based on how far past thresholds
    matched_conditions: list[str]
    failed_conditions: list[str]  # Conditions that prevented full match
    partial_match_score: float    # Fraction of conditions met (for early warning)
```

**Partial Match Scoring**: Rules report not just binary triggered/not-triggered, but a **partial match score** (e.g., 2 of 3 conditions met = 0.67). This enables early warning before all conditions align.

**Rule Evaluation Order**: Rules are evaluated in severity order (Catastrophic first) to support early exit when a maximum-severity rule fires.

**Properties**: Fully deterministic. Explainable. Directly traceable to master asset model. Configurable via external rule definitions (YAML/JSON).

---

### E3. Unsupervised Anomaly Detector

**Purpose**: Detect novel or unusual patterns not covered by predefined rules.

**Primary Model**: **Isolation Forest**

**Justification**:
- No labeled anomaly data required (the 100K "normal" rows are the training set)
- Handles high-dimensional feature vectors well
- Linear time complexity — suitable for real-time
- Resistant to irrelevant features
- Produces anomaly scores (not just binary)
- Interpretable via feature importance

**Architecture**:

```python
class AnomalyDetector:
    def __init__(self, config: AnomalyConfig):
        self.model = IsolationForest(
            n_estimators=200,
            max_samples='auto',
            contamination=0.01,     # Expected 1% anomaly rate
            random_state=42,
        )
        self.scaler = StandardScaler()
        self.feature_names: list[str] = []
        
    def fit(self, normal_data: np.ndarray, feature_names: list[str]) -> None:
        """Train on normal operating data only."""
        self.feature_names = feature_names
        scaled = self.scaler.fit_transform(normal_data)
        self.model.fit(scaled)
    
    def score(self, features: np.ndarray) -> AnomalyResult:
        """Score a single observation. Returns anomaly score 0-1."""
        scaled = self.scaler.transform(features.reshape(1, -1))
        raw_score = -self.model.score_samples(scaled)[0]  # Higher = more anomalous
        normalized = self._normalize_score(raw_score)
        return AnomalyResult(
            score=normalized,
            is_anomaly=normalized > self.config.threshold,
            top_contributing_features=self._explain(features, scaled),
        )
```

**Feature Selection for Anomaly Detection**:
- Use only continuous SCADA + gas sensor features (not binary states)
- Include rolling statistics (60s, 300s windows)
- Include rate-of-change features
- Exclude permit/maintenance/worker features (these change state discretely)

**Complementary Model** (optional): **Local Outlier Factor (LOF)** as a second opinion, particularly for density-based anomalies that Isolation Forest may miss.

---

### E4. Supervised Classifier (Optional)

**Purpose**: Classify risk type when labeled data quality supports it.

**When to enable**: Only when:
1. At least 100K normal + 30K fault rows are available
2. Cross-validated F1 > 0.7 on held-out fault scenarios
3. The classifier adds detection capability beyond rules + anomaly detection

**Model**: **Gradient Boosted Trees** (LightGBM or XGBoost)

**Architecture**:

```python
class SupervisedClassifier:
    def __init__(self, config: ClassifierConfig):
        self.model = None           # Trained model
        self.label_encoder = None   # Maps event_label → class
        self.is_trained: bool = False
        
    def train(self, features: np.ndarray, labels: np.ndarray) -> TrainResult:
        """Train multi-class classifier on scenario-labeled data."""
        ...
    
    def predict(self, features: np.ndarray) -> ClassifierResult:
        """Predict risk class and probability."""
        if not self.is_trained:
            return ClassifierResult(enabled=False)
        proba = self.model.predict_proba(features.reshape(1, -1))[0]
        return ClassifierResult(
            predicted_class=...,
            class_probabilities=dict(zip(self.label_encoder.classes_, proba)),
            confidence=max(proba),
        )
```

**Label Mapping**:

| Scenario Label | Risk Class |
|---|---|
| `normal` | 0 — Normal |
| `*_onset`, `*_degradation` | 1 — Early Warning |
| `*_detected`, `*_rising` | 2 — Developing |
| `*_failure`, `*_exposure`, `*_explosive_range` | 3 — Critical |
| `*_esd`, `*_emergency`, `*_maximum_risk` | 4 — Emergency |
| `*_resolved`, `*_stabilizing`, `*_aftermath` | 5 — Recovery |

---

### E5. Risk Fusion Layer

**Purpose**: Combine outputs from all detection layers into a single coherent risk assessment.

**Fusion Strategy**: **Weighted maximum with escalation logic**

```python
class RiskFusion:
    def fuse(self,
             threshold_alerts: list[ThresholdAlert],
             rule_results: list[RuleResult],
             anomaly_result: AnomalyResult,
             classifier_result: ClassifierResult | None,
             data_quality: ValidationResult) -> FusedRiskScore:
        
        # 1. Base score from threshold alerts
        threshold_score = self._score_thresholds(threshold_alerts)
        
        # 2. Rule engine score (dominant when rules fire)
        rule_score = self._score_rules(rule_results)
        
        # 3. Anomaly score (supplementary)
        anomaly_score = anomaly_result.score * self.config.anomaly_weight
        
        # 4. Classifier score (optional supplementary)
        classifier_score = self._score_classifier(classifier_result)
        
        # 5. Fusion: rules dominate, anomaly supplements
        if rule_score > 0:
            # When compound rules fire, they set the floor
            base = max(rule_score, threshold_score)
            # Anomaly can only escalate, not reduce
            combined = base + anomaly_score * 0.2
        else:
            # No rules fired — use max of other signals
            combined = max(threshold_score, anomaly_score * 0.6, classifier_score)
        
        # 6. Data quality penalty
        if data_quality.missing_fraction > 0.3:
            # High missing data → increase score (fail-safe)
            combined = max(combined, 30.0)  
            # Missing data in safety system = elevated risk
        
        # 7. Clamp to 0-100
        final_score = max(0.0, min(100.0, combined))
        
        return FusedRiskScore(
            overall_score=final_score,
            severity=self._score_to_severity(final_score),
            component_scores={
                "threshold": threshold_score,
                "rules": rule_score,
                "anomaly": anomaly_score,
                "classifier": classifier_score,
            },
        )
```

**Score-to-Severity Mapping**:

| Score Range | Severity | Meaning |
|---|---|---|
| 0–15 | Normal | All systems operating within bounds |
| 16–35 | Low | Minor deviations, monitoring recommended |
| 36–55 | Medium | Significant deviation, investigation required |
| 56–75 | High | Dangerous conditions developing, intervention needed |
| 76–90 | Critical | Immediate action required, personnel at risk |
| 91–100 | Catastrophic | Emergency shutdown / evacuation conditions |

**Escalation Rules**:
- Any Catastrophic compound rule firing → score ≥ 85
- Any 2+ compound rules firing simultaneously → score += 15
- ESD activated → score = 95
- Missing safety sensor during active hazard → score += 20

---

## Layer F: Output Generation

### Risk Assessment Output Schema

```python
@dataclass
class RiskAssessment:
    """Complete risk assessment for one zone at one timestamp."""
    
    # Identity
    assessment_id: str                    # UUID
    zone_id: str                          # Canonical zone ID
    timestamp: str                        # ISO 8601
    tick: int
    
    # Risk Score
    overall_risk_score: float             # 0.0 to 100.0
    severity: str                         # Normal/Low/Medium/High/Critical/Catastrophic
    
    # Hazard Classification
    predicted_hazard_type: str            # "Explosion", "Toxic Exposure", "Fire", etc.
    confidence: float                     # 0.0 to 1.0
    
    # Contributing Factors
    contributing_factors: list[ContributingFactor]
    
    # Triggered Rules
    triggered_rules: list[TriggeredRule]
    partial_rules: list[PartialRule]      # Rules with >50% conditions met
    
    # Anomaly Detection
    anomaly_score: float                  # 0.0 to 1.0
    anomaly_contributing_features: list[str]
    
    # Baseline Status
    baseline_status: dict[str, str]       # sensor_id → NORMAL/HIGH/HIHI/LOW
    sensors_in_alarm: int
    
    # Prediction
    estimated_lead_time_seconds: int | None  # Estimated time to incident if unmitigated
    trend_direction: str                  # "improving" / "stable" / "worsening"
    
    # Data Quality
    data_quality_warnings: list[str]
    data_completeness: float              # 0.0 to 1.0
    
    # Explainability
    human_readable_explanation: str        # Natural language summary
    machine_readable_evidence: list[Evidence]

@dataclass
class ContributingFactor:
    factor_type: str                      # "sensor", "equipment", "permit", "worker", "rule"
    factor_id: str                        # Sensor/equipment/rule ID
    description: str                      # Human-readable
    current_value: Any
    threshold: Any
    contribution_weight: float            # 0-1

@dataclass
class TriggeredRule:
    rule_id: int
    rule_name: str
    severity: str
    matched_conditions: list[str]
    
@dataclass
class Evidence:
    evidence_type: str                    # "sensor_reading", "alarm", "rule", "anomaly", "state"
    source_id: str
    value: Any
    context: str
```

### Human-Readable Explanation Generation

The explanation is built deterministically from contributing factors:

```python
def generate_explanation(assessment: RiskAssessment) -> str:
    """Generate natural-language explanation from structured evidence."""
    parts = []
    
    if assessment.triggered_rules:
        rule = assessment.triggered_rules[0]  # Highest severity
        parts.append(f"COMPOUND RISK: {rule.rule_name} (Severity: {rule.severity})")
        parts.append(f"Conditions matched: {', '.join(rule.matched_conditions)}")
    
    if assessment.sensors_in_alarm > 0:
        parts.append(f"{assessment.sensors_in_alarm} sensor(s) in alarm state")
    
    for factor in assessment.contributing_factors[:3]:  # Top 3
        parts.append(f"• {factor.description}: {factor.current_value} "
                     f"(threshold: {factor.threshold})")
    
    if assessment.data_quality_warnings:
        parts.append(f"⚠ Data quality: {', '.join(assessment.data_quality_warnings[:2])}")
    
    return " | ".join(parts)
```

---

## Layer G: Evaluation Framework

### G.1 Core Metrics

| Metric | Computation | Target |
|---|---|---|
| **False Negative Rate (FNR)** | `FN / (FN + TP)` at severity ≥ High | < 5% (safety-critical) |
| **Recall** | `TP / (TP + FN)` per hazard class | > 95% for Catastrophic, > 90% for Critical |
| **Precision** | `TP / (TP + FP)` per hazard class | > 70% (accept some false alarms for safety) |
| **F1 Score** | Harmonic mean of P and R | > 0.80 |
| **False Alarms per Simulated Hour** | `FP / (total_ticks / 3600)` | < 2 per hour |
| **Detection Latency** | Ticks between fault onset and first alert | < 60s for gas leaks, < 300s for equipment degradation |
| **Prediction Lead Time** | Ticks between alert and peak severity phase | Report distribution |
| **Scenario-Level Detection Rate** | Fraction of fault scenarios where risk score > 50 during fault phase | 100% for all 6 fault scenarios |
| **Calibration** | Reliability diagram (predicted severity vs. actual) | Monotonically increasing |

### G.2 Evaluation Protocol

```python
class Evaluator:
    def evaluate_scenario(self, 
                          assessments: list[RiskAssessment],
                          ground_truth: list[str],    # event_labels
                          scenario_id: str) -> ScenarioMetrics:
        """Evaluate AI performance on a single scenario run."""
        ...
    
    def evaluate_all(self,
                     scenario_results: dict[str, ScenarioMetrics]) -> OverallMetrics:
        """Aggregate metrics across all scenarios."""
        ...
    
    def ablation_study(self,
                       data: pd.DataFrame,
                       layers_to_disable: list[str]) -> AblationResult:
        """Measure contribution of each detection layer."""
        ...
```

### G.3 Ablation Studies

| Experiment | Disabled Layer | Measures |
|---|---|---|
| Rules only | E3, E4 | Baseline detection from rules alone |
| Anomaly only | E2, E4 | Unsupervised detection capability |
| Rules + Anomaly | E4 | Expected production configuration |
| Full pipeline | None | Maximum detection capability |
| No features | D (raw values only) | Feature engineering contribution |

### G.4 Label Mapping for Evaluation

```python
LABEL_TO_SEVERITY = {
    "normal": 0,
    "normal_hot_work": 0,
    # Onset / early warning → Low
    "seal_degradation": 1, "fan_degradation": 1, "early_wear": 1,
    "compound_onset": 1, "confined_space_permit": 1,
    # Developing → Medium  
    "leak_onset": 2, "performance_loss": 2, "advanced_wear": 2,
    "hot_work_leak_onset": 2, "confined_space_o2_dropping": 2,
    # Critical → High
    "leak_detected": 3, "gas_accumulation": 3, "critical_vibration": 3,
    "hot_work_gas_rising": 3, "hot_work_gas_detected": 3,
    "confined_space_entry": 3, "compound_pump_leak": 3,
    "compound_vent_failure": 3,
    # Emergency → Critical
    "leak_confirmed": 4, "failure": 4, "compound_explosive_range": 4,
    "confined_space_exposure": 4, "hot_work_suspended": 4,
    # Maximum → Catastrophic
    "compound_maximum_risk": 5, "compound_esd": 5,
    "emergency_isolation": 5, "emergency_ventilation": 5,
    # Recovery → decreasing
    "switchover": 2, "stabilized": 1,
    "leak_secured": 1, "recovery": 1,
    "hot_work_emergency": 4, "hot_work_resolved": 1,
    "compound_emergency": 4, "compound_stabilizing": 2,
    "confined_space_rescue": 4, "confined_space_aftermath": 2,
}
```

---

## Proposed Python Package Structure

```
specguard_ai/
├── __init__.py
├── version.py
│
├── config/                          # External configuration
│   ├── __init__.py
│   ├── settings.py                  # Global settings, paths, defaults
│   ├── id_mapping.yaml              # Simulator ↔ master model ID maps
│   ├── sensor_specs.yaml            # Sensor thresholds from master model
│   ├── compound_rules.yaml          # 35 compound rules as structured data
│   └── model_params.yaml            # ML model hyperparameters
│
├── adapters/                        # Layer A: Input adapters
│   ├── __init__.py
│   ├── base.py                      # BaseAdapter protocol
│   ├── scada.py
│   ├── gas.py
│   ├── equipment.py
│   ├── permits.py
│   ├── maintenance.py
│   ├── workers.py
│   ├── cctv.py
│   ├── shift_logs.py
│   ├── scenario.py                  # Ground truth adapter
│   └── id_mapper.py                 # ID reconciliation layer
│
├── assembler/                       # Layer B: Plant-state assembler
│   ├── __init__.py
│   ├── snapshot.py                  # PlantSnapshot, ZoneSnapshot dataclasses
│   └── assembler.py                 # Assembly logic
│
├── validation/                      # Layer C: Data validation
│   ├── __init__.py
│   ├── validators.py                # All validation checks
│   └── quality.py                   # DataQualityFlag, ValidationResult
│
├── features/                        # Layer D: Feature engineering
│   ├── __init__.py
│   ├── base.py                      # FeatureVector dataclass
│   ├── rolling.py                   # Rolling statistics
│   ├── derivatives.py               # Rate of change, acceleration
│   ├── duration.py                  # Time-since features
│   ├── cross_sensor.py              # Cross-sensor features
│   ├── equipment.py                 # Equipment health features
│   ├── permits.py                   # Permit features
│   ├── maintenance.py               # Maintenance features
│   ├── workers.py                   # Worker exposure features
│   ├── proximity.py                 # Geospatial proximity features
│   ├── data_quality.py              # DQ features
│   └── pipeline.py                  # Feature pipeline orchestrator
│
├── detection/                       # Layer E: Risk detection
│   ├── __init__.py
│   ├── threshold.py                 # E1: Single-sensor threshold baseline
│   ├── rules/                       # E2: Compound rule engine
│   │   ├── __init__.py
│   │   ├── engine.py                # Rule evaluation engine
│   │   ├── rule_defs.py             # Rule dataclass definitions
│   │   └── rule_loader.py           # Load rules from YAML
│   ├── anomaly/                     # E3: Unsupervised anomaly detection
│   │   ├── __init__.py
│   │   ├── isolation_forest.py      # Primary anomaly model
│   │   └── explain.py               # Anomaly feature attribution
│   ├── classifier/                  # E4: Optional supervised model
│   │   ├── __init__.py
│   │   ├── trainer.py               # Model training pipeline
│   │   └── predictor.py             # Inference
│   └── fusion.py                    # E5: Risk fusion layer
│
├── output/                          # Layer F: Output generation
│   ├── __init__.py
│   ├── schema.py                    # RiskAssessment, Evidence dataclasses
│   ├── explanation.py               # Human-readable explanation generator
│   └── formatter.py                 # JSON / dict output formatting
│
├── evaluation/                      # Layer G: Evaluation framework
│   ├── __init__.py
│   ├── metrics.py                   # All metric computations
│   ├── evaluator.py                 # Scenario-level evaluation
│   ├── ablation.py                  # Ablation study runner
│   ├── calibration.py               # Score calibration
│   └── reports.py                   # Markdown report generation
│
├── pipeline.py                      # Master pipeline: adapters → ... → output
│
├── data_types.py                    # All shared dataclasses and enums
│
└── utils/                           # Shared utilities
    ├── __init__.py
    ├── logging.py                   # Structured logging
    └── serialization.py             # JSON/YAML serialization helpers

tests/
├── __init__.py
├── conftest.py                      # Shared fixtures, sample data
├── test_adapters/
├── test_assembler/
├── test_validation/
├── test_features/
├── test_detection/
│   ├── test_threshold.py
│   ├── test_rules.py
│   ├── test_anomaly.py
│   └── test_fusion.py
├── test_output/
├── test_evaluation/
├── test_pipeline.py                 # End-to-end integration tests
└── fixtures/                        # Sample CSV/JSONL for testing
    ├── normal_100rows.csv
    ├── gas_leak_100rows.csv
    └── explosion_risk_100rows.csv
```

---

## Data Flow (Batch Mode)

```
1. simulate.py --scenario all --format both --split → CSV/JSONL files
2. specguard_ai.pipeline.run_batch(data_dir="./output")
   ├── Adapters parse CSV files into typed records
   ├── Assembler merges into PlantSnapshot per tick
   ├── Validator flags quality issues
   ├── Feature pipeline computes ~150 features per zone per tick
   ├── Detection layers score risk:
   │   ├── Threshold: 55 sensor checks
   │   ├── Rules: 35 compound rule evaluations  
   │   ├── Anomaly: Isolation Forest score
   │   └── Fusion: combined 0-100 score
   ├── Output: RiskAssessment per zone per tick
   └── Evaluation: metrics against ground-truth labels
```

## Data Flow (Streaming Mode)

```
1. External system pushes one row/event at a time
2. specguard_ai.pipeline.process_event(event_dict)
   ├── Adapter parses single event
   ├── Assembler updates rolling PlantSnapshot (in memory)
   ├── Validator checks single row
   ├── Feature pipeline updates rolling windows
   ├── Detection layers score (< 10ms per tick target)
   └── Output: RiskAssessment (returned synchronously)
```

---

## Assumptions

1. The digital twin simulator output is the sole data source during development.
2. The `event_label` field provides sufficient ground truth for supervised training.
3. The 35 compound rules from the master asset model are the minimum required detection capability.
4. Isolation Forest is the appropriate baseline anomaly model (will validate empirically).
5. The AI package will be distributed as a pip-installable package.
6. Feature computation must run in < 10ms per tick for streaming viability.
7. Risk scores are not used to trigger automatic shutdowns — they inform human operators.
8. The system must produce meaningful output even with 30%+ missing sensor data.
9. No deep learning models will be used unless simpler methods demonstrably fail.
10. The evaluation framework uses simulated time (ticks), not wall-clock time.
