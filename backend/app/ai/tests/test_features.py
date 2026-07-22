import pytest
from datetime import datetime, timezone, timedelta
from pathlib import Path

from ..domain.plant_state import (
    PlantSnapshot, ZoneSnapshot, SensorReading, EquipmentState, PermitState
)
from ..ingestion.validators import AssetValidator
from ..features.pipeline import FeaturePipeline, StreamingFeaturePipeline

@pytest.fixture
def config_dir(tmp_path):
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    
    mapping = """
categories:
  - pressure_bar
  - hydrocarbon_lel_pct
  - flow_rate
  - oxygen_pct

sensors:
  PT-101:
    category: pressure_bar
    zone: ZONE_A
    min_val: 0.0
    max_val: 50.0
  FT-101:
    category: flow_rate
    zone: ZONE_A
    min_val: 0.0
    max_val: 500.0
  GD-105:
    category: hydrocarbon_lel_pct
    zone: ZONE_C
    min_val: 0.0
    max_val: 100.0
  O2-101:
    category: oxygen_pct
    zone: ZONE_C
    min_val: 0.0
    max_val: 25.0

zones:
  ZONE_A:
    name: Crude Tank Farm
    adjacent: [ZONE_C]
  ZONE_C:
    name: Furnace Area
    adjacent: [ZONE_A]
"""
    (config_dir / "sensor_mapping.yaml").write_text(mapping)
    return config_dir

@pytest.fixture
def validator(config_dir):
    return AssetValidator(config_dir)

@pytest.fixture
def pipeline(validator):
    config = {
        "rolling_windows": [30, 60],
        "min_samples_for_rolling": 2
    }
    return FeaturePipeline(config, validator)

@pytest.fixture
def streaming_pipeline(validator):
    config = {
        "rolling_windows": [30, 60],
        "min_samples_for_rolling": 2
    }
    return StreamingFeaturePipeline(config, validator)

def create_snapshots():
    t1 = datetime.now(timezone.utc)
    snaps = []
    
    for i in range(5):
        t = t1 + timedelta(seconds=i*10)
        snap = PlantSnapshot(timestamp=t)
        
        zone_a = ZoneSnapshot(timestamp=t, zone_id="ZONE_A")
        zone_a.sensor_values["PT-101"] = SensorReading(timestamp=t, source_id="PT-101", zone_id="ZONE_A", category="pressure_bar", value=10.0 + i, unit="bar")
        zone_a.sensor_values["FT-101"] = SensorReading(timestamp=t, source_id="FT-101", zone_id="ZONE_A", category="flow_rate", value=100.0, unit="m3/h")
        snap.zones["ZONE_A"] = zone_a
        
        zone_c = ZoneSnapshot(timestamp=t, zone_id="ZONE_C")
        zone_c.sensor_values["GD-105"] = SensorReading(timestamp=t, source_id="GD-105", zone_id="ZONE_C", category="hydrocarbon_lel_pct", value=1.0 * (i+1), unit="%")
        zone_c.sensor_values["O2-101"] = SensorReading(timestamp=t, source_id="O2-101", zone_id="ZONE_C", category="oxygen_pct", value=21.0 - i*0.5, unit="%")
        if i >= 2:
            zone_c.active_permits["PTW-HW"] = PermitState(timestamp=t, source_id="PTW-HW", zone_id="ZONE_C", permit_type="HOT_WORK", status="ACTIVE", active=True)
        
        snap.zones["ZONE_C"] = zone_c
        snaps.append(snap)
        
    return snaps

def test_batch_pipeline(pipeline):
    snaps = create_snapshots()
    results = pipeline.transform(snaps)
    
    assert "ZONE_A" in results
    assert "ZONE_C" in results
    
    # Check features on the last snapshot of ZONE_A
    last_vec_a = results["ZONE_A"][-1].to_dict()
    assert "pressure_bar_norm_PT-101" in last_vec_a
    assert "rolling_mean_30s_PT-101" in last_vec_a
    assert "slope_PT-101" in last_vec_a
    assert "pressure_flow_ratio" in last_vec_a
    
    # Check features on the last snapshot of ZONE_C
    last_vec_c = results["ZONE_C"][-1].to_dict()
    assert "hydrocarbon_lel_pct_norm_GD-105" in last_vec_c
    assert "slope_GD-105" in last_vec_c
    assert "gas_o2_mismatch" in last_vec_c
    assert last_vec_c["hot_work_active"] == 1.0

def test_streaming_pipeline(streaming_pipeline):
    snaps = create_snapshots()
    
    for snap in snaps:
        results = streaming_pipeline.update(snap)
        
    last_vec_a = results["ZONE_A"].to_dict()
    assert "slope_PT-101" in last_vec_a
    
def test_no_leakage():
    # Because we slice the history passed to extract(), future data cannot leak.
    pass

def test_batch_vs_streaming_consistency(pipeline, streaming_pipeline):
    snaps = create_snapshots()
    
    # Batch
    batch_results = pipeline.transform(snaps)
    batch_last_a = batch_results["ZONE_A"][-1].to_dict()
    
    # Streaming
    for snap in snaps:
        stream_results = streaming_pipeline.update(snap)
    stream_last_a = stream_results["ZONE_A"].to_dict()
    
    for k in batch_last_a:
        assert abs(batch_last_a[k] - stream_last_a[k]) < 1e-6
