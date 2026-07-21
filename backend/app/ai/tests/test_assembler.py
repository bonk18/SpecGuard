import pytest
from datetime import datetime, timezone, timedelta
from pathlib import Path
from ..domain.plant_state import (
    SensorReading, DataQualityStatus, EquipmentState, PermitState, MaintenanceState, WorkerEvent
)
from ..domain.enums import SourceType
from ..ingestion.validators import AssetValidator
from ..ingestion.state_assembler import PlantStateAssembler

@pytest.fixture
def config_dir(tmp_path):
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    
    mapping = """
categories:
  - pressure_bar
  - hydrocarbon_lel_pct

sensors:
  PT-101:
    category: pressure_bar
    zone: ZONE_A
    equipment: TK-101
    min_val: 0.0
    max_val: 50.0
    safety_critical: false
  GD-105:
    category: hydrocarbon_lel_pct
    zone: ZONE_C
    equipment: H-101
    min_val: 0.0
    max_val: 100.0
    safety_critical: true

equipment:
  TK-101:
    type: storage_tank
    zone: ZONE_A

zones:
  ZONE_A:
    name: Crude Tank Farm
    adjacent: [ZONE_B]
  ZONE_C:
    name: Furnace Area
    adjacent: []
"""
    (config_dir / "sensor_mapping.yaml").write_text(mapping)
    return config_dir

@pytest.fixture
def validator(config_dir):
    return AssetValidator(config_dir)

@pytest.fixture
def assembler(validator):
    config = {
        "forward_fill_max_age": 60,
        "safety_critical_max_age": 5,
        "permit_validity": 3600,
        "worker_event_expiry": 3600
    }
    return PlantStateAssembler(validator, config)

def test_valid_sensor_assembly(assembler):
    now = datetime.now(timezone.utc)
    reading = SensorReading(
        timestamp=now,
        source_id="PT-101",
        zone_id="ZONE_A",
        equipment_id="TK-101",
        category="pressure_bar",
        value=15.0,
        unit="bar"
    )
    issues = assembler.process_event(reading)
    assert len(issues) == 0
    
    snapshot = assembler.build_snapshot(now)
    assert "PT-101" in snapshot.zones["ZONE_A"].sensor_values
    assert snapshot.zones["ZONE_A"].sensor_values["PT-101"].value == 15.0

def test_missing_sensor(assembler):
    now = datetime.now(timezone.utc)
    reading = SensorReading(
        timestamp=now,
        source_id="UNKNOWN",
        zone_id="ZONE_A",
        category="pressure_bar",
        value=15.0,
        unit="bar"
    )
    issues = assembler.process_event(reading)
    assert len(issues) > 0
    assert any(i.issue_type == DataQualityStatus.INVALID_REF for i in issues)

def test_stale_reading(assembler):
    past = datetime.now(timezone.utc) - timedelta(seconds=70)
    reading = SensorReading(
        timestamp=past,
        source_id="PT-101",
        zone_id="ZONE_A",
        category="pressure_bar",
        value=15.0,
        unit="bar"
    )
    assembler.process_event(reading)
    
    now = datetime.now(timezone.utc)
    snapshot = assembler.build_snapshot(now)
    
    stale_reading = snapshot.zones["ZONE_A"].sensor_values["PT-101"]
    assert stale_reading.data_quality_status == DataQualityStatus.STALE

def test_safety_critical_stale(assembler):
    past = datetime.now(timezone.utc) - timedelta(seconds=10)
    reading = SensorReading(
        timestamp=past,
        source_id="GD-105",
        zone_id="ZONE_C",
        equipment_id="H-101",
        category="hydrocarbon_lel_pct",
        value=5.0,
        unit="%"
    )
    assembler.process_event(reading)
    
    now = datetime.now(timezone.utc)
    snapshot = assembler.build_snapshot(now)
    
    stale_reading = snapshot.zones["ZONE_C"].sensor_values["GD-105"]
    assert stale_reading.data_quality_status == DataQualityStatus.STALE

def test_batch_processing(assembler):
    t1 = datetime.now(timezone.utc) - timedelta(seconds=10)
    t2 = t1 + timedelta(seconds=1)
    t3 = t2 + timedelta(seconds=1)
    
    events = [
        SensorReading(timestamp=t1, source_id="PT-101", zone_id="ZONE_A", category="pressure_bar", value=10.0, unit="bar"),
        SensorReading(timestamp=t3, source_id="PT-101", zone_id="ZONE_A", category="pressure_bar", value=12.0, unit="bar")
    ]
    
    snapshots = assembler.process_batch(events, interval_seconds=1)
    # t1, t2, t3 snapshots
    assert len(snapshots) == 3
    assert snapshots[0].zones["ZONE_A"].sensor_values["PT-101"].value == 10.0
    # t2 uses forward fill from t1
    assert snapshots[1].zones["ZONE_A"].sensor_values["PT-101"].value == 10.0
    assert snapshots[2].zones["ZONE_A"].sensor_values["PT-101"].value == 12.0

def test_permit_activation_expiry(assembler):
    now = datetime.now(timezone.utc)
    permit = PermitState(
        timestamp=now,
        source_id="PTW-123",
        zone_id="ZONE_A",
        permit_type="HOT_WORK",
        status="ACTIVE",
        active=True
    )
    assembler.process_event(permit)
    assert "PTW-123" in assembler.build_snapshot(now).zones["ZONE_A"].active_permits
    
    # Expiry
    future = now + timedelta(seconds=4000)
    assert "PTW-123" not in assembler.build_snapshot(future).zones["ZONE_A"].active_permits

def test_worker_events(assembler):
    now = datetime.now(timezone.utc)
    worker = WorkerEvent(
        timestamp=now,
        source_id="W-1",
        zone_id="ZONE_A",
        worker_id="WRK-100",
        action="ENTER"
    )
    assembler.process_event(worker)
    assert "WRK-100" in assembler.build_snapshot(now).zones["ZONE_A"].workers_present
    
    worker_exit = WorkerEvent(
        timestamp=now + timedelta(seconds=1),
        source_id="W-1",
        zone_id="ZONE_A",
        worker_id="WRK-100",
        action="EXIT"
    )
    assembler.process_event(worker_exit)
    assert "WRK-100" not in assembler.build_snapshot(now + timedelta(seconds=1)).zones["ZONE_A"].workers_present
