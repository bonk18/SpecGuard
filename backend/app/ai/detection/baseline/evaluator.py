from typing import List, Dict, Any
from .models import BaselineResult
from ...domain.plant_state import ZoneSnapshot, DataQualityStatus
from ...ingestion.validators import AssetValidator

class BaselineEvaluator:
    def __init__(self, validator: AssetValidator):
        self.validator = validator
        
    def evaluate(self, snapshot: ZoneSnapshot) -> List[BaselineResult]:
        results = []
        for sensor_id, reading in snapshot.sensor_values.items():
            if reading.data_quality_status == DataQualityStatus.STALE:
                # Based on config, decide whether to alert on stale. 
                # For baseline, we strictly evaluate raw values against limits.
                pass
            
            sensor_info = self.validator.sensor_mapping.get("sensors", {}).get(sensor_id, {})
            
            # Use specific warning/critical bounds if available, else fallback to min_val/max_val
            critical_max = sensor_info.get("critical_max", sensor_info.get("max_val"))
            warning_max = sensor_info.get("warning_max")
            
            critical_min = sensor_info.get("critical_min", sensor_info.get("min_val"))
            warning_min = sensor_info.get("warning_min")
            
            triggered = False
            level = None
            threshold = 0.0
            
            if critical_max is not None and reading.value >= critical_max:
                triggered = True
                level = "CRITICAL"
                threshold = critical_max
            elif critical_min is not None and reading.value <= critical_min:
                triggered = True
                level = "CRITICAL"
                threshold = critical_min
            elif warning_max is not None and reading.value >= warning_max:
                triggered = True
                level = "WARNING"
                threshold = warning_max
            elif warning_min is not None and reading.value <= warning_min:
                triggered = True
                level = "WARNING"
                threshold = warning_min
                
            if triggered:
                results.append(BaselineResult(
                    alarm_triggered=True,
                    alarm_level=level,
                    sensor=sensor_id,
                    value=reading.value,
                    threshold=threshold,
                    detection_time=snapshot.timestamp.isoformat(),
                    zone=snapshot.zone_id,
                    equipment=sensor_info.get("equipment"),
                    data_quality=reading.data_quality_status.value
                ))
                
        return results
