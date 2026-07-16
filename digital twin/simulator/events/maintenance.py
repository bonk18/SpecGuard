"""
Maintenance activity tracking.

Manages scheduled and reactive maintenance with equipment isolation,
technician assignment, and completion tracking.
"""

import numpy as np

from simulator.config import EquipmentState


class MaintenanceActivity:
    """Single maintenance activity."""
    __slots__ = ('activity_id', 'equipment_id', 'description',
                 'isolation_complete', 'technician', 'started_tick',
                 'expected_duration', 'completed', 'completed_tick')

    def __init__(self, activity_id: str, equipment_id: str,
                 description: str, technician: str,
                 expected_duration: int, started_tick: int):
        self.activity_id = activity_id
        self.equipment_id = equipment_id
        self.description = description
        self.isolation_complete = False
        self.technician = technician
        self.started_tick = started_tick
        self.expected_duration = expected_duration
        self.completed = False
        self.completed_tick = 0

    def to_dict(self, tick: int) -> dict:
        elapsed = tick - self.started_tick
        return {
            "activity_id": self.activity_id,
            "equipment_id": self.equipment_id,
            "description": self.description,
            "isolation_complete": self.isolation_complete,
            "technician": self.technician,
            "started_tick": self.started_tick,
            "expected_duration": self.expected_duration,
            "elapsed": elapsed,
            "remaining": max(0, self.expected_duration - elapsed),
            "completed": self.completed,
            "progress_pct": min(100.0, (elapsed / max(1, self.expected_duration)) * 100),
        }


class MaintenanceManager:
    """Manages maintenance activities across all equipment."""

    MAINTENANCE_DESCRIPTIONS = {
        "pump": [
            "Bearing replacement on {eq}",
            "Seal inspection and replacement on {eq}",
            "Vibration analysis on {eq}",
            "Lubrication service on {eq}",
            "Impeller inspection on {eq}",
        ],
        "valve": [
            "Packing replacement on {eq}",
            "Actuator calibration on {eq}",
            "Seat repair on {eq}",
            "Stroke testing on {eq}",
        ],
        "storage_tank": [
            "Internal inspection of {eq}",
            "Corrosion assessment on {eq}",
            "Level gauge calibration on {eq}",
            "Relief valve testing on {eq}",
        ],
        "pipeline": [
            "Ultrasonic thickness testing on {eq}",
            "Flange inspection on {eq}",
            "Corrosion coupon retrieval from {eq}",
            "Weld inspection on {eq}",
        ],
        "ventilation": [
            "Fan belt replacement on {eq}",
            "Motor inspection on {eq}",
            "Duct cleaning on {eq}",
            "Damper calibration on {eq}",
        ],
    }

    TECHNICIANS = ["W003", "W004", "W009", "W010"]

    def __init__(self, seed: int = 42):
        self._rng = np.random.default_rng(seed + 400)
        self.activities: dict[str, MaintenanceActivity] = {}
        self._next_id = 1
        self._scheduled_checks: dict[str, int] = {}  # equipment_id → next_check_tick

    def schedule_maintenance(self, equipment_id: str, equipment_type: str,
                              tick: int, description: str | None = None,
                              duration: int | None = None) -> MaintenanceActivity:
        """Schedule a maintenance activity."""
        aid = f"MA-{self._next_id:04d}"
        self._next_id += 1

        if description is None:
            templates = self.MAINTENANCE_DESCRIPTIONS.get(equipment_type, ["General maintenance on {eq}"])
            description = self._rng.choice(templates).format(eq=equipment_id)

        if duration is None:
            duration = int(self._rng.integers(1800, 7200))  # 30 min to 2 hours

        technician = self._rng.choice(self.TECHNICIANS)

        activity = MaintenanceActivity(
            aid, equipment_id, description, technician, duration, tick)
        self.activities[aid] = activity
        return activity

    def update(self, tick: int, equipment_states: dict[str, dict]) -> list[dict]:
        """Update maintenance activities.

        Args:
            tick: Current simulation tick
            equipment_states: Dict of equipment_id → state dict

        Returns:
            List of maintenance event dicts
        """
        events = []

        # Check for equipment needing reactive maintenance
        for eq_id, state in equipment_states.items():
            if state.get("needs_maintenance") and not self._has_active(eq_id):
                eq_type = eq_id.split("-")[0].lower()
                type_map = {"tk": "storage_tank", "pl": "pipeline",
                            "pmp": "pump", "vlv": "valve", "vent": "ventilation"}
                eq_type = type_map.get(eq_type, "general")
                activity = self.schedule_maintenance(eq_id, eq_type, tick)
                events.append({
                    "event": "maintenance_scheduled",
                    "activity": activity.to_dict(tick),
                })

        # Update active activities
        for aid, activity in list(self.activities.items()):
            if activity.completed:
                continue

            elapsed = tick - activity.started_tick

            # Isolation happens 300s after start
            if not activity.isolation_complete and elapsed > 300:
                activity.isolation_complete = True
                events.append({
                    "event": "isolation_complete",
                    "activity_id": aid,
                    "equipment_id": activity.equipment_id,
                })

            # Completion
            if elapsed >= activity.expected_duration:
                activity.completed = True
                activity.completed_tick = tick
                events.append({
                    "event": "maintenance_completed",
                    "activity_id": aid,
                    "equipment_id": activity.equipment_id,
                })

        return events

    def _has_active(self, equipment_id: str) -> bool:
        """Check if equipment has active maintenance."""
        return any(a.equipment_id == equipment_id and not a.completed
                   for a in self.activities.values())

    def get_active_activities(self, tick: int) -> list[dict]:
        """Return all active (uncompleted) maintenance activities."""
        return [a.to_dict(tick) for a in self.activities.values()
                if not a.completed]

    def get_current_state(self, tick: int) -> dict:
        """Return summarized maintenance state."""
        active = self.get_active_activities(tick)
        return {
            "active_count": len(active),
            "activities": active,
        }

    def reset(self, seed: int = 42) -> None:
        self._rng = np.random.default_rng(seed + 400)
        self.activities.clear()
        self._next_id = 1
        self._scheduled_checks.clear()
