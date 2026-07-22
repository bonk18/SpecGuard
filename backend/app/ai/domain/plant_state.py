from datetime import datetime
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from .enums import DataQualityStatus, SourceType

class DataQualityIssue(BaseModel):
    timestamp: datetime
    source_id: str
    issue_type: DataQualityStatus
    description: str

class TemporalRecord(BaseModel):
    timestamp: datetime
    source_id: str
    zone_id: str
    equipment_id: Optional[str] = None
    source_type: SourceType
    data_quality_status: DataQualityStatus = DataQualityStatus.VALID

class SensorReading(TemporalRecord):
    source_type: SourceType = SourceType.SENSOR
    category: str
    value: float
    unit: str

class EquipmentState(TemporalRecord):
    source_type: SourceType = SourceType.EQUIPMENT
    status: str
    health_score: Optional[float] = None

class PermitState(TemporalRecord):
    source_type: SourceType = SourceType.PERMIT
    permit_type: str
    status: str
    active: bool

class MaintenanceState(TemporalRecord):
    source_type: SourceType = SourceType.MAINTENANCE
    task_id: str
    status: str
    active: bool

class WorkerEvent(TemporalRecord):
    source_type: SourceType = SourceType.WORKER
    worker_id: str
    action: str  # "ENTER", "EXIT", "UPDATE"

class CCTVEvent(TemporalRecord):
    source_type: SourceType = SourceType.CCTV
    event_type: str
    confidence: float

class ScenarioGroundTruth(TemporalRecord):
    source_type: SourceType = SourceType.SCENARIO
    scenario_id: str
    event_label: str

class ZoneSnapshot(BaseModel):
    timestamp: datetime
    zone_id: str
    sensor_values: Dict[str, SensorReading] = Field(default_factory=dict)
    equipment_states: Dict[str, EquipmentState] = Field(default_factory=dict)
    active_permits: Dict[str, PermitState] = Field(default_factory=dict)
    active_maintenance: Dict[str, MaintenanceState] = Field(default_factory=dict)
    workers_present: Dict[str, WorkerEvent] = Field(default_factory=dict)
    cctv_events: List[CCTVEvent] = Field(default_factory=list)
    adjacent_zones: List[str] = Field(default_factory=list)
    data_freshness: Dict[str, float] = Field(default_factory=dict)
    missing_sources: List[str] = Field(default_factory=list)
    scenario_metadata: Optional[ScenarioGroundTruth] = None
    quality_issues: List[DataQualityIssue] = Field(default_factory=list)

class PlantSnapshot(BaseModel):
    timestamp: datetime
    zones: Dict[str, ZoneSnapshot] = Field(default_factory=dict)
    global_quality_issues: List[DataQualityIssue] = Field(default_factory=list)
