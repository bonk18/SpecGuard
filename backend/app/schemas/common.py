"""Shared vocabulary and validation behavior for SpecGuard contracts."""

from enum import Enum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, StringConstraints


# A controlled enum prevents different services from representing the same
# concept as "hot-work", "Hot Work", and "HOT_WORK". Stable values make joins,
# filtering, alert rules, and frontend rendering predictable across the system.
class Severity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class ZoneId(str, Enum):
    """Prototype refinery zones with stable serialized identifiers."""

    STORAGE_AREA = "ZONE_A"
    PUMP_STATION = "ZONE_B"
    PIPELINE_AREA = "ZONE_C"
    MAINTENANCE_AREA = "ZONE_D"
    CONTROL_ROOM = "ZONE_E"


class RiskType(str, Enum):
    FIRE_EXPLOSION = "FIRE_EXPLOSION"
    TOXIC_GAS_EXPOSURE = "TOXIC_GAS_EXPOSURE"
    OXYGEN_DEFICIENCY = "OXYGEN_DEFICIENCY"
    OVERPRESSURE = "OVERPRESSURE"
    EQUIPMENT_FAILURE = "EQUIPMENT_FAILURE"
    CONFINED_SPACE = "CONFINED_SPACE"
    ELECTRICAL_HAZARD = "ELECTRICAL_HAZARD"
    UNKNOWN = "UNKNOWN"


class HazardCode(str, Enum):
    RISING_LEL = "RISING_LEL"
    HIGH_H2S = "HIGH_H2S"
    LOW_OXYGEN = "LOW_OXYGEN"
    PRESSURE_RISING = "PRESSURE_RISING"
    HIGH_TEMPERATURE = "HIGH_TEMPERATURE"
    ABNORMAL_FLOW = "ABNORMAL_FLOW"
    VENTILATION_FAILURE = "VENTILATION_FAILURE"
    INCOMPLETE_ISOLATION = "INCOMPLETE_ISOLATION"
    HOT_WORK_ACTIVE = "HOT_WORK_ACTIVE"
    CONFINED_SPACE_ACTIVE = "CONFINED_SPACE_ACTIVE"
    WORKERS_PRESENT = "WORKERS_PRESENT"
    PPE_VIOLATION = "PPE_VIOLATION"
    RESTRICTED_ZONE_ENTRY = "RESTRICTED_ZONE_ENTRY"
    OVERDUE_MAINTENANCE = "OVERDUE_MAINTENANCE"
    UNRESOLVED_SHIFT_OBSERVATION = "UNRESOLVED_SHIFT_OBSERVATION"
    UNKNOWN = "UNKNOWN"


class PermitType(str, Enum):
    HOT_WORK = "HOT_WORK"
    COLD_WORK = "COLD_WORK"
    CONFINED_SPACE = "CONFINED_SPACE"
    LINE_BREAKING = "LINE_BREAKING"
    ELECTRICAL = "ELECTRICAL"
    WORKING_AT_HEIGHT = "WORKING_AT_HEIGHT"


class PermitStatus(str, Enum):
    DRAFT = "DRAFT"
    REQUESTED = "REQUESTED"
    APPROVED = "APPROVED"
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    EXPIRED = "EXPIRED"
    CLOSED = "CLOSED"
    CANCELLED = "CANCELLED"


class MaintenanceStatus(str, Enum):
    SCHEDULED = "SCHEDULED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    OVERDUE = "OVERDUE"
    CANCELLED = "CANCELLED"


class ActionStatus(str, Enum):
    PROPOSED = "PROPOSED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class EvidenceType(str, Enum):
    REGULATION = "REGULATION"
    SOP = "SOP"
    HISTORICAL_INCIDENT = "HISTORICAL_INCIDENT"
    NEAR_MISS = "NEAR_MISS"
    SHIFT_LOG = "SHIFT_LOG"
    SENSOR = "SENSOR"
    PERMIT = "PERMIT"
    MAINTENANCE = "MAINTENANCE"
    CCTV = "CCTV"


NonEmptyString = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1),
]
UsefulText = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=10),
]


class SpecGuardSchema(BaseModel):
    """Base behavior shared by the new public service contracts.

    Rejecting unknown fields catches producer/consumer version drift instead of
    silently discarding safety-relevant data. Whitespace stripping also makes a
    string containing only spaces fail the normal minimum-length checks.
    """

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
