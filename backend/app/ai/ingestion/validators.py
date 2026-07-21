import yaml
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional
from ..domain.plant_state import TemporalRecord, SensorReading, DataQualityIssue, PermitState, MaintenanceState
from ..domain.enums import DataQualityStatus

class AssetValidator:
    def __init__(self, config_dir: Path):
        self.sensor_mapping = self._load_yaml(config_dir / "sensor_mapping.yaml")
        
    def _load_yaml(self, path: Path) -> Dict:
        if path.exists():
            with open(path, 'r') as f:
                return yaml.safe_load(f)
        return {}
        
    def validate_sensor_reading(self, reading: SensorReading) -> List[DataQualityIssue]:
        issues = []
        now = datetime.now(timezone.utc)
        
        # Check future timestamp
        if reading.timestamp > now:
            issues.append(DataQualityIssue(
                timestamp=reading.timestamp,
                source_id=reading.source_id,
                issue_type=DataQualityStatus.FUTURE_TIMESTAMP,
                description="Timestamp is in the future"
            ))
            
        # Check sensor exists
        sensor_info = self.sensor_mapping.get("sensors", {}).get(reading.source_id)
        if not sensor_info:
            issues.append(DataQualityIssue(
                timestamp=reading.timestamp,
                source_id=reading.source_id,
                issue_type=DataQualityStatus.INVALID_REF,
                description=f"Sensor {reading.source_id} not found in master asset model"
            ))
            return issues
            
        # Validate zone match
        if sensor_info.get("zone") != reading.zone_id:
            issues.append(DataQualityIssue(
                timestamp=reading.timestamp,
                source_id=reading.source_id,
                issue_type=DataQualityStatus.INVALID_REF,
                description=f"Sensor {reading.source_id} does not belong to zone {reading.zone_id}"
            ))
            
        # Validate equipment match if applicable
        if reading.equipment_id and sensor_info.get("equipment") != reading.equipment_id:
            issues.append(DataQualityIssue(
                timestamp=reading.timestamp,
                source_id=reading.source_id,
                issue_type=DataQualityStatus.INVALID_REF,
                description=f"Sensor {reading.source_id} does not belong to equipment {reading.equipment_id}"
            ))
            
        # Validate plausible limits
        min_val = sensor_info.get("min_val", float('-inf'))
        max_val = sensor_info.get("max_val", float('inf'))
        if not (min_val <= reading.value <= max_val):
            issues.append(DataQualityIssue(
                timestamp=reading.timestamp,
                source_id=reading.source_id,
                issue_type=DataQualityStatus.OUT_OF_BOUNDS,
                description=f"Value {reading.value} out of plausible bounds [{min_val}, {max_val}]"
            ))
            
        return issues
        
    def validate_permit(self, permit: PermitState) -> List[DataQualityIssue]:
        issues = []
        now = datetime.now(timezone.utc)
        
        if permit.timestamp > now:
            issues.append(DataQualityIssue(
                timestamp=permit.timestamp,
                source_id=permit.source_id,
                issue_type=DataQualityStatus.FUTURE_TIMESTAMP,
                description="Timestamp is in the future"
            ))
            
        zones = self.sensor_mapping.get("zones", {})
        if permit.zone_id not in zones:
            issues.append(DataQualityIssue(
                timestamp=permit.timestamp,
                source_id=permit.source_id,
                issue_type=DataQualityStatus.INVALID_REF,
                description=f"Zone {permit.zone_id} not found in master asset model"
            ))
            
        if permit.equipment_id:
            equipment = self.sensor_mapping.get("equipment", {})
            if permit.equipment_id not in equipment:
                issues.append(DataQualityIssue(
                    timestamp=permit.timestamp,
                    source_id=permit.source_id,
                    issue_type=DataQualityStatus.INVALID_REF,
                    description=f"Equipment {permit.equipment_id} not found in master asset model"
                ))
        return issues

    def validate_maintenance(self, maintenance: MaintenanceState) -> List[DataQualityIssue]:
        issues = []
        now = datetime.now(timezone.utc)
        
        if maintenance.timestamp > now:
            issues.append(DataQualityIssue(
                timestamp=maintenance.timestamp,
                source_id=maintenance.source_id,
                issue_type=DataQualityStatus.FUTURE_TIMESTAMP,
                description="Timestamp is in the future"
            ))
            
        if maintenance.equipment_id:
            equipment = self.sensor_mapping.get("equipment", {})
            if maintenance.equipment_id not in equipment:
                issues.append(DataQualityIssue(
                    timestamp=maintenance.timestamp,
                    source_id=maintenance.source_id,
                    issue_type=DataQualityStatus.INVALID_REF,
                    description=f"Equipment {maintenance.equipment_id} not found in master asset model"
                ))
        return issues
