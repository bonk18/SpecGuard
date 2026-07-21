import pytest
from datetime import datetime, timezone
from ..domain.plant_state import ZoneSnapshot, SensorReading, DataQualityStatus
from ..detection.baseline.evaluator import BaselineEvaluator
from ..ingestion.validators import AssetValidator

class DummyValidator:
    def __init__(self):
        self.sensor_mapping = {
            "sensors": {
                "S1": {"warning_max": 80.0, "critical_max": 90.0, "equipment": "EQ1"},
                "S2": {"min_val": 0.0, "max_val": 100.0} # Fallback to max_val
            }
        }

def test_baseline_evaluator():
    validator = DummyValidator()
    evaluator = BaselineEvaluator(validator)
    
    now = datetime.now(timezone.utc)
    snap = ZoneSnapshot(timestamp=now, zone_id="Z1")
    
    # Normal
    snap.sensor_values["S1"] = SensorReading(timestamp=now, source_id="S1", zone_id="Z1", category="t", value=50.0, unit="C")
    res = evaluator.evaluate(snap)
    assert len(res) == 0
    
    # Warning
    snap.sensor_values["S1"] = SensorReading(timestamp=now, source_id="S1", zone_id="Z1", category="t", value=85.0, unit="C")
    res = evaluator.evaluate(snap)
    assert len(res) == 1
    assert res[0].alarm_level == "WARNING"
    
    # Critical
    snap.sensor_values["S1"] = SensorReading(timestamp=now, source_id="S1", zone_id="Z1", category="t", value=95.0, unit="C")
    res = evaluator.evaluate(snap)
    assert len(res) == 1
    assert res[0].alarm_level == "CRITICAL"
    
    # Fallback to max_val
    snap.sensor_values["S2"] = SensorReading(timestamp=now, source_id="S2", zone_id="Z1", category="t", value=105.0, unit="C")
    res = evaluator.evaluate(snap)
    # S1 is still critical, S2 is critical
    assert len(res) == 2
    assert res[1].sensor == "S2"
    assert res[1].alarm_level == "CRITICAL"
