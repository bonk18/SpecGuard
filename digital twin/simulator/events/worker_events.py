"""
Worker events generator.

Tracks worker movement between zones, task assignments, PPE compliance,
and time-in-zone exposure limits.
"""

import numpy as np

from simulator.config import (
    WORKERS, ZONES, ZoneID, Shift, WorkerProfile,
    ZONE_TRAVEL_TIMES, MAX_ZONE_EXPOSURE, PPE_COMPLIANCE_RATES,
)


class WorkerState:
    """State of a single worker."""
    __slots__ = ('worker_id', 'name', 'role', 'shift', 'current_zone',
                 'task', 'ppe_compliant', 'ppe_items', 'time_in_zone',
                 'is_traveling', 'travel_remaining', 'destination',
                 'is_on_shift')

    def __init__(self, profile: WorkerProfile):
        self.worker_id = profile.worker_id
        self.name = profile.name
        self.role = profile.role
        self.shift = profile.shift
        self.current_zone = ZoneID.ZONE_E.value  # Start in control room
        self.task = "standby"
        self.ppe_compliant = True
        self.ppe_items = {
            "hard_hat": True, "safety_glasses": True,
            "gloves": True, "steel_toe_boots": True,
            "gas_detector": True, "fire_resistant_clothing": True,
        }
        self.time_in_zone: int = 0
        self.is_traveling = False
        self.travel_remaining: int = 0
        self.destination: str | None = None
        self.is_on_shift = False


class WorkerEventGenerator:
    """Manages worker movement, tasks, and PPE tracking across zones."""

    TASKS = [
        "routine_inspection", "equipment_monitoring", "valve_operation",
        "sample_collection", "log_recording", "safety_check",
        "maintenance", "hot_work", "confined_space_entry",
        "emergency_response", "general",
    ]

    TASK_ZONES = {
        "routine_inspection": [ZoneID.ZONE_A, ZoneID.ZONE_B, ZoneID.ZONE_C],
        "equipment_monitoring": [ZoneID.ZONE_A, ZoneID.ZONE_B, ZoneID.ZONE_C],
        "valve_operation": [ZoneID.ZONE_A, ZoneID.ZONE_B],
        "sample_collection": [ZoneID.ZONE_A, ZoneID.ZONE_C],
        "log_recording": [ZoneID.ZONE_E],
        "safety_check": [ZoneID.ZONE_A, ZoneID.ZONE_B, ZoneID.ZONE_C, ZoneID.ZONE_D],
        "maintenance": [ZoneID.ZONE_C, ZoneID.ZONE_D],
        "hot_work": [ZoneID.ZONE_C, ZoneID.ZONE_D],
        "confined_space_entry": [ZoneID.ZONE_D],
        "emergency_response": [ZoneID.ZONE_A, ZoneID.ZONE_B, ZoneID.ZONE_C],
        "general": [ZoneID.ZONE_E],
    }

    def __init__(self, seed: int = 42):
        self._rng = np.random.default_rng(seed + 200)
        self.workers: dict[str, WorkerState] = {}
        for profile in WORKERS:
            self.workers[profile.worker_id] = WorkerState(profile)
        self._task_durations: dict[str, int] = {}  # worker_id → remaining ticks

    def update(self, tick: int, current_shift: Shift,
               emergency_zones: list[str] | None = None,
               scenario_overrides: dict | None = None) -> list[dict]:
        """Update all workers for one tick.

        Args:
            tick: Current simulation tick
            current_shift: Current shift (DAY/NIGHT)
            emergency_zones: Zones with active emergencies (workers evacuate)
            scenario_overrides: Dict of worker_id → forced assignments

        Returns:
            List of worker event dicts
        """
        events = []
        emergency_zones = emergency_zones or []
        scenario_overrides = scenario_overrides or {}

        for wid, ws in self.workers.items():
            # Check if worker is on shift
            ws.is_on_shift = (ws.shift == current_shift)
            if not ws.is_on_shift:
                ws.current_zone = "off_site"
                ws.task = "off_shift"
                ws.time_in_zone = 0
                continue

            # Handle scenario overrides
            if wid in scenario_overrides:
                override = scenario_overrides[wid]
                if "zone" in override:
                    target_zone = override["zone"]
                    if ws.current_zone != target_zone and not ws.is_traveling:
                        self._start_travel(ws, target_zone)
                if "task" in override:
                    ws.task = override["task"]
                if "ppe_compliant" in override:
                    ws.ppe_compliant = override["ppe_compliant"]

            # Handle traveling
            if ws.is_traveling:
                ws.travel_remaining -= 1
                if ws.travel_remaining <= 0:
                    ws.is_traveling = False
                    ws.current_zone = ws.destination
                    ws.destination = None
                    ws.time_in_zone = 0
                    # Set PPE compliance based on task
                    rate = PPE_COMPLIANCE_RATES.get(ws.task, 0.93)
                    ws.ppe_compliant = self._rng.random() < rate
                    if not ws.ppe_compliant:
                        # Randomly choose which PPE item is missing
                        items = list(ws.ppe_items.keys())
                        missing = self._rng.choice(items)
                        ws.ppe_items = {k: True for k in items}
                        ws.ppe_items[missing] = False
                    else:
                        ws.ppe_items = {k: True for k in ws.ppe_items}
                continue

            # Emergency evacuation
            if ws.current_zone in emergency_zones:
                self._start_travel(ws, ZoneID.ZONE_E.value)
                ws.task = "emergency_response"
                events.append(self._make_event(ws, tick, "emergency_evacuation"))
                continue

            # Increment time in zone
            ws.time_in_zone += 1

            # Check exposure limits
            zone_max = MAX_ZONE_EXPOSURE.get(
                ZoneID(ws.current_zone) if ws.current_zone.startswith("Zone") else ZoneID.ZONE_E,
                43200)
            if ws.time_in_zone >= zone_max:
                self._start_travel(ws, ZoneID.ZONE_E.value)
                ws.task = "mandatory_break"
                events.append(self._make_event(ws, tick, "exposure_limit_reached"))
                continue

            # Task assignment logic (stochastic)
            task_remaining = self._task_durations.get(wid, 0)
            if task_remaining > 0:
                self._task_durations[wid] = task_remaining - 1
            else:
                # Assign new task
                if self._rng.random() < 0.001:  # ~every 1000 seconds
                    task = str(self._rng.choice(self.TASKS[:8]))  # Normal tasks
                    zones = self.TASK_ZONES.get(task, [ZoneID.ZONE_E])
                    zone_values = [z.value for z in zones]
                    target_zone = str(self._rng.choice(zone_values))
                    duration = int(self._rng.integers(300, 3600))
                    ws.task = task
                    self._task_durations[wid] = duration
                    if ws.current_zone != target_zone:
                        self._start_travel(ws, target_zone)

        # Generate current state for all on-shift workers
        worker_events = []
        for wid, ws in self.workers.items():
            if ws.is_on_shift:
                worker_events.append(self._make_event(ws, tick))

        return worker_events

    def _start_travel(self, ws: WorkerState, destination: str) -> None:
        """Initiate travel between zones."""
        ws.is_traveling = True
        ws.destination = destination
        try:
            src = ZoneID(ws.current_zone) if ws.current_zone.startswith("Zone") else ZoneID.ZONE_E
            dst = ZoneID(destination)
            ws.travel_remaining = ZONE_TRAVEL_TIMES.get((src, dst), 60)
        except ValueError:
            ws.travel_remaining = 60

    def _make_event(self, ws: WorkerState, tick: int,
                    event_type: str = "position_update") -> dict:
        return {
            "worker_id": ws.worker_id,
            "worker_name": ws.name,
            "role": ws.role,
            "current_zone": ws.current_zone,
            "task": ws.task,
            "ppe_compliant": ws.ppe_compliant,
            "ppe_items": dict(ws.ppe_items),
            "time_in_zone": ws.time_in_zone,
            "is_traveling": ws.is_traveling,
            "event_type": event_type,
        }

    def get_workers_in_zone(self, zone_id: str) -> list[str]:
        """Return list of worker IDs currently in a zone."""
        return [wid for wid, ws in self.workers.items()
                if ws.current_zone == zone_id and ws.is_on_shift and not ws.is_traveling]

    def force_worker_to_zone(self, worker_id: str, zone_id: str,
                              task: str = "directed") -> None:
        """Force a worker to move to a specific zone (used by scenarios)."""
        ws = self.workers.get(worker_id)
        if ws and ws.is_on_shift:
            ws.task = task
            if ws.current_zone != zone_id:
                self._start_travel(ws, zone_id)
            else:
                ws.current_zone = zone_id

    def reset(self, seed: int = 42) -> None:
        self._rng = np.random.default_rng(seed + 200)
        for ws in self.workers.values():
            ws.current_zone = ZoneID.ZONE_E.value
            ws.task = "standby"
            ws.ppe_compliant = True
            ws.ppe_items = {k: True for k in ws.ppe_items}
            ws.time_in_zone = 0
            ws.is_traveling = False
            ws.is_on_shift = False
        self._task_durations.clear()
