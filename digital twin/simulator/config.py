"""
Global configuration for the petroleum refinery digital twin.

Defines plant layout, zones, equipment, worker roster, sensor specifications,
and simulation parameters.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


# ─────────────────────────────────────────────────────────────────────
# Enumerations
# ─────────────────────────────────────────────────────────────────────

class ZoneID(str, Enum):
    ZONE_A = "Zone_A"  # Storage Tank area
    ZONE_B = "Zone_B"  # Pipeline Network
    ZONE_C = "Zone_C"  # Pump Station
    ZONE_D = "Zone_D"  # Maintenance Area
    ZONE_E = "Zone_E"  # Control Room


class EquipmentType(str, Enum):
    STORAGE_TANK = "storage_tank"
    PIPELINE = "pipeline"
    PUMP = "pump"
    VALVE = "valve"
    VENTILATION = "ventilation"


class EquipmentState(str, Enum):
    RUNNING = "running"
    STOPPED = "stopped"
    DEGRADED = "degraded"
    FAILED = "failed"
    MAINTENANCE = "maintenance"


class PermitType(str, Enum):
    HOT_WORK = "hot_work"
    CONFINED_SPACE = "confined_space"
    ELECTRICAL = "electrical"
    LINE_BREAKING = "line_breaking"


class PermitStatus(str, Enum):
    REQUESTED = "requested"
    APPROVED = "approved"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    CLOSED = "closed"


class ScenarioID(str, Enum):
    NORMAL = "normal"
    GAS_LEAK = "gas_leak"
    VENTILATION_FAILURE = "ventilation_failure"
    PUMP_FAILURE = "pump_failure"
    HOT_WORK_GAS_LEAK = "hot_work_gas_leak"
    CONFINED_SPACE = "confined_space"
    EXPLOSION_RISK = "explosion_risk"


class Shift(str, Enum):
    DAY = "day"
    NIGHT = "night"


# ─────────────────────────────────────────────────────────────────────
# Data Classes
# ─────────────────────────────────────────────────────────────────────

@dataclass
class ZoneConfig:
    zone_id: ZoneID
    name: str
    description: str
    hazard_rating: int          # 1-5
    max_workers: int
    is_confined: bool = False
    requires_gas_test: bool = False
    equipment_ids: list[str] = field(default_factory=list)


@dataclass
class EquipmentConfig:
    equipment_id: str
    equipment_type: EquipmentType
    zone_id: ZoneID
    name: str
    base_degradation_rate: float   # per second
    failure_threshold: float       # health below this = failure


@dataclass
class SensorSpec:
    """Specification for a single sensor channel."""
    name: str
    unit: str
    nominal: float          # Normal operating value
    std: float              # Normal operating std deviation
    low_alarm: float
    high_alarm: float
    hihi_alarm: float
    noise_std: float        # Measurement noise


@dataclass
class WorkerProfile:
    worker_id: str
    name: str
    role: str
    shift: Shift
    certifications: list[str] = field(default_factory=list)


# ─────────────────────────────────────────────────────────────────────
# Plant Layout
# ─────────────────────────────────────────────────────────────────────

ZONES: dict[ZoneID, ZoneConfig] = {
    ZoneID.ZONE_A: ZoneConfig(
        zone_id=ZoneID.ZONE_A,
        name="Storage Tank Area",
        description="Hydrocarbon storage tanks with level and pressure monitoring",
        hazard_rating=4,
        max_workers=4,
        is_confined=False,
        requires_gas_test=True,
        equipment_ids=["TK-101", "TK-102", "VLV-101", "VENT-101"],
    ),
    ZoneID.ZONE_B: ZoneConfig(
        zone_id=ZoneID.ZONE_B,
        name="Pipeline Network",
        description="Interconnecting pipeline with flow and pressure monitoring",
        hazard_rating=3,
        max_workers=3,
        is_confined=False,
        requires_gas_test=True,
        equipment_ids=["PL-201", "PL-202", "VLV-201", "VLV-202"],
    ),
    ZoneID.ZONE_C: ZoneConfig(
        zone_id=ZoneID.ZONE_C,
        name="Pump Station",
        description="Main pumping station with centrifugal pumps",
        hazard_rating=4,
        max_workers=3,
        is_confined=False,
        requires_gas_test=True,
        equipment_ids=["PMP-301", "PMP-302", "VLV-301", "VENT-301"],
    ),
    ZoneID.ZONE_D: ZoneConfig(
        zone_id=ZoneID.ZONE_D,
        name="Maintenance Workshop",
        description="Maintenance and repair area with confined spaces",
        hazard_rating=2,
        max_workers=6,
        is_confined=True,
        requires_gas_test=True,
        equipment_ids=["VENT-401"],
    ),
    ZoneID.ZONE_E: ZoneConfig(
        zone_id=ZoneID.ZONE_E,
        name="Control Room",
        description="Central control and monitoring facility",
        hazard_rating=1,
        max_workers=4,
        is_confined=False,
        requires_gas_test=False,
        equipment_ids=[],
    ),
}


# ─────────────────────────────────────────────────────────────────────
# Equipment Registry
# ─────────────────────────────────────────────────────────────────────

EQUIPMENT: dict[str, EquipmentConfig] = {
    # Zone A - Storage Tanks
    "TK-101": EquipmentConfig("TK-101", EquipmentType.STORAGE_TANK, ZoneID.ZONE_A,
                               "Primary Storage Tank", 1e-7, 0.15),
    "TK-102": EquipmentConfig("TK-102", EquipmentType.STORAGE_TANK, ZoneID.ZONE_A,
                               "Secondary Storage Tank", 1e-7, 0.15),
    "VLV-101": EquipmentConfig("VLV-101", EquipmentType.VALVE, ZoneID.ZONE_A,
                                "Tank Inlet Isolation Valve", 5e-8, 0.2),
    "VENT-101": EquipmentConfig("VENT-101", EquipmentType.VENTILATION, ZoneID.ZONE_A,
                                 "Tank Area Ventilation", 8e-8, 0.2),
    # Zone B - Pipeline
    "PL-201": EquipmentConfig("PL-201", EquipmentType.PIPELINE, ZoneID.ZONE_B,
                               "Main Feed Pipeline", 5e-8, 0.1),
    "PL-202": EquipmentConfig("PL-202", EquipmentType.PIPELINE, ZoneID.ZONE_B,
                               "Product Pipeline", 5e-8, 0.1),
    "VLV-201": EquipmentConfig("VLV-201", EquipmentType.VALVE, ZoneID.ZONE_B,
                                "Pipeline Isolation Valve", 5e-8, 0.2),
    "VLV-202": EquipmentConfig("VLV-202", EquipmentType.VALVE, ZoneID.ZONE_B,
                                "Pipeline Relief Valve", 5e-8, 0.2),
    # Zone C - Pump Station
    "PMP-301": EquipmentConfig("PMP-301", EquipmentType.PUMP, ZoneID.ZONE_C,
                                "Main Feed Pump", 2e-7, 0.15),
    "PMP-302": EquipmentConfig("PMP-302", EquipmentType.PUMP, ZoneID.ZONE_C,
                                "Standby Pump", 1e-7, 0.15),
    "VLV-301": EquipmentConfig("VLV-301", EquipmentType.VALVE, ZoneID.ZONE_C,
                                "Pump Discharge Valve", 5e-8, 0.2),
    "VENT-301": EquipmentConfig("VENT-301", EquipmentType.VENTILATION, ZoneID.ZONE_C,
                                 "Pump Station Ventilation", 8e-8, 0.2),
    # Zone D - Maintenance
    "VENT-401": EquipmentConfig("VENT-401", EquipmentType.VENTILATION, ZoneID.ZONE_D,
                                 "Workshop Ventilation", 8e-8, 0.2),
}


# ─────────────────────────────────────────────────────────────────────
# Sensor Specifications
# ─────────────────────────────────────────────────────────────────────

# TEP-derived sensor specs (scaled from extracted statistics)
SENSOR_SPECS: dict[str, SensorSpec] = {
    # --- SCADA Sensors ---
    "pipeline_pressure": SensorSpec(
        "Pipeline Pressure", "kPa", 2705.0, 7.5,
        low_alarm=2650.0, high_alarm=2760.0, hihi_alarm=2800.0, noise_std=0.5),
    "tank_pressure": SensorSpec(
        "Storage Tank Pressure", "kPa", 2634.0, 7.9,
        low_alarm=2580.0, high_alarm=2690.0, hihi_alarm=2720.0, noise_std=0.5),
    "pump_outlet_pressure": SensorSpec(
        "Pump Outlet Pressure", "kPa", 3102.0, 6.5,
        low_alarm=3050.0, high_alarm=3160.0, hihi_alarm=3200.0, noise_std=0.4),
    "pipeline_temperature": SensorSpec(
        "Pipeline Temperature", "°C", 120.4, 0.02,
        low_alarm=118.0, high_alarm=123.0, hihi_alarm=125.0, noise_std=0.005),
    "tank_temperature": SensorSpec(
        "Tank Temperature", "°C", 80.1, 0.24,
        low_alarm=75.0, high_alarm=85.0, hihi_alarm=90.0, noise_std=0.02),
    "pipeline_flow": SensorSpec(
        "Pipeline Flow Rate", "m³/h", 42.3, 0.22,
        low_alarm=38.0, high_alarm=47.0, hihi_alarm=50.0, noise_std=0.02),
    "hydrocarbon_flow": SensorSpec(
        "Hydrocarbon Feed Flow", "m³/h", 0.25, 0.03,
        low_alarm=0.15, high_alarm=0.35, hihi_alarm=0.40, noise_std=0.002),
    "pump_flow": SensorSpec(
        "Pump Flow Rate", "m³/h", 22.95, 0.62,
        low_alarm=18.0, high_alarm=28.0, hihi_alarm=30.0, noise_std=0.05),
    "isolation_valve": SensorSpec(
        "Isolation Valve Position", "%", 24.6, 3.0,
        low_alarm=5.0, high_alarm=80.0, hihi_alarm=95.0, noise_std=0.1),
    "relief_valve": SensorSpec(
        "Relief Valve Position", "%", 40.1, 1.5,
        low_alarm=10.0, high_alarm=70.0, hihi_alarm=90.0, noise_std=0.1),
    "steam_valve": SensorSpec(
        "Steam Valve Position", "%", 48.0, 2.7,
        low_alarm=10.0, high_alarm=80.0, hihi_alarm=95.0, noise_std=0.1),
    "pump_speed": SensorSpec(
        "Pump Speed", "RPM", 41.1, 0.54,
        low_alarm=30.0, high_alarm=55.0, hihi_alarm=60.0, noise_std=0.05),
    "pump_power": SensorSpec(
        "Pump Power", "kW", 341.4, 1.65,
        low_alarm=300.0, high_alarm=380.0, hihi_alarm=400.0, noise_std=0.1),
    "pump_temperature": SensorSpec(
        "Pump Temperature", "°C", 65.8, 0.43,
        low_alarm=50.0, high_alarm=80.0, hihi_alarm=90.0, noise_std=0.03),
    # --- Gas Sensors (process-safety derived, not TEP-direct) ---
    "hc_gas_lel": SensorSpec(
        "Hydrocarbon Gas", "%LEL", 0.5, 0.3,
        low_alarm=0.0, high_alarm=10.0, hihi_alarm=20.0, noise_std=0.1),
    "h2s_ppm": SensorSpec(
        "Hydrogen Sulfide", "ppm", 0.2, 0.1,
        low_alarm=0.0, high_alarm=5.0, hihi_alarm=10.0, noise_std=0.05),
    "voc_ppm": SensorSpec(
        "Volatile Organic Compounds", "ppm", 1.0, 0.5,
        low_alarm=0.0, high_alarm=25.0, hihi_alarm=50.0, noise_std=0.1),
    "oxygen_pct": SensorSpec(
        "Oxygen Level", "%", 20.9, 0.1,
        low_alarm=19.5, high_alarm=23.5, hihi_alarm=25.0, noise_std=0.02),
}


# ─────────────────────────────────────────────────────────────────────
# Worker Roster
# ─────────────────────────────────────────────────────────────────────

WORKERS: list[WorkerProfile] = [
    # Day shift
    WorkerProfile("W001", "A. Kumar", "Operator", Shift.DAY,
                  ["hot_work", "confined_space", "electrical"]),
    WorkerProfile("W002", "B. Singh", "Operator", Shift.DAY,
                  ["hot_work", "line_breaking"]),
    WorkerProfile("W003", "C. Patel", "Technician", Shift.DAY,
                  ["electrical", "confined_space"]),
    WorkerProfile("W004", "D. Reddy", "Technician", Shift.DAY,
                  ["hot_work", "line_breaking", "confined_space"]),
    WorkerProfile("W005", "E. Sharma", "Supervisor", Shift.DAY,
                  ["hot_work", "confined_space", "electrical", "line_breaking"]),
    WorkerProfile("W006", "F. Gupta", "Safety Officer", Shift.DAY,
                  ["hot_work", "confined_space", "electrical", "line_breaking"]),
    # Night shift
    WorkerProfile("W007", "G. Rao", "Operator", Shift.NIGHT,
                  ["hot_work", "confined_space"]),
    WorkerProfile("W008", "H. Joshi", "Operator", Shift.NIGHT,
                  ["hot_work", "line_breaking"]),
    WorkerProfile("W009", "I. Mehta", "Technician", Shift.NIGHT,
                  ["electrical", "confined_space"]),
    WorkerProfile("W010", "J. Das", "Technician", Shift.NIGHT,
                  ["hot_work", "line_breaking", "electrical"]),
    WorkerProfile("W011", "K. Nair", "Supervisor", Shift.NIGHT,
                  ["hot_work", "confined_space", "electrical", "line_breaking"]),
    WorkerProfile("W012", "L. Iyer", "Safety Officer", Shift.NIGHT,
                  ["hot_work", "confined_space", "electrical", "line_breaking"]),
]


# ─────────────────────────────────────────────────────────────────────
# Simulation Parameters
# ─────────────────────────────────────────────────────────────────────

SIM_TIME_STEP = 1.0          # seconds per tick
SHIFT_DURATION = 43200       # 12 hours in seconds

# Scenario default durations (seconds)
SCENARIO_DURATIONS: dict[ScenarioID, int] = {
    ScenarioID.NORMAL:               100_000,
    ScenarioID.GAS_LEAK:              5_000,
    ScenarioID.VENTILATION_FAILURE:   5_000,
    ScenarioID.PUMP_FAILURE:          5_000,
    ScenarioID.HOT_WORK_GAS_LEAK:    5_000,
    ScenarioID.CONFINED_SPACE:        5_000,
    ScenarioID.EXPLOSION_RISK:        5_000,
}

# PPE compliance probabilities by task type
PPE_COMPLIANCE_RATES: dict[str, float] = {
    "routine_inspection": 0.95,
    "maintenance": 0.90,
    "emergency_response": 0.98,
    "hot_work": 0.92,
    "confined_space_entry": 0.88,
    "general": 0.93,
}

# Travel time between zones (seconds)
ZONE_TRAVEL_TIMES: dict[tuple[ZoneID, ZoneID], int] = {
    (ZoneID.ZONE_A, ZoneID.ZONE_B): 120,
    (ZoneID.ZONE_A, ZoneID.ZONE_C): 180,
    (ZoneID.ZONE_A, ZoneID.ZONE_D): 240,
    (ZoneID.ZONE_A, ZoneID.ZONE_E): 300,
    (ZoneID.ZONE_B, ZoneID.ZONE_C): 90,
    (ZoneID.ZONE_B, ZoneID.ZONE_D): 150,
    (ZoneID.ZONE_B, ZoneID.ZONE_E): 210,
    (ZoneID.ZONE_C, ZoneID.ZONE_D): 120,
    (ZoneID.ZONE_C, ZoneID.ZONE_E): 180,
    (ZoneID.ZONE_D, ZoneID.ZONE_E): 60,
}

# Make travel times symmetric
_symmetric = {}
for (z1, z2), t in ZONE_TRAVEL_TIMES.items():
    _symmetric[(z2, z1)] = t
ZONE_TRAVEL_TIMES.update(_symmetric)
del _symmetric

# Maximum exposure time in hazardous zone (seconds)
MAX_ZONE_EXPOSURE: dict[ZoneID, int] = {
    ZoneID.ZONE_A: 7200,    # 2 hours
    ZoneID.ZONE_B: 7200,
    ZoneID.ZONE_C: 3600,    # 1 hour
    ZoneID.ZONE_D: 3600,
    ZoneID.ZONE_E: 43200,   # Full shift
}
