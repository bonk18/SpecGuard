# SpecGuard — AI Implementation Plan

> **Author**: AI Architecture Team  
> **Date**: 2026-07-20  
> **Version**: 1.0  
> **Status**: Proposed — **awaiting confirmation before implementation begins**  
> **Prerequisites**: Reviewed `AI_REPOSITORY_AUDIT.md` and `AI_ARCHITECTURE.md`

---

## Executive Summary

This plan implements the AI architecture described in `AI_ARCHITECTURE.md` in four phases over approximately 4 weeks. Each phase produces a working, testable deliverable. The system will detect compound industrial risks in CDU-100 refinery data using a layered approach: threshold baselines → deterministic compound rules → unsupervised anomaly detection → risk fusion.

**Total estimated files**: ~55 Python modules + ~20 test files + ~10 config files  
**Total estimated lines of code**: ~6,000–8,000 (excluding tests: ~3,000)

---

## Phase 1: Foundation (Estimated: 5–7 days)

### Goal
Generate training data, establish the Python package, implement input adapters, data validation, and plant-state assembly.

---

### 1.1 Generate Baseline Dataset

**Task**: Run the digital twin simulator to produce the complete 130,000-row dataset.

**Commands**:
```bash
cd "digital twin"
pip install -r requirements.txt
python simulate.py --scenario all --format both --split --output ../data/output
```

**Expected output**: 
- `data/output/simulation_data.csv` (~130K rows, ~60 columns)
- `data/output/scada.csv`, `gas.csv`, `workers.csv`, `permits.csv`, `maintenance.csv`, `equipment.csv`, `shift_logs.csv`, `cctv.csv`
- `data/output/simulation_data.jsonl`

**Verification**: Row count = 130,000. All 7 scenarios represented. No empty files.

---

### 1.2 Create Python Package Skeleton

#### [NEW] `specguard_ai/__init__.py`
Package init with version.

#### [NEW] `specguard_ai/version.py`
Version string.

#### [NEW] `specguard_ai/data_types.py`
All shared dataclasses and enums:
- `SCADAReading`, `GasReading`, `EquipmentSnapshot`, `PermitState`
- `MaintenanceState`, `WorkerSnapshot`, `CCTVEvent`, `ShiftLogEntry`
- `ScenarioMetadata`, `DataQualityFlag`, `ValidationResult`
- `ZoneSnapshot`, `PlantSnapshot`, `FeatureVector`

#### [NEW] `pyproject.toml`
Package metadata, dependencies:
- Runtime: `numpy>=1.24`, `pandas>=2.0`, `scikit-learn>=1.3`, `pyyaml>=6.0`
- Dev: `pytest>=7.0`, `pytest-cov`

---

### 1.3 Implement ID Mapping Layer

#### [NEW] `specguard_ai/config/id_mapping.yaml`
Complete bidirectional mapping:
```yaml
zones:
  Zone_A: ZONE_A    # Crude Oil Tank Farm
  Zone_B: ZONE_B    # Feed Preheat & Desalter Area
  Zone_C: ZONE_C    # Fired Heater (Furnace) Area
  Zone_D: ZONE_D    # Distillation Column & Overhead
  Zone_E: ZONE_E    # Control Room & Utilities
  # ZONE_F, ZONE_G: Not modeled in simulator

equipment:
  TK-101: TK-101
  TK-102: TK-102
  PMP-301: P-101A   # Main Feed Pump → Crude Charge Pump A
  PMP-302: P-101B   # Standby Pump → Crude Charge Pump B
  PL-201: PL-002    # Main Feed Pipeline
  PL-202: PL-008    # Product Pipeline → Naphtha line
  VLV-101: XV-001   # Tank Inlet Isolation → Tank outlet isolation
  VLV-201: XV-002   # Pipeline Isolation
  VLV-202: XV-007   # Pipeline Relief → Furnace inlet isolation
  VLV-301: XV-010   # Pump Discharge
  VENT-101: VENT-101
  VENT-301: VENT-201
  VENT-401: VENT-101  # Approx mapping

sensors:
  pipeline_pressure: PT-102
  tank_pressure: PT-101
  pump_outlet_pressure: PT-106
  pipeline_temperature: TT-102
  tank_temperature: TT-101
  pipeline_flow: FT-102
  pump_flow: FT-104
  pump_speed: MC-101   # Approx (motor current ≈ speed)
  pump_power: MC-101
  pump_temperature: TT-104  # Approx
  hc_gas_lel: GD-105
  h2s_ppm: H2S-102
  oxygen_pct: O2-101

workers:
  W001: WRK-001
  W002: WRK-002
  W003: WRK-003
  # ... (12 simulator workers → 20 master model workers)
```

#### [NEW] `specguard_ai/adapters/id_mapper.py`
Load YAML, provide `to_canonical()` and `to_simulator()` methods.

---

### 1.4 Implement Input Adapters

#### [NEW] `specguard_ai/adapters/base.py`
`BaseAdapter` protocol with `parse_row()`, `parse_batch()`, `validate_schema()`.

#### [NEW] `specguard_ai/adapters/scada.py`, `gas.py`, `equipment.py`, `permits.py`, `maintenance.py`, `workers.py`, `cctv.py`, `shift_logs.py`, `scenario.py`
One adapter per data category. Each:
- Parses a CSV row or JSONL dict into a typed dataclass
- Maps IDs to canonical namespace
- Handles missing/null values gracefully

---

### 1.5 Implement Plant-State Assembler

#### [NEW] `specguard_ai/assembler/snapshot.py`
`PlantSnapshot` and `ZoneSnapshot` dataclass definitions (detailed in architecture).

#### [NEW] `specguard_ai/assembler/assembler.py`
- `assemble_from_row(row: dict) -> PlantSnapshot`
- `assemble_from_batch(df: pd.DataFrame) -> list[PlantSnapshot]`
- Distribute fields to zones using sensor-zone mapping
- Aggregate worker counts per zone

---

### 1.6 Implement Data Validation

#### [NEW] `specguard_ai/validation/quality.py`
`DataQualityFlag` enum and `ValidationResult` dataclass.

#### [NEW] `specguard_ai/validation/validators.py`
All 10 validation checks (missing values, duplicates, impossible values, stale readings, etc.).

---

### 1.7 Phase 1 Tests

#### [NEW] `tests/conftest.py`
Shared fixtures: sample rows from each scenario, mock PlantSnapshots.

#### [NEW] `tests/fixtures/`
100-row CSV samples from normal, gas_leak, and explosion_risk scenarios.

#### [NEW] `tests/test_adapters/test_scada.py`, etc.
Unit tests for each adapter.

#### [NEW] `tests/test_assembler/test_assembler.py`
Test snapshot assembly from sample data.

#### [NEW] `tests/test_validation/test_validators.py`
Test each validation check.

### Phase 1 Verification
```bash
pytest tests/ -v --tb=short
# Expected: All tests pass
# Verify: Adapters parse all 130K rows without errors
# Verify: Every PlantSnapshot has at least 1 zone populated
```

---

## Phase 2: Core Risk Engine (Estimated: 5–7 days)

### Goal
Implement feature engineering, threshold baseline, and the deterministic compound-rule engine.

---

### 2.1 Implement Sensor Threshold Configuration

#### [NEW] `specguard_ai/config/sensor_specs.yaml`
Extract all 55 sensor specifications from master asset model Section 5:
```yaml
PT-101:
  sensor_type: pressure
  unit: "kg/cm²g"
  normal_min: 0.3
  normal_max: 0.7
  warning_high: 0.8
  critical_high: 1.0
  sampling_rate_s: 1
# ... (all 55 sensors)
```

---

### 2.2 Implement Feature Engineering Pipeline

#### [NEW] `specguard_ai/features/base.py`
`FeatureVector` dataclass and `FeatureExtractor` protocol.

#### [NEW] `specguard_ai/features/rolling.py`
Rolling mean, std, min, max, median, z-score at 30s/60s/300s/900s windows.

#### [NEW] `specguard_ai/features/derivatives.py`
First derivative, smoothed derivative, second derivative, sign, streak.

#### [NEW] `specguard_ai/features/duration.py`
Time-since features (last alarm, state change, shift start, etc.).

#### [NEW] `specguard_ai/features/cross_sensor.py`
Pressure-flow ratio, temperature-pressure deviation, pump power/flow, vibration×temperature.

#### [NEW] `specguard_ai/features/equipment.py`
Bearing health, seal health, decay rate, failure proximity, standby availability.

#### [NEW] `specguard_ai/features/permits.py`
Permit active flags, permit count, conflict potential, gas test status.

#### [NEW] `specguard_ai/features/maintenance.py`
Active maintenance flag, isolation status, simultaneous count.

#### [NEW] `specguard_ai/features/workers.py`
Worker count, exposure limit fraction, PPE non-compliance, night shift manning.

#### [NEW] `specguard_ai/features/proximity.py`
Hot work near gas, worker near failed equipment, maintenance near active process.

#### [NEW] `specguard_ai/features/data_quality.py`
Missing fraction, stale count, dropout rate.

#### [NEW] `specguard_ai/features/pipeline.py`
`FeaturePipeline` class orchestrating all extractors:
```python
class FeaturePipeline:
    def __init__(self, config: FeatureConfig):
        self.extractors = [
            RollingStatsExtractor(config.windows),
            DerivativeExtractor(),
            DurationExtractor(),
            CrossSensorExtractor(),
            EquipmentExtractor(),
            PermitExtractor(),
            MaintenanceExtractor(),
            WorkerExtractor(),
            ProximityExtractor(),
            DataQualityExtractor(),
        ]
    
    def extract(self, snapshot: PlantSnapshot, history: deque) -> FeatureVector:
        features = {}
        for ext in self.extractors:
            features.update(ext.extract(snapshot, history))
        return FeatureVector(
            zone_id=snapshot.zones[...].zone_id,
            features=features,
        )
```

---

### 2.3 Implement Threshold Baseline (E1)

#### [NEW] `specguard_ai/detection/threshold.py`
- Load sensor specs from YAML
- For each sensor in PlantSnapshot, compare value against warning/critical thresholds
- Return `list[ThresholdAlert]` with sensor ID, alarm level, actual value, threshold

---

### 2.4 Translate and Implement Compound Rules (E2)

#### [NEW] `specguard_ai/config/compound_rules.yaml`
All 35 rules as structured YAML:
```yaml
rules:
  - rule_id: 1
    name: "Hot Work + HC Gas + Wind"
    severity: "Catastrophic"
    hazard_type: "Explosion / Flash Fire"
    applicable_zones: ["ZONE_B", "ZONE_C", "ZONE_D"]
    conditions:
      - field: "permit.hot_work_active"
        operator: "=="
        value: true
      - field: "gas.hc_lel"
        operator: ">"
        value: 10.0
      - field: "environmental.wind_toward_work"
        operator: "=="
        value: true   # Note: wind not available in simulator — mark as optional
    explanation: "Hot work generates ignition sources..."
    optional_conditions: [2]   # Wind condition is optional (data not available)
```

#### [NEW] `specguard_ai/detection/rules/rule_defs.py`
`RuleCondition`, `CompoundRule`, `RuleResult` dataclasses.

#### [NEW] `specguard_ai/detection/rules/rule_loader.py`
Load rules from YAML, instantiate `CompoundRule` objects.

#### [NEW] `specguard_ai/detection/rules/engine.py`
`CompoundRuleEngine`:
- Evaluate all 35 rules against `PlantSnapshot` + `FeatureVector`
- Return `list[RuleResult]` with full/partial match scores
- Deterministic — same input always produces same output

---

### 2.5 Phase 2 Tests

#### [NEW] `tests/test_features/test_rolling.py`, `test_derivatives.py`, etc.
Unit tests for each feature extractor.

#### [NEW] `tests/test_detection/test_threshold.py`
Test threshold detection with known alarm values.

#### [NEW] `tests/test_detection/test_rules.py`
Test each compound rule with synthetic snapshots designed to trigger it.
**Critical**: At least one test per rule (35 tests minimum).

### Phase 2 Verification
```bash
pytest tests/ -v --tb=short
# Run feature pipeline on gas_leak scenario:
python -m specguard_ai.features.pipeline --input data/output/gas_leak/ --output features.csv
# Verify: Feature matrix has ~150 columns, no NaN explosions
# Run rule engine on explosion_risk scenario:
python -m specguard_ai.detection.rules.engine --input data/output/ --scenario explosion_risk
# Verify: Rules 5, 10, 14, 33 (or equivalents) trigger during appropriate phases
```

---

## Phase 3: ML Models & Fusion (Estimated: 5–7 days)

### Goal
Train anomaly detection model, implement risk fusion, implement output generation.

---

### 3.1 Implement Anomaly Detection (E3)

#### [NEW] `specguard_ai/detection/anomaly/isolation_forest.py`
- `AnomalyDetector` class with `fit()`, `score()`, `save()`, `load()`
- Train on normal scenario (100K rows) feature vectors
- Score = 0.0 (normal) to 1.0 (highly anomalous)
- Feature importance via permutation importance

#### [NEW] `specguard_ai/detection/anomaly/explain.py`
Feature attribution for anomaly scores — which features contributed most.

**Training protocol**:
1. Extract features from 100K normal rows → `X_train`
2. Fit `IsolationForest(n_estimators=200, contamination=0.01)`
3. Validate: score distribution on normal data should be low; score on fault scenarios should be high
4. Save model to `models/anomaly_detector.pkl`

---

### 3.2 Implement Supervised Classifier (E4, Optional)

#### [NEW] `specguard_ai/detection/classifier/trainer.py`
- Train gradient-boosted classifier on all 130K rows
- Labels from `LABEL_TO_SEVERITY` mapping
- 5-fold cross-validation with stratified splits by scenario
- Only enable if CV F1 > 0.7

#### [NEW] `specguard_ai/detection/classifier/predictor.py`
- Load trained model, predict risk class and probabilities

---

### 3.3 Implement Risk Fusion (E5)

#### [NEW] `specguard_ai/detection/fusion.py`
`RiskFusion` class implementing weighted-maximum fusion:
- Rules dominate when they fire
- Anomaly supplements
- Data quality penalty
- Score → severity mapping
- Escalation rules

---

### 3.4 Implement Output Generation (Layer F)

#### [NEW] `specguard_ai/output/schema.py`
`RiskAssessment`, `ContributingFactor`, `TriggeredRule`, `Evidence` dataclasses.

#### [NEW] `specguard_ai/output/explanation.py`
Deterministic natural-language explanation from structured evidence.

#### [NEW] `specguard_ai/output/formatter.py`
JSON/dict serialization of `RiskAssessment`.

---

### 3.5 Implement Master Pipeline

#### [NEW] `specguard_ai/pipeline.py`
`RiskPipeline` class:
```python
class RiskPipeline:
    def __init__(self, config_dir: str):
        self.adapters = AdapterRegistry(config_dir)
        self.assembler = PlantStateAssembler(config_dir)
        self.validator = DataValidator()
        self.features = FeaturePipeline(config_dir)
        self.threshold = ThresholdDetector(config_dir)
        self.rules = CompoundRuleEngine(config_dir)
        self.anomaly = AnomalyDetector(config_dir)
        self.classifier = SupervisedClassifier(config_dir)  # Optional
        self.fusion = RiskFusion(config_dir)
        self.output = OutputGenerator()
    
    def process_row(self, row: dict) -> RiskAssessment:
        """Process a single data row → risk assessment."""
        ...
    
    def process_batch(self, csv_dir: str) -> list[RiskAssessment]:
        """Process a batch of CSV files → risk assessments."""
        ...
```

---

### 3.6 Phase 3 Tests

#### [NEW] `tests/test_detection/test_anomaly.py`
- Test: Normal data scores low
- Test: Gas leak data scores high during fault phases
- Test: Explosion risk data scores highest

#### [NEW] `tests/test_detection/test_fusion.py`
- Test: Rules dominate fusion when they fire
- Test: Anomaly escalates when no rules fire
- Test: Missing data increases score
- Test: Score → severity mapping is correct

#### [NEW] `tests/test_pipeline.py`
End-to-end test: CSV file → list[RiskAssessment].

### Phase 3 Verification
```bash
pytest tests/ -v --tb=short
# Run full pipeline on all scenarios:
python -m specguard_ai.pipeline --input data/output/ --output results/
# Verify: Every fault scenario produces risk_score > 50 during critical phases
# Verify: Normal scenario produces risk_score < 20 for > 95% of ticks
```

---

## Phase 4: Evaluation & Hardening (Estimated: 4–5 days)

### Goal
Implement evaluation framework, run all metrics, calibrate thresholds, create documentation.

---

### 4.1 Implement Evaluation Framework (Layer G)

#### [NEW] `specguard_ai/evaluation/metrics.py`
All metrics: FNR, recall, precision, F1, false alarms/hour, detection latency, lead time, scenario detection rate, calibration.

#### [NEW] `specguard_ai/evaluation/evaluator.py`
`ScenarioEvaluator`:
- Run pipeline on each scenario
- Compare output to ground-truth labels
- Compute per-scenario and aggregate metrics

#### [NEW] `specguard_ai/evaluation/ablation.py`
Ablation runner: disable each detection layer, measure impact.

#### [NEW] `specguard_ai/evaluation/calibration.py`
Score calibration: ensure monotonic relationship between score and actual severity.

#### [NEW] `specguard_ai/evaluation/reports.py`
Generate markdown evaluation reports with tables and charts.

---

### 4.2 Run Full Evaluation

Execute evaluation on all 7 scenarios, generate report.

### 4.3 Threshold Tuning

Based on evaluation results:
- Adjust rule condition thresholds if precision is too low
- Adjust anomaly detection contamination parameter
- Adjust fusion weights
- Adjust score-to-severity boundaries

### 4.4 Documentation

#### [NEW] `docs/AI_MODEL_CARD.md`
Model card per detection layer (Isolation Forest, rule engine, classifier if used).

#### [NEW] `docs/AI_EVALUATION_REPORT.md`
Full evaluation results with tables and analysis.

---

## Open Questions for Team

> [!IMPORTANT]
> The following questions need resolution before or during implementation.

1. **Zone ID namespace**: Should we standardize on `ZONE_A` (master model) or `Zone_A` (simulator)? The AI layer will implement a mapping either way, but a team-wide standard avoids long-term drift.

2. **Equipment ID reconciliation**: The simulator has 13 equipment items vs. 27 in the master model. Several compound rules reference equipment not modeled in the simulator (e.g., `C-101`, `H-101`, `E-104`). Should the AI layer:
   - (a) Only evaluate rules for simulated equipment, or
   - (b) Treat unmodeled equipment as "unknown state" and still check partial conditions?

3. **Wind/weather data**: Rules 1, 9, 12, 22, 31 reference wind direction, lightning, and rain. The simulator does not generate weather data. Options:
   - (a) Defer these rules entirely
   - (b) Synthesize weather features from a random model
   - (c) Add weather generation to the simulator (requires digital twin team)

4. **Flat CSV vs. JSONL for training**: The flat CSV loses multi-worker and multi-zone gas data. Recommendation: Use JSONL for full-fidelity training data. Acceptable?

5. **Where should `specguard_ai/` live?** Options:
   - (a) Root of repository: `/specguard_ai/`
   - (b) Under backend: `/backend/specguard_ai/`
   - (c) Separate repository

6. **Model persistence**: Where should trained models (`.pkl` files) be stored?
   - (a) `specguard_ai/models/` (in repo, gitignored)
   - (b) `data/models/`

---

## Assumptions

1. The simulator is correct and stable — no breaking changes expected during AI development.
2. The team approves the proposed package structure before Phase 1 begins.
3. scikit-learn is an acceptable ML dependency.
4. The AI layer will not write to the database or call FastAPI endpoints.
5. Generated simulation data (130K rows) is sufficient for initial model development.
6. The `event_label` ground truth is reliable for evaluation purposes.
7. Risk scores between 0–100 with 6 severity levels is the agreed output format.
8. The AI team has autonomy over `specguard_ai/`, `tests/`, and `docs/AI_*.md`.
9. Evaluation targets: ≥95% recall on Catastrophic hazards, ≤2 false alarms/hour.
10. No production deployment during this phase — this is R&D and validation.

---

## Dependencies

| Dependency | Version | Purpose |
|---|---|---|
| `numpy` | ≥1.24 | Numerical computation |
| `pandas` | ≥2.0 | Data manipulation |
| `scikit-learn` | ≥1.3 | Isolation Forest, StandardScaler, metrics |
| `pyyaml` | ≥6.0 | Configuration loading |
| `pytest` | ≥7.0 | Testing (dev only) |
| `pytest-cov` | ≥4.0 | Coverage (dev only) |

**Explicitly NOT required**: TensorFlow, PyTorch, LangChain, any LLM SDK, FastAPI, SQLAlchemy.

---

## Risk Mitigation

| Risk | Probability | Impact | Mitigation |
|---|---|---|---|
| Simulator data insufficient for ML | Medium | High | Prioritize rule-based detection; augment data by varying random seeds |
| ID mapping errors | Medium | Medium | Comprehensive mapping tests; validate against master model |
| Feature engineering too slow for streaming | Low | High | Profile early; use incremental computation with deque windows |
| Compound rules too noisy (false alarms) | Medium | Medium | Partial-match scoring with tunable thresholds; ablation to identify noisy rules |
| Isolation Forest underfits | Low | Medium | Try LOF as alternative; ensemble if needed |
| Team disagrees on package location | Low | Low | Propose root-level `/specguard_ai/`, adapt if needed |
