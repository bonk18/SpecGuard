import os
import pandas as pd
from datetime import datetime, timezone
from ..domain.plant_state import SensorReading, PermitState, MaintenanceState, WorkerEvent
from ..ingestion.validators import AssetValidator
from ..ingestion.state_assembler import PlantStateAssembler
from ..features.pipeline import StreamingFeaturePipeline
import yaml
from pathlib import Path

def process_scenario(scenario_name: str, in_path: str, out_path: str):
    print(f"Processing {scenario_name}...")
    df = pd.read_csv(in_path)
    
    with open("backend/app/ai/config/feature_config.yaml", "r") as f:
        config = yaml.safe_load(f)
        
    validator = AssetValidator(Path("backend/app/ai/config"))
    
    # Actually, we need to bypass full validation or use pseudo IDs for the simulator data
    # since it uses generic names. We'll map to valid categories.
    assembler = PlantStateAssembler(validator, config)
    pipeline = StreamingFeaturePipeline(config, validator)
    
    records = []
    
    for i, row in df.iterrows():
        try:
            ts = pd.to_datetime(row["timestamp"]).to_pydatetime()
            
            # Map flat row to domain events
            gas_zone = row.get("gas_zone_id", "ZONE_C")
            if pd.isna(gas_zone): gas_zone = "ZONE_C"
            gas_zone = str(gas_zone).upper()
            
            worker_zone = row.get("worker_zone", "ZONE_E")
            if pd.isna(worker_zone): worker_zone = "ZONE_E"
            worker_zone = str(worker_zone).upper()
            
            events = []
            
            if pd.notna(row.get("hc_gas_lel")):
                events.append(SensorReading(timestamp=ts, source_id="GD-SIM", zone_id=gas_zone, category="hydrocarbon", value=float(row["hc_gas_lel"]), unit="%"))
                
            if pd.notna(row.get("h2s_ppm")):
                events.append(SensorReading(timestamp=ts, source_id="H2S-SIM", zone_id=gas_zone, category="h2s", value=float(row["h2s_ppm"]), unit="ppm"))
                
            if pd.notna(row.get("oxygen_pct")):
                events.append(SensorReading(timestamp=ts, source_id="O2-SIM", zone_id=gas_zone, category="oxygen", value=float(row["oxygen_pct"]), unit="%"))
                
            if pd.notna(row.get("pipeline_pressure")):
                events.append(SensorReading(timestamp=ts, source_id="PT-SIM", zone_id="ZONE_A", category="pressure", value=float(row["pipeline_pressure"]), unit="bar"))
                
            if pd.notna(row.get("pipeline_temperature")):
                events.append(SensorReading(timestamp=ts, source_id="TT-SIM", zone_id="ZONE_A", category="temperature", value=float(row["pipeline_temperature"]), unit="c"))

            if pd.notna(row.get("bearing_wear")):
                events.append(SensorReading(timestamp=ts, source_id="VIB-SIM", zone_id="ZONE_A", category="vibration", value=float(row["bearing_wear"]), unit="mm"))

            if pd.notna(row.get("ventilation_status")):
                events.append(SensorReading(timestamp=ts, source_id="VENT-SIM", zone_id=gas_zone, category="ventilation_health", value=float(row["ventilation_status"]), unit="pct"))
            
            if row.get("hot_work_active") == True:
                events.append(PermitState(timestamp=ts, source_id="HW-SIM", zone_id=gas_zone, permit_type="HOT_WORK", status="ACTIVE", active=True))
                
            if row.get("confined_space_active") == True:
                events.append(PermitState(timestamp=ts, source_id="CS-SIM", zone_id=gas_zone, permit_type="CONFINED_SPACE", status="ACTIVE", active=True))
                
            if row.get("line_breaking_active") == True:
                events.append(PermitState(timestamp=ts, source_id="LB-SIM", zone_id="ZONE_A", permit_type="LINE_BREAKING", status="ACTIVE", active=True))
                
            if row.get("maintenance_required") == True:
                events.append(MaintenanceState(timestamp=ts, source_id="MAINT-SIM", zone_id="ZONE_A", task_id="TASK-SIM", status="ACTIVE", active=True))
            
            if pd.notna(row.get("worker_id")):
                events.append(WorkerEvent(timestamp=ts, source_id="W-SIM", zone_id=worker_zone, worker_id=str(row["worker_id"]), action="ENTER"))
                
            # Process events
            for event in events:
                assembler.process_event(event)
                
            snapshot = assembler.build_snapshot(ts)
            zone_results = pipeline.update(snapshot)
            
            # Since simulator primarily simulates one active zone event at a time, we will record all active zones
            for zid, feature_vector in zone_results.items():
                record = {
                    "timestamp": feature_vector.timestamp.isoformat(),
                    "zone_id": zid,
                    "scenario_id": scenario_name,
                    "label": 1 if row.get("event_label", "normal") != "normal" else 0
                }
                
                for k, v in feature_vector.features.items():
                    record[k] = v.value
                    
                records.append(record)
                
        except Exception as e:
            print(f"Error on row {i}: {e}")
            
    if records:
        out_df = pd.DataFrame(records)
        out_df.to_parquet(out_path)
        print(f"Saved {len(out_df)} rows to {out_path}")
    else:
        print(f"No records extracted for {scenario_name}")

def main():
    base_dir = "data/raw"
    out_dir = "data/processed"
    os.makedirs(out_dir, exist_ok=True)
    
    for scenario in os.listdir(base_dir):
        scenario_dir = os.path.join(base_dir, scenario)
        if not os.path.isdir(scenario_dir):
            continue
            
        in_path = os.path.join(scenario_dir, "simulation_data.csv")
        if not os.path.exists(in_path):
            continue
            
        out_path = os.path.join(out_dir, f"{scenario}_features.parquet")
        process_scenario(scenario, in_path, out_path)

if __name__ == "__main__":
    main()
