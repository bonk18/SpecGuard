from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional
import pandas as pd
from ..domain.plant_state import (
    PlantSnapshot, ZoneSnapshot, SensorReading, EquipmentState,
    PermitState, MaintenanceState, WorkerEvent, CCTVEvent, ScenarioGroundTruth,
    TemporalRecord, DataQualityIssue
)
from ..domain.enums import DataQualityStatus
from .validators import AssetValidator

class StateStore:
    def __init__(self):
        self.sensors: Dict[str, SensorReading] = {}
        self.equipment: Dict[str, EquipmentState] = {}
        self.permits: Dict[str, PermitState] = {}
        self.maintenance: Dict[str, MaintenanceState] = {}
        self.workers: Dict[str, WorkerEvent] = {}

class PlantStateAssembler:
    def __init__(self, validator: AssetValidator, config: Dict):
        self.validator = validator
        self.config = config
        self.state = StateStore()

    def process_event(self, event: TemporalRecord) -> List[DataQualityIssue]:
        issues = []
        if isinstance(event, SensorReading):
            issues.extend(self.validator.validate_sensor_reading(event))
            if not any(i.issue_type == DataQualityStatus.FUTURE_TIMESTAMP for i in issues):
                self.state.sensors[event.source_id] = event
        elif isinstance(event, EquipmentState):
            self.state.equipment[event.source_id] = event
        elif isinstance(event, PermitState):
            issues.extend(self.validator.validate_permit(event))
            if not any(i.issue_type == DataQualityStatus.FUTURE_TIMESTAMP for i in issues):
                if event.active:
                    self.state.permits[event.source_id] = event
                else:
                    self.state.permits.pop(event.source_id, None)
        elif isinstance(event, MaintenanceState):
            issues.extend(self.validator.validate_maintenance(event))
            if not any(i.issue_type == DataQualityStatus.FUTURE_TIMESTAMP for i in issues):
                if event.active:
                    self.state.maintenance[event.source_id] = event
                else:
                    self.state.maintenance.pop(event.source_id, None)
        elif isinstance(event, WorkerEvent):
            if event.action == "ENTER" or event.action == "UPDATE":
                self.state.workers[event.worker_id] = event
            elif event.action == "EXIT":
                self.state.workers.pop(event.worker_id, None)
        # handle CCTV and SCENARIO here
        
        return issues

    def build_snapshot(self, timestamp: datetime) -> PlantSnapshot:
        snapshot = PlantSnapshot(timestamp=timestamp)
        zones = self.validator.sensor_mapping.get("zones", {})
        
        for zone_id, zone_info in zones.items():
            snapshot.zones[zone_id] = ZoneSnapshot(
                timestamp=timestamp,
                zone_id=zone_id,
                adjacent_zones=zone_info.get("adjacent", [])
            )
            
        for sensor_id, reading in self.state.sensors.items():
            if reading.zone_id in snapshot.zones:
                age = (timestamp - reading.timestamp).total_seconds()
                max_age = self.config.get("forward_fill_max_age", 60)
                is_safety_critical = self.validator.sensor_mapping.get("sensors", {}).get(sensor_id, {}).get("safety_critical", False)
                
                status = reading.data_quality_status
                if is_safety_critical and age > self.config.get("safety_critical_max_age", 5):
                    status = DataQualityStatus.STALE
                elif age > max_age:
                    status = DataQualityStatus.STALE
                    
                reading_copy = reading.model_copy()
                reading_copy.data_quality_status = status
                
                snapshot.zones[reading.zone_id].sensor_values[sensor_id] = reading_copy
                snapshot.zones[reading.zone_id].data_freshness[sensor_id] = age
                
        for worker_id, event in list(self.state.workers.items()):
            age = (timestamp - event.timestamp).total_seconds()
            if age > self.config.get("worker_event_expiry", 3600):
                self.state.workers.pop(worker_id, None)
            elif event.zone_id in snapshot.zones:
                snapshot.zones[event.zone_id].workers_present[worker_id] = event

        for permit_id, event in list(self.state.permits.items()):
            age = (timestamp - event.timestamp).total_seconds()
            if age > self.config.get("permit_validity", 8*3600):
                self.state.permits.pop(permit_id, None)
            elif event.zone_id in snapshot.zones:
                snapshot.zones[event.zone_id].active_permits[permit_id] = event
                
        for maintenance_id, event in list(self.state.maintenance.items()):
            age = (timestamp - event.timestamp).total_seconds()
            if age > self.config.get("maintenance_validity", 8*3600):
                self.state.maintenance.pop(maintenance_id, None)
            elif event.zone_id in snapshot.zones:
                snapshot.zones[event.zone_id].active_maintenance[maintenance_id] = event

        for equipment_id, event in list(self.state.equipment.items()):
            if event.zone_id in snapshot.zones:
                 snapshot.zones[event.zone_id].equipment_states[equipment_id] = event
                
        return snapshot

    def process_batch(self, events: List[TemporalRecord], interval_seconds: int = 1) -> List[PlantSnapshot]:
        snapshots = []
        if not events: 
            return []
            
        events.sort(key=lambda x: x.timestamp)
        current_time = events[0].timestamp
        
        for event in events:
            while event.timestamp >= current_time + timedelta(seconds=interval_seconds):
                snapshots.append(self.build_snapshot(current_time))
                current_time += timedelta(seconds=interval_seconds)
            self.process_event(event)
            
        snapshots.append(self.build_snapshot(current_time))
        return snapshots
