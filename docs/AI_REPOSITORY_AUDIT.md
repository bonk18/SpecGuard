# SpecGuard — AI Repository Audit

> **Author**: AI Architecture Team  
> **Date**: 2026-07-20  
> **Scope**: Full repository audit prior to AI layer implementation  
> **Status**: Complete — awaiting team review

---

## 1. Current Repository Structure

```
SpecGuard/
├── .gitignore
├── LICENSE
├── README.md                          # Informal project notes (not documentation)
├── requirements.txt                   # Backend: FastAPI, Pydantic, SQLAlchemy, Uvicorn
│
├── docs/
│   ├── master_asset_model.md          # ★ Primary domain model (1,045 lines, 81 KB)
│   └── .gitkeep
│
├── digital twin/                      # ★ Complete simulator — Python package
│   ├── README.md                      # Excellent documentation
│   ├── requirements.txt               # numpy, pandas, scipy
│   ├── simulate.py                    # CLI entry point
│   └── simulator/
│       ├── __init__.py
│       ├── clock.py                   # Simulation clock with shift tracking
│       ├── config.py                  # Zones, equipment, sensors, workers, enums
│       ├── plant.py                   # Master orchestrator — 396 lines
│       ├── equipment/                 # 5 equipment types (base, pump, pipeline, valve, ventilation, tank)
│       ├── sensor_models/             # TEP-derived process model, SCADA sensors, gas sensors, noise
│       ├── events/                    # Worker, PTW, maintenance, shift logs, CCTV
│       ├── scenario_engine/           # 7 scenarios (normal + 6 fault/compound)
│       ├── export/                    # CSV and JSONL exporters
│       └── tep/                       # TEP statistics (52 KB JSON) + extraction script
│
├── backend/                           # FastAPI skeleton (stub phase)
│   └── app/
│       ├── main.py                    # FastAPI app with 7 routers
│       ├── api/                       # 7 route stubs (all return "Coming Soon")
│       ├── schemas/                   # 6 Pydantic schemas (minimal, 10-19 lines each)
│       ├── models/                    # Empty (only __init__.py)
│       ├── services/                  # Empty
│       ├── core/                      # Empty
│       ├── database/                  # SQLite config
│       └── utils/                     # Empty
│
├── data/
│   └── .gitkeep                       # Empty — no generated data committed
│
└── frontend/
    └── .gitkeep                       # Empty — not started
```

### Key Observation

The repository has **two fully developed components** (master asset model + digital twin simulator) and **one skeleton** (FastAPI backend). There is **no existing AI/ML code** anywhere in the repository.

---

## 2. Existing Data Sources

### 2.1 Digital Twin Simulator Output

The simulator generates **56+ columns** per tick at **1-second resolution** across 8 categories:

| Category | Columns | Source Module |
|---|---|---|
| SCADA sensors | 14 process variables + alarms | `scada_sensors.py` via `process_model.py` |
| Gas sensors | 4 gas readings + 4 alarms + zone ID | `gas_sensors.py` |
| Equipment state | 6 aggregate flags (pump/valve/vent status, bearing wear) | `plant.py` aggregation |
| Worker events | 5 fields (ID, zone, task, PPE, time-in-zone) | `worker_events.py` |
| Permit state | 4 boolean flags (hot_work, confined_space, electrical, line_breaking) | `permit_to_work.py` |
| Maintenance | 4 fields (equipment, isolation, technician, remaining) | `maintenance.py` |
| Shift logs | 3 fields (severity, message, operator) | `shift_logs.py` |
| CCTV events | 5 fields (camera, zone, event_type, description, confidence) | `cctv_events.py` |

### 2.2 TEP Statistical Foundation

The process model uses **16 process variables** extracted from the Tennessee Eastman Process dataset:

- `hydrocarbon_flow`, `pipeline_flow`, `pipeline_pressure`, `tank_level`
- `pipeline_temperature`, `tank_temperature`, `separator_level`, `tank_pressure`
- `pump_outlet_pressure`, `pump_flow`, `pump_temperature`, `pump_power`
- `isolation_valve`, `relief_valve`, `steam_valve`, `pump_speed`

Statistics include: means, standard deviations, min/max, autocorrelation lag-1/lag-2, full covariance matrix, correlation matrix, and **20+ fault signatures** with mean shifts and variance ratios.

### 2.3 Export Formats

| Format | File | Description |
|---|---|---|
| Combined CSV | `simulation_data.csv` | All columns, one row per second |
| Split CSVs | `scada.csv`, `gas.csv`, `workers.csv`, `permits.csv`, `maintenance.csv`, `equipment.csv`, `shift_logs.csv`, `cctv.csv` | Domain-specific splits |
| JSONL | `simulation_data.jsonl` | Hierarchical, one JSON object per tick |

### 2.4 No Existing Generated Data

The `data/` directory is empty. Data must be generated using `python simulate.py`.

---

## 3. Existing Sensor and Operational Schemas

### 3.1 Master Asset Model JSON Schemas (Section 15)

The master asset model defines **9 JSON schemas** in embedded code blocks:

| Schema | Key Fields | Validation |
|---|---|---|
| `zones.json` | zone_id, hazard_level, hazard_rating, max_workers, is_confined | Pattern: `^ZONE_[A-Z]$` |
| `equipment.json` | equipment_id, equipment_type (12 enum values), zone_id, criticality, operating_state (6 enum values) | References valid zones |
| `sensors.json` | sensor_id, sensor_type (12 enum values), equipment_id, zone_id, normal_range, thresholds | Per-sensor thresholds |
| `pipelines.json` | pipeline_id, source/dest equipment, fluid, operating conditions | Pattern: `^PL-\d{3}$` |
| `workers.json` | worker_id, role_id, shift, certifications, risk_exposure | Pattern: `^WRK-\d{3}$` |
| `permits.json` | permit_type_id, applicable_zones, required_isolation, required_ppe | Pattern: `^PTW-[A-Z]{2}$` |
| `maintenance.json` | maintenance_id, equipment_id, maintenance_type, risk_level | References valid equipment/permits |
| `cameras.json` | camera_id, zone_id, coverage_type (6 types), detection capabilities | Pattern: `^CAM-\d{3}$` |
| `emergency_assets.json` | emergency_asset_id, asset_type (12 types), zone_coverage, triggers | Pattern: `^EM-[A-Z]+-\d{3}$` |

### 3.2 Backend Pydantic Schemas

| Schema | File | Fields | Quality |
|---|---|---|---|
| `SensorReading` | `sensor.py` | sensor_id, zone_id, gas_level, temperature, pressure, ventilation_status, equipment_status, timestamp | **Minimal** — collapses all sensor types into one |
| `Permit` | `permit.py` | permit_id, permit_type, zone_id, issued_to, status, start_time, end_time | **Incomplete** — missing gas_test, isolation, holder |
| `RiskAlert` | `alert.py` | alert_id, zone_id, risk_score, severity, predicted_incident, contributing_signals, timestamp | **Reasonable** — usable as AI output target |
| `CCTVEvent` | `cctv.py` | event_id, camera_id, zone_id, workers_detected, ppe_compliance, timestamp | **Minimal** — missing event_type, confidence, description |
| `MaintenanceEvent` | `maintainance.py` | maintenance_id, equipment_id, equipment_name, zone_id, maintenance_type, status, assigned_team, timestamp | **Reasonable** but filename has typo |
| `Intervention` | `intervention.py` | intervention_id, alert_id, recommended_actions, priority, status, generated_at | **Stub** — would need enrichment |

### 3.3 Simulator Config Enums/Dataclasses

| Class | Key Attributes | Used By |
|---|---|---|
| `ZoneID` | 5 zones (Zone_A–Zone_E) | All modules |
| `EquipmentType` | 5 types | Equipment factory |
| `EquipmentState` | 5 states | Equipment models |
| `PermitType` | 4 types | PTW manager |
| `PermitStatus` | 5 states | PTW lifecycle |
| `ScenarioID` | 7 scenarios | Scenario engine |
| `Shift` | DAY/NIGHT | Clock, workers |
| `SensorSpec` | nominal, std, alarms, noise_std | SCADA/gas sensors |

---

## 4. Existing Scenario System

### 4.1 Scenario Architecture

```
BaseScenario (ABC)
  ├── ScenarioPhase (dataclass: name, start_tick, duration, description, label)
  ├── apply(tick, plant) — abstract
  ├── get_current_phase(tick) → ScenarioPhase
  ├── get_label(tick) → str              ★ Ground-truth label per tick
  ├── ramp(tick, start, duration, start_val, end_val)
  └── sigmoid_ramp(tick, start, duration, start_val, end_val)
```

### 4.2 Available Scenarios

| # | Scenario ID | Duration | Phases | Fault Injection | Ground Truth Labels |
|---|---|---|---|---|---|
| 1 | `normal` | 100,000s | 1 | None | `normal` |
| 2 | `gas_leak` | 5,000s | 7 | TEP Fault 2 | `normal → seal_degradation → leak_onset → leak_detected → leak_confirmed → emergency_isolation → leak_secured` |
| 3 | `ventilation_failure` | 5,000s | 7 | TEP Fault 6 | `normal → fan_degradation → performance_loss → failure → gas_accumulation → emergency_ventilation → recovery` |
| 4 | `pump_failure` | 5,000s | 7 | TEP Fault 2 | `normal → early_wear → advanced_wear → critical_vibration → failure → switchover → stabilized` |
| 5 | `hot_work_gas_leak` | 5,000s | 7 | TEP Fault 5 | `normal_hot_work → hot_work_leak_onset → hot_work_gas_rising → hot_work_gas_detected → hot_work_suspended → hot_work_emergency → hot_work_resolved` |
| 6 | `confined_space` | 5,000s | 7 | TEP Faults 7+14 | `normal → confined_space_permit → confined_space_o2_dropping → confined_space_entry → confined_space_exposure → confined_space_rescue → confined_space_aftermath` |
| 7 | `explosion_risk` | 5,000s | 9 | TEP Faults 2+4+6 | `normal → compound_onset → compound_pump_leak → compound_vent_failure → compound_explosive_range → compound_maximum_risk → compound_esd → compound_emergency → compound_stabilizing` |

### 4.3 Ground-Truth Label System

Each tick carries an `event_label` field set by `BaseScenario.get_label(tick)`. This provides **tick-level ground truth** for supervised training.

**Total labeled data**: 130,000 rows (100K normal + 30K fault) when running all scenarios.

---

## 5. Existing Risk Rules

### 5.1 Compound Risk Matrix (35 Rules)

The master asset model defines **35 compound risk rules** in Section 13. These are currently **documentation only** — they are NOT implemented as executable code.

**Severity Distribution**:

| Severity | Count | Rule Numbers |
|---|---|---|
| Catastrophic | 17 | 1, 2, 4, 5, 7, 9, 10, 14, 16, 20, 21, 22, 25, 27, 32 (+ 2 more) |
| Critical | 2 | 3, 16 |
| High | 14 | 6, 8, 11, 15, 17, 18, 19, 23, 26, 28, 29, 30, 33, 35 |
| Medium | 2 | 24, 31 |

**Condition Types Referenced**:

- Sensor thresholds: PT, TT, FT, GD, H2S, O2, VB, MC, LT, FD, SD, ZT
- Permit states: PTW-HW, PTW-CS, PTW-EI, PTW-LB, PTW-WH
- Equipment states: pump running/failed, ventilation failed, valve position
- Maintenance states: active maintenance, LOTO status, isolation
- Worker states: zone presence, PPE compliance, fatigue, gas monitor
- Environmental: wind direction, lightning, rain/flooding, shift timing
- Organizational: night shift manning, alarm flood, shift handover, SIMOPS

### 5.2 Programmatic Risk Detection in Simulator

The simulator has **limited inline risk detection**:

1. **PTW Manager** (`permit_to_work.py` L144-159): Hot work + HC > 5% LEL → auto-suspend permit
2. **Gas Sensors** (`gas_sensors.py`): HC/H2S/VOC/O2 alarm evaluation (NORMAL/HIGH/HIHI/LOW)
3. **SCADA Sensors** (`scada_sensors.py`): Per-variable alarm evaluation (NORMAL/HIGH/HIHI/LOW)
4. **Plant** (`plant.py` L278-287): Emergency zone detection (HC > 20% LEL, O2 < 19%, H2S > 10 ppm)

**None of the 35 compound rules from the master asset model are implemented as executable detection logic.**

---

## 6. Available Ground-Truth Labels

| Source | Label Field | Values | Coverage |
|---|---|---|---|
| Scenario engine | `event_label` | ~40 unique phase labels | Every tick |
| Scenario engine | `scenario_id` | 7 scenario IDs | Every tick |
| SCADA alarms | `{sensor}_alarm` | NORMAL / HIGH / HIHI / LOW | Every tick |
| Gas alarms | `{gas}_alarm` | NORMAL / HIGH / HIHI / LOW | Every tick |
| Equipment state | `pump_failed`, `valve_failed`, `ventilation_failed` | Boolean | Every tick |
| PTW conflict | `permit_conflict` event | Event-driven (sparse) | PTW manager events only |
| CCTV events | `event_type` | 11 event types | Event-driven |
| Shift logs | `severity` | INFO / WARNING / CRITICAL | Every ~300s |

### Key Observation on Labels

The `event_label` field is the **primary ground truth** for risk detection. It transitions through phases, enabling:
- Binary classification: normal vs. abnormal
- Multi-class classification: specific fault type
- Severity regression: phase progression → increasing risk
- Anomaly detection: normal baseline vs. deviation

**Missing**: There is no explicit `risk_score` ground truth. Risk scores must be derived from scenario phase, sensor values, and domain rules.

---

## 7. Missing Fields Required for Risk Modelling

### 7.1 Critical Gaps in Simulator Output

| Missing Field | Why Needed | Impact on AI |
|---|---|---|
| **Per-sensor zone mapping** | Simulator outputs aggregate values without sensor IDs from master model (e.g., `pipeline_pressure` not `PT-101`) | Cannot map to master model sensor thresholds |
| **Wind direction/speed** | 4 of 35 compound rules reference wind | Cannot evaluate rules 1, 9, 12, 22 |
| **Weather conditions** | Rules 22, 31 reference lightning, rain/flooding | Cannot evaluate weather-compound risks |
| **Worker count per zone** | Rules 6, 19 reference overcrowding | Available via worker_events but not aggregated per zone per tick |
| **Worker gas monitor status** | Rule 15 references personal gas monitor | PPE items tracked but not specifically "gas_monitor present" |
| **LOTO verification status** | Rules 3, 7, 11 reference LOTO state | Maintenance isolation tracked but not LOTO specifically |
| **Multiple zone gas readings per tick** | Only primary zone (Zone_C) gas readings in flat CSV | Other zone gas readings computed but not exported in flat row |
| **Fire water system pressure** | Rule 13 references ring main pressure | Not tracked in simulator |
| **Alarm count / alarm flood** | Rule 6 references 5+ simultaneous alarms | Active alarms available but count not in output row |
| **Scaffold/access blocking** | Rule 28 references blocked emergency access | Not modeled |
| **Crude type switch** | Rule 27 references crude type change | Not modeled |
| **UPS/power state** | Rule 23 references power failure | Not modeled |

### 7.2 Schema Gaps in Backend

| Gap | Current State | Required |
|---|---|---|
| `SensorReading` schema | Collapses all sensor types to single record | Per-sensor-type readings matching simulator output |
| No `RiskAssessment` schema | Missing | AI output schema with score, contributing factors, evidence |
| No `PlantSnapshot` schema | Missing | Unified zone-time snapshot for AI consumption |
| No `FeatureVector` schema | Missing | Engineered feature set for model input |

---

## 8. Schema Inconsistencies

### 8.1 Zone ID Mismatch ⚠️ CRITICAL

| Component | Zone IDs Used | Pattern |
|---|---|---|
| Master Asset Model | `ZONE_A` through `ZONE_G` | `ZONE_{letter}` (7 zones) |
| Simulator `config.py` | `Zone_A` through `Zone_E` | `Zone_{letter}` (5 zones) |
| Simulator Zone Names | Storage Tank, Pipeline Network, Pump Station, Maintenance Workshop, Control Room | Simplified |
| Master Model Zone Names | Crude Oil Tank Farm, Feed Preheat & Desalter, Fired Heater, Distillation Column, Product Pumps, Control Room, Pipe Rack | CDU-specific |

**Impact**: The simulator models a **generic petroleum facility** with 5 zones, while the master asset model describes a **specific CDU-100 atmospheric distillation unit** with 7 zones. Zone IDs use different casing (`ZONE_A` vs `Zone_A`).

### 8.2 Equipment ID Mismatch ⚠️ CRITICAL

| Component | Equipment IDs | Count |
|---|---|---|
| Master Asset Model | `TK-101`, `P-101A`, `E-101`, `H-101`, `C-101`, etc. | 27 equipment items |
| Simulator | `TK-101`, `TK-102`, `PMP-301`, `PMP-302`, `PL-201`, `VLV-xxx`, `VENT-xxx` | 13 equipment items |

The simulator uses **different equipment IDs** (e.g., `PMP-301` instead of `P-101A`). Only `TK-101` and `TK-102` match.

### 8.3 Worker ID Mismatch

| Component | Worker IDs | Count |
|---|---|---|
| Master Asset Model | `WRK-001` through `WRK-020` | 20 workers |
| Simulator | `W001` through `W012` | 12 workers |

### 8.4 Camera ID Mismatch

| Component | Camera IDs |
|---|---|
| Master Asset Model | `CAM-101` through `CAM-111` |
| Simulator CCTV | `CAM-A01`, `CAM-B01`, `CAM-C01`, etc. |

### 8.5 Permit Type Mismatch

| Component | Permit Types |
|---|---|
| Master Asset Model | `PTW-HW`, `PTW-CS`, `PTW-EI`, `PTW-LB`, `PTW-WH`, `PTW-EX` (6 types) |
| Simulator | `hot_work`, `confined_space`, `electrical`, `line_breaking` (4 types) |

Missing in simulator: Working at Height (`PTW-WH`), Excavation (`PTW-EX`).

### 8.6 Sensor Coverage Gap

| Domain | Master Model Sensors | Simulator Sensors |
|---|---|---|
| Pressure | 13 (PT-101 to PT-113) | 3 aggregate (pipeline, tank, pump) |
| Temperature | 8 (TT-101 to TT-108) | 3 aggregate (pipeline, tank, pump) |
| Flow | 9 (FT-101 to FT-109) | 3 aggregate (pipeline, HC, pump) |
| Gas/HC | 7 (GD-101 to GD-107) | 1 aggregate per zone |
| H2S | 3 (H2S-101 to H2S-103) | 1 aggregate per zone |
| Vibration | 3 (VB-101 to VB-103) | Pump vibration only |
| Motor Current | 3 (MC-101 to MC-103) | Not directly exported |
| Level | 3 (LT-101 to LT-103) | Not exported |
| Flame | 2 (FD-101, FD-102) | Not modeled |
| Smoke | 1 (SD-101) | Not modeled |
| Valve Position | 2 (ZT-101, ZT-102) | Aggregate only |
| Oxygen | 1 (O2-101) | Per-zone aggregate |

### 8.7 Backend Schema Typo

File `maintainance.py` should be `maintenance.py` (misspelling).

---

## 9. Components That Should Be Reused

| Component | Path | Reuse Strategy |
|---|---|---|
| TEP Process Model | `simulator/sensor_models/process_model.py` | Use directly for data generation; the AR(1) with multivariate correlation is excellent |
| TEP Statistics | `simulator/tep/tep_statistics.json` | Reference for baseline means, stds, fault signatures |
| Scenario Engine | `simulator/scenario_engine/` | Use all 7 scenarios for generating training/validation data |
| BaseScenario phases | `scenario_engine/base_scenario.py` | Reuse `ScenarioPhase` and ramp functions for ground truth labeling |
| Gas Sensor Physics | `simulator/sensor_models/gas_sensors.py` | Zone-based concentration model with ventilation coupling |
| Equipment Models | `simulator/equipment/` | Bearing/seal degradation curves for feature engineering baselines |
| Noise Model | `simulator/sensor_models/noise.py` | Drift, dropout, and spike artifacts for data quality features |
| Master Asset Model | `docs/master_asset_model.md` | The 35 compound rules are the specification for the rule engine |
| SensorSpec | `simulator/config.py` | Alarm thresholds for threshold-based risk layer |
| CSV/JSONL Exporters | `simulator/export/` | Use for generating training datasets |
| RiskAlert Schema | `backend/app/schemas/alert.py` | Starting point for AI output schema |
| Simulation Clock | `simulator/clock.py` | Shift tracking and diurnal cycle |

---

## 10. Components That Should NOT Be Modified

| Component | Reason |
|---|---|
| `simulator/` (entire package) | Owned by digital twin team; AI layer consumes output only |
| `backend/app/api/` | Owned by FastAPI team |
| `backend/app/database/` | Owned by database team |
| `backend/app/main.py` | FastAPI entry point — not our concern |
| `frontend/` | Owned by frontend team |
| `docs/master_asset_model.md` | Reference document; propose amendments via team review only |

**Exception**: If a simulator defect prevents AI data consumption, propose a minimal fix as a PR with the digital twin team.

---

## 11. Risks That Could Block AI Development

### 11.1 Critical Blockers

| # | Risk | Severity | Mitigation |
|---|---|---|---|
| 1 | **Zone ID mismatch** between master model and simulator prevents mapping 35 compound rules to simulator data | **CRITICAL** | AI layer must implement a mapping table: `Zone_A ↔ ZONE_A`, etc. Recommend proposing a canonical ID namespace to the team. |
| 2 | **Equipment ID mismatch** prevents linking sensor readings to specific equipment in compound rules | **CRITICAL** | AI layer must implement equipment ID mapping table. Some rules reference equipment not modeled in the simulator. |
| 3 | **No generated dataset exists** — cannot begin model development until data is produced | **HIGH** | First implementation step must be running `simulate.py --scenario all --format both --split` |
| 4 | **Simulator exports only Zone_C gas readings** in flat CSV row; compound rules need multi-zone gas data | **HIGH** | Use JSONL format (hierarchical) or use split CSV mode; alternatively extract from `gas_sensors._zone_hc` in a custom adapter |
| 5 | **35 compound rules are prose only** — no executable specification | **HIGH** | Must be translated into structured rule definitions (conditions + thresholds + severity) |

### 11.2 Significant Risks

| # | Risk | Severity | Mitigation |
|---|---|---|---|
| 6 | Only 130K rows of training data (30K fault); some ML models need more | **MEDIUM** | Use data augmentation; prioritize rule-based and unsupervised methods |
| 7 | Scenarios run sequentially with `plant.reset()` between them — no mixed-scenario data | **MEDIUM** | Train separate models per scenario or implement scenario mixing |
| 8 | No weather, wind, or environmental data in simulator | **MEDIUM** | Synthesize environmental features or defer weather-dependent rules |
| 9 | Flat CSV row loses multi-worker data (only first worker exported) | **MEDIUM** | Use JSONL for full worker list, or build zone-level worker aggregations |
| 10 | No existing tests anywhere in the repository | **MEDIUM** | AI package must be built with comprehensive tests from day one |
| 11 | TEP fault signatures may not perfectly map to CDU-100 process behavior | **LOW** | Accept as approximation; document deviation in model cards |

---

## 12. Recommended Implementation Order

### Phase 1: Foundation (Week 1)

1. **Generate baseline dataset** — Run simulator for all 7 scenarios
2. **Create ID mapping layer** — Zone, equipment, sensor, worker ID reconciliation
3. **Define AI package structure** — `specguard_ai/` with clear module boundaries
4. **Implement input adapters** — Parse CSV/JSONL into typed dataclasses
5. **Implement data validation** — Missing values, impossible readings, stale timestamps

### Phase 2: Core Risk Engine (Week 2)

6. **Translate 35 compound rules** into structured rule definitions
7. **Implement threshold-based baseline** — Single-sensor alarm monitoring
8. **Implement deterministic compound-rule engine** — Evaluate all 35 rules
9. **Implement plant-state assembler** — Unified zone-time snapshots
10. **Implement feature engineering** — Rolling stats, rate-of-change, cross-sensor features

### Phase 3: ML Models (Week 3)

11. **Train unsupervised anomaly detector** — Isolation Forest on feature vectors
12. **Implement risk-fusion layer** — Combine rules + anomaly scores
13. **Implement risk-scoring algorithm** — 0-100 score with severity mapping
14. **Implement output generation** — Full risk assessment with explanation

### Phase 4: Evaluation & Hardening (Week 4)

15. **Implement evaluation framework** — All specified metrics
16. **Run scenario-level evaluations** — Detection rate, latency, false alarms
17. **Calibration and threshold tuning** — Align scores with domain severity
18. **Create model cards and documentation**
19. **Optional**: Supervised classifier if label quality supports it

---

## Appendix A: File-by-File Inventory

| File | Lines | Bytes | Purpose |
|---|---|---|---|
| `docs/master_asset_model.md` | 1,045 | 81,469 | Complete domain model |
| `digital twin/simulate.py` | 203 | 7,267 | CLI entry point |
| `digital twin/simulator/config.py` | 371 | 15,708 | All configuration |
| `digital twin/simulator/plant.py` | 396 | 16,263 | Master orchestrator |
| `digital twin/simulator/clock.py` | 70 | 2,258 | Time management |
| `digital twin/simulator/equipment/base.py` | 104 | 3,799 | Equipment ABC |
| `digital twin/simulator/equipment/pump.py` | 137 | 5,206 | Pump model |
| `digital twin/simulator/equipment/pipeline.py` | ~80 | 2,957 | Pipeline model |
| `digital twin/simulator/equipment/valve.py` | ~85 | 3,037 | Valve model |
| `digital twin/simulator/equipment/ventilation.py` | ~90 | 3,185 | Ventilation model |
| `digital twin/simulator/equipment/storage_tank.py` | ~85 | 2,934 | Tank model |
| `digital twin/simulator/sensor_models/process_model.py` | 190 | 7,736 | TEP multivariate model |
| `digital twin/simulator/sensor_models/scada_sensors.py` | 118 | 4,054 | SCADA readings |
| `digital twin/simulator/sensor_models/gas_sensors.py` | 158 | 6,557 | Gas detection |
| `digital twin/simulator/sensor_models/noise.py` | 65 | 2,214 | Noise generation |
| `digital twin/simulator/events/worker_events.py` | 232 | 9,447 | Worker tracking |
| `digital twin/simulator/events/permit_to_work.py` | 208 | 8,196 | PTW lifecycle |
| `digital twin/simulator/events/maintenance.py` | 191 | 7,069 | Maintenance mgmt |
| `digital twin/simulator/events/shift_logs.py` | 185 | 8,338 | Log generation |
| `digital twin/simulator/events/cctv_events.py` | 171 | 7,717 | CCTV events |
| `digital twin/simulator/scenario_engine/base_scenario.py` | 105 | 3,698 | Scenario ABC |
| `digital twin/simulator/scenario_engine/normal.py` | ~25 | 967 | Normal scenario |
| `digital twin/simulator/scenario_engine/gas_leak.py` | ~130 | 4,943 | Gas leak |
| `digital twin/simulator/scenario_engine/ventilation_failure.py` | ~110 | 4,116 | Vent failure |
| `digital twin/simulator/scenario_engine/pump_failure.py` | ~130 | 4,973 | Pump failure |
| `digital twin/simulator/scenario_engine/hot_work_gas_leak.py` | 136 | 6,181 | Compound: hot work + gas |
| `digital twin/simulator/scenario_engine/confined_space.py` | 116 | 5,212 | Confined space |
| `digital twin/simulator/scenario_engine/explosion_risk.py` | 214 | 9,966 | Compound: max risk |
| `digital twin/simulator/export/csv_exporter.py` | 114 | 4,861 | CSV export |
| `digital twin/simulator/export/json_exporter.py` | ~120 | 4,347 | JSONL export |
| `digital twin/simulator/tep/tep_statistics.json` | 1,535 | 52,597 | TEP reference data |
| `digital twin/simulator/tep/extract_statistics.py` | ~200 | 8,791 | TEP extraction |
| `backend/app/main.py` | 28 | 899 | FastAPI app |
| `backend/app/schemas/*.py` | ~100 total | ~1,500 | 6 Pydantic schemas |
| `backend/app/api/*.py` | ~84 total | ~1,300 | 7 route stubs |

---

## Appendix B: Assumptions

1. The digital twin simulator is correct and will not be modified by the AI team.
2. The master asset model is the authoritative domain specification.
3. Generated simulation data is the primary (and initially only) data source.
4. The AI layer will run as a standalone Python package, independent of FastAPI.
5. The 35 compound rules are mandatory detection targets.
6. No real SCADA, CCTV, or IoT data is available — only simulated data.
7. The AI layer should be designed to handle both batch CSV and streaming JSONL.
8. The team will agree on a canonical ID namespace to resolve mismatches.
9. Environmental/weather features referenced by some compound rules will be synthesized or deferred.
10. The AI layer will not include deep learning unless simpler methods fail to achieve acceptable detection rates.
