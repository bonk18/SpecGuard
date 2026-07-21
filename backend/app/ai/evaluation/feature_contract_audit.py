import os
import sys
import json
import yaml

# Add the project root to sys.path so we can import the backend module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../..')))

from backend.app.ai.features.registry import registry
from backend.app.ai.features.extractors.extractors import (
    RawExtractor, RollingExtractor, TrendExtractor, 
    CrossSensorExtractor, EquipmentExtractor, PermitExtractor, DataQualityExtractor,
    GeospatialExtractor, MaintenanceExtractor
)
from backend.app.ai.ingestion.validators import AssetValidator

def main():
    # 1. Parse Risk Rules
    with open("backend/app/ai/config/risk_rules.yaml", "r") as f:
        rule_config = yaml.safe_load(f)
    
    rules = rule_config.get("rules", [])
    rule_features = set()
    invalid_rule_references = []
    
    for r in rules:
        if not r.get("enabled", True):
            continue
            
        conds = r.get("conditions", {}).get("all", []) + r.get("conditions", {}).get("any", [])
        for c in conds:
            if "feature" in c:
                rule_features.add(c["feature"])
                if not isinstance(c["feature"], str):
                    invalid_rule_references.append(c)
                    
        for esc in r.get("escalation", []):
            if "when" in esc and "feature" in esc["when"]:
                rule_features.add(esc["when"]["feature"])

    # 2. Parse Extractors
    # Extractors don't all register their features statically (some do it dynamically per sensor),
    # but we can check the registry. We should also parse feature_config.yaml.
    with open("backend/app/ai/config/feature_config.yaml", "r") as f:
        feature_config = yaml.safe_load(f)
        
    from pathlib import Path
    validator = AssetValidator(Path("backend/app/ai/config"))
    
    # Instantiate extractors to let them register static features if they do in __init__
    extractors = [
        RawExtractor(feature_config, validator),
        RollingExtractor(feature_config, validator),
        TrendExtractor(feature_config, validator),
        CrossSensorExtractor(feature_config, validator),
        EquipmentExtractor(feature_config, validator),
        PermitExtractor(feature_config, validator),
        DataQualityExtractor(feature_config, validator),
        GeospatialExtractor(feature_config, validator),
        MaintenanceExtractor(feature_config, validator)
    ]
    
    # We will simulate a fake snapshot to force registration of dynamic features
    # But it's easier to list known extracted features from the codebase plus the registry
    
    # Because some features are dynamically named (e.g. hydrocarbon_norm_GD-SIM),
    # we will just gather all explicitly named rule features and check if they exist in our known list.
    
    known_static_features = {
        "worker_count", "active_permit_count",
        "isolation_incomplete", "maintenance_active", "hot_work_active",
        "stale_sensor_count", "adjacent_zone_risk", "maintenance_overdue",
        "esd_bypassed", "exit_obstructed", "confined_space_active",
        "shift_handover_active", "process_active", "line_break_active",
        "min_oxygen_pct", "max_valve_position", "fire_detected", "smoke_detected",
        "unack_alarm_count", "pressure_disagreement", "max_pressure_bar",
        "ventilation_health", "max_hydrocarbon_lel_pct", "max_h2s_ppm", "max_vibration",
        "slope_hydrocarbon", "slope_pressure", "slope_temperature", "slope_h2s"
    }
    
    # Let's assume our planned extracted features will include the dynamic ones 
    # but for this audit, we will just cross-check what the rules need vs what we currently have
    # Let's actually list what is missing *right now* based on what is in the code.
    
    # We will statically define what's in the pipeline right now:
    currently_extracted = {
        "worker_count", "active_permit_count", "isolation_incomplete"
    } # + the dynamic ones which we aren't counting here easily.
    
    # Actually, we can just run the feature extraction on a dummy event to see what it outputs!
    from datetime import datetime, timezone, timedelta
    from backend.app.ai.domain.plant_state import ZoneSnapshot, SensorReading, SourceType, MaintenanceState, PermitState
    
    dummy_snapshot1 = ZoneSnapshot(
        timestamp=datetime.now(timezone.utc) - timedelta(seconds=10),
        zone_id="ZONE_A"
    )
    dummy_snapshot2 = ZoneSnapshot(
        timestamp=datetime.now(timezone.utc),
        zone_id="ZONE_A"
    )
    
    # Add dummy sensors and permits to trigger all extraction logic
    for ds in [dummy_snapshot1, dummy_snapshot2]:
        ds.sensor_values["GD-SIM"] = SensorReading(
            timestamp=ds.timestamp, source_id="GD-SIM", zone_id="ZONE_A",
            source_type=SourceType.SENSOR, category="hydrocarbon", value=15.0, unit="%"
        )
        ds.sensor_values["PT-SIM"] = SensorReading(
            timestamp=ds.timestamp, source_id="PT-SIM", zone_id="ZONE_A",
            source_type=SourceType.SENSOR, category="pressure", value=2.0, unit="bar"
        )
        ds.sensor_values["TT-SIM"] = SensorReading(
            timestamp=ds.timestamp, source_id="TT-SIM", zone_id="ZONE_A",
            source_type=SourceType.SENSOR, category="temperature", value=45.0, unit="C"
        )
        ds.sensor_values["VENT-SIM"] = SensorReading(
            timestamp=ds.timestamp, source_id="VENT-SIM", zone_id="ZONE_A",
            source_type=SourceType.SENSOR, category="ventilation_health", value=0.1, unit="ratio"
        )
        ds.active_maintenance["M-1"] = MaintenanceState(
            timestamp=ds.timestamp, source_id="M-1",
            task_id="M-1", zone_id="ZONE_A", equipment_id="EQ-1", status="ACTIVE", scheduled_start=ds.timestamp, active=True
        )
    
    # Change values in snap2 to trigger trend
    dummy_snapshot2.sensor_values["GD-SIM"].value = 20.0
    dummy_snapshot2.sensor_values["PT-SIM"].value = 2.5
    dummy_snapshot2.sensor_values["TT-SIM"].value = 50.0
    
    # Run extractors
    extracted_features = set()
    for ex in extractors:
        for fv in ex.extract(dummy_snapshot2, [dummy_snapshot1, dummy_snapshot2]):
            extracted_features.add(fv.name)
            
    # Add known aliases we added in evaluate_systems.py (which should really be in extractors)
    # The audit requires us to fix this so extractors emit the rule features directly.
    # Currently extractors output:
    # hydrocarbon_norm_GD-SIM, ventilation_health_norm_VENT-SIM, slope_..., rolling_...
    # worker_count, active_permit_count, isolation_incomplete, stale_sensor_count
    
    missing_features = list(rule_features - extracted_features)
    unused_features = list(extracted_features - rule_features)
    
    coverage = len(rule_features.intersection(extracted_features)) / len(rule_features) if rule_features else 0
    
    output = {
      "rule_features": sorted(list(rule_features)),
      "extracted_features": sorted(list(extracted_features)),
      "missing_features": sorted(missing_features),
      "unused_features": sorted(unused_features),
      "invalid_rule_references": invalid_rule_references,
      "feature_type_mismatches": [], # Would need schema validation
      "coverage_percent": round(coverage * 100, 2)
    }
    
    os.makedirs("evaluation", exist_ok=True)
    with open("evaluation/feature_rule_contract.json", "w") as f:
        json.dump(output, f, indent=2)

if __name__ == "__main__":
    main()
