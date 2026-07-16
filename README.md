# Digital Twin Petroleum Refinery Simulator

A modular, realistic Digital Twin simulator of a petroleum refinery process unit. This simulator generates continuous, time-series multivariate industrial sensor streams with physically meaningful dependencies between sensors. It is designed specifically to serve as the data source for training and validating AI-powered Industrial Safety Intelligence platforms to detect both simple faults and complex, compound risks.

## Features

- **Realistic Multivariate Dependencies**: Uses statistical properties extracted from the Tennessee Eastman Process (TEP) to ensure that variables (like pump speed, pipeline pressure, and flow rates) are realistically cross-correlated.
- **Diverse Simulation Scenarios**: Simulates normal refinery operations as well as 6 distinct fault scenarios ranging from minor equipment wear to severe compound explosion risks.
- **Granular Event Tracking**: Tracks not just physical sensors (SCADA and Gas), but also worker movements, Permit-to-Work (PTW) statuses, scheduled/reactive maintenance, synthesized CCTV events, and realistic operator shift logs.
- **Flexible Exporting**: Outputs telemetry as a single monolithic JSON Lines (JSONL) stream or as split relational CSV files by data category.

## Project Structure

The repository is organized into a modular architecture:

```text
digital_twin/
├── simulator/
│   ├── config.py              # Global configuration, zone definitions, equipment setup
│   ├── clock.py               # Simulation clock (tick manager)
│   ├── plant.py               # Plant orchestrator coupling all models together
│   │
│   ├── equipment/             # Physical equipment models
│   │   ├── storage_tank.py
│   │   ├── pipeline.py
│   │   ├── pump.py
│   │   ├── valve.py
│   │   └── ventilation.py
│   │
│   ├── sensor_models/         # Sensor generation and noise
│   │   ├── process_model.py   # Core TEP-derived multivariate process model
│   │   ├── scada_sensors.py   # Pressure, temperature, flow, speed SCADA readings
│   │   ├── gas_sensors.py     # HC (LEL), H2S, VOC, and O2 sensors
│   │   └── noise.py           # Gaussian noise, drift, and dropouts
│   │
│   ├── events/                # Human and organizational event models
│   │   ├── worker_events.py   # Worker location, task assignment, PPE tracking
│   │   ├── permit_to_work.py  # PTW lifecycle (Hot Work, Confined Space, etc.)
│   │   ├── maintenance.py     # Maintenance activities and equipment isolation
│   │   ├── shift_logs.py      # Automated shift log generation
│   │   └── cctv_events.py     # Synthesized structured CCTV detections
│   │
│   ├── scenario_engine/       # Fault injection and scenario progression
│   │   ├── base_scenario.py
│   │   ├── normal.py
│   │   ├── gas_leak.py
│   │   ├── ventilation_failure.py
│   │   ├── pump_failure.py
│   │   ├── hot_work_gas_leak.py
│   │   ├── confined_space.py
│   │   └── explosion_risk.py
│   │
│   ├── export/                # Exporters
│   │   ├── csv_exporter.py
│   │   └── json_exporter.py
│   │
│   └── tep/                   # Tennessee Eastman Process references
│       ├── extract_statistics.py
│       └── tep_statistics.json
│
├── simulate.py                # Main CLI entry point
├── requirements.txt           # Project dependencies
└── output/                    # Generated simulation data directory
```

## Available Scenarios

1. **`normal`** (100,000 rows): Normal steady-state operation with natural variability, diurnal cycles, and shift changes.
2. **`gas_leak`** (5,000 rows): Small gas leak developing from pump seal degradation, leading to detection and emergency response.
3. **`ventilation_failure`** (5,000 rows): Fan motor degradation leading to complete failure and gas accumulation.
4. **`pump_failure`** (5,000 rows): Bearing wear progression causing vibration, overheating, seizure, and switchover.
5. **`hot_work_gas_leak`** (5,000 rows): Compound scenario where an undetected leak develops near an active hot work permit.
6. **`confined_space`** (5,000 rows): O2 depletion in a confined space, worker entry without proper gas testing, and rescue.
7. **`explosion_risk`** (5,000 rows): Maximum risk compound scenario featuring a simultaneous pump seal failure, ventilation failure, and active hot work leading to an Emergency Shut Down (ESD).

## Installation

Ensure you have a Python environment (e.g., conda) setup. Install the dependencies:

```bash
pip install -r requirements.txt
```

*(Note: The `numpy`, `pandas`, and `scipy` packages are required.)*

## Usage

Use the `simulate.py` CLI to run simulations. 

### Basic Usage

Run the normal scenario (default 100,000 seconds/rows) and output to CSV:
```bash
python simulate.py --scenario normal
```

Run a specific fault scenario:
```bash
python simulate.py --scenario gas_leak
```

### Advanced Usage

Run all scenarios sequentially to generate the complete 130,000-row dataset, outputting both JSON and split CSV files:
```bash
python simulate.py --scenario all --format both --split --output ./output
```

Override the duration of a scenario (in seconds/ticks):
```bash
python simulate.py --scenario ventilation_failure --duration 7200
```

### Output Formats
- **Combined CSV**: A monolithic `simulation_data.csv` containing all 56+ telemetry columns.
- **Split CSVs (`--split`)**: Separates data into domain-specific files (`scada.csv`, `gas.csv`, `workers.csv`, `permits.csv`, `maintenance.csv`, `equipment.csv`, `shift_logs.csv`, `cctv.csv`). Recommended for building relational databases.
- **JSON Lines (`--format json`)**: A hierarchical `simulation_data.jsonl` where each line is a tick containing nested telemetry categories. Highly recommended for direct ingestion into document databases or stream processing tools.
