"""
Plant orchestrator — master simulation loop.

Instantiates all modules, runs the tick-by-tick simulation loop,
manages inter-module dependencies, and collects output rows.
"""

from simulator.clock import SimulationClock
from simulator.config import (
    EQUIPMENT, EquipmentType, ZoneID, ZONES,
    EquipmentState, ScenarioID, SCENARIO_DURATIONS,
)

# Equipment models
from simulator.equipment.storage_tank import StorageTank
from simulator.equipment.pipeline import Pipeline
from simulator.equipment.pump import Pump
from simulator.equipment.valve import Valve
from simulator.equipment.ventilation import VentilationSystem

# Sensor models
from simulator.sensor_models.process_model import ProcessModel
from simulator.sensor_models.scada_sensors import SCADASensors
from simulator.sensor_models.gas_sensors import GasSensors

# Event generators
from simulator.events.worker_events import WorkerEventGenerator
from simulator.events.permit_to_work import PermitToWorkManager
from simulator.events.maintenance import MaintenanceManager
from simulator.events.shift_logs import ShiftLogGenerator
from simulator.events.cctv_events import CCTVEventGenerator

# Scenarios
from simulator.scenario_engine.base_scenario import BaseScenario
from simulator.scenario_engine.normal import NormalScenario
from simulator.scenario_engine.gas_leak import GasLeakScenario
from simulator.scenario_engine.ventilation_failure import VentilationFailureScenario
from simulator.scenario_engine.pump_failure import PumpFailureScenario
from simulator.scenario_engine.hot_work_gas_leak import HotWorkGasLeakScenario
from simulator.scenario_engine.confined_space import ConfinedSpaceScenario
from simulator.scenario_engine.explosion_risk import ExplosionRiskScenario


# Map scenario IDs to scenario classes
SCENARIO_CLASSES: dict[str, type[BaseScenario]] = {
    "normal": NormalScenario,
    "gas_leak": GasLeakScenario,
    "ventilation_failure": VentilationFailureScenario,
    "pump_failure": PumpFailureScenario,
    "hot_work_gas_leak": HotWorkGasLeakScenario,
    "confined_space": ConfinedSpaceScenario,
    "explosion_risk": ExplosionRiskScenario,
}


class Plant:
    """Master plant orchestrator.

    Each tick:
      1. Scenario engine modifies plant parameters
      2. Equipment models update
      3. Process model generates correlated sensor values
      4. SCADA/gas sensors apply noise and alarms
      5. Event generators produce worker/permit/maintenance/log/cctv events
      6. All data collected into a single output row
    """

    def __init__(self, seed: int = 42):
        self.seed = seed
        self.clock = SimulationClock()

        # Initialize equipment
        self.equipment: dict[str, object] = {}
        self._init_equipment()

        # Initialize sensor models
        self.process_model = ProcessModel()
        self.process_model.reset(seed)
        self.scada_sensors = SCADASensors(seed)
        self.gas_sensors = GasSensors(seed)

        # Initialize event generators
        self.worker_events = WorkerEventGenerator(seed)
        self.permit_mgr = PermitToWorkManager(seed)
        self.maintenance_mgr = MaintenanceManager(seed)
        self.shift_log_gen = ShiftLogGenerator(seed)
        self.cctv_gen = CCTVEventGenerator(seed)

        # Active scenario
        self.scenario: BaseScenario | None = None

    def _init_equipment(self) -> None:
        """Instantiate equipment objects from config."""
        type_map = {
            EquipmentType.STORAGE_TANK: StorageTank,
            EquipmentType.PIPELINE: Pipeline,
            EquipmentType.PUMP: Pump,
            EquipmentType.VALVE: Valve,
            EquipmentType.VENTILATION: VentilationSystem,
        }
        for eq_id, cfg in EQUIPMENT.items():
            cls = type_map.get(cfg.equipment_type)
            if cls:
                self.equipment[eq_id] = cls(cfg)

    def reset(self, seed: int | None = None) -> None:
        """Reset all modules to initial state."""
        if seed is not None:
            self.seed = seed
        self.clock = SimulationClock()
        self.equipment.clear()
        self._init_equipment()
        self.process_model.reset(self.seed)
        self.scada_sensors.reset(self.seed)
        self.gas_sensors.reset(self.seed)
        self.worker_events.reset(self.seed)
        self.permit_mgr.reset(self.seed)
        self.maintenance_mgr.reset(self.seed)
        self.shift_log_gen.reset(self.seed)
        self.cctv_gen.reset(self.seed)
        self.scenario = None

    def set_scenario(self, scenario: BaseScenario) -> None:
        """Set the active scenario."""
        self.scenario = scenario

    def tick(self) -> dict:
        """Execute one simulation tick and return the output row."""
        t = self.clock.tick

        # 1. Apply scenario effects
        if self.scenario:
            self.scenario.apply(t, self)

        # 2. Update all equipment
        equipment_states = {}
        for eq_id, eq in self.equipment.items():
            eq.update(t)
            equipment_states[eq_id] = eq.get_state_dict()

        # 3. Couple equipment state to process model
        self._apply_equipment_coupling()

        # 4. Generate process model values
        process_values = self.process_model.step(
            diurnal_factor=self.clock.time_of_day_factor)

        # 5. Calculate aggregate values for sensors
        vent_effectiveness = self._get_ventilation_effectiveness()

        # 6. Generate SCADA sensor readings
        scada = self.scada_sensors.generate(
            process_values, equipment_states,
            ventilation_status=vent_effectiveness, tick=t)

        # 7. Collect leak rates per zone
        zone_leaks = self._get_zone_leaks()

        # 8. Generate gas sensor readings (for primary zone)
        primary_zone = ZoneID.ZONE_C.value  # Pump station = most active
        gas = self.gas_sensors.generate(
            primary_zone, zone_leaks.get(primary_zone, {}),
            ventilation_effectiveness=vent_effectiveness,
            temperature=process_values.get("pump_temperature", 35.0),
            tick=t)

        # Also update other zones (for cross-zone effects)
        for zone_id in [ZoneID.ZONE_A.value, ZoneID.ZONE_B.value, ZoneID.ZONE_D.value]:
            zone_vent = self._get_zone_ventilation(zone_id)
            self.gas_sensors.generate(
                zone_id, zone_leaks.get(zone_id, {}),
                ventilation_effectiveness=zone_vent,
                tick=t)

        # 9. Worker events
        emergency_zones = self._get_emergency_zones(gas)
        workers = self.worker_events.update(
            t, self.clock.current_shift, emergency_zones)

        # 10. Permit-to-work updates
        zone_hc = {z: self.gas_sensors._zone_hc.get(z, 0.0)
                    for z in [ZoneID.ZONE_A.value, ZoneID.ZONE_B.value,
                              ZoneID.ZONE_C.value, ZoneID.ZONE_D.value]}
        permit_events = self.permit_mgr.update(t, zone_hc)
        permit_state = self.permit_mgr.get_current_state(t)

        # 11. Maintenance updates
        maint_events = self.maintenance_mgr.update(t, equipment_states)
        maint_state = self.maintenance_mgr.get_current_state(t)

        # 12. Shift log generation
        plant_state_for_log = {
            "equipment": equipment_states,
            "scada": scada,
        }
        alarms = self.scada_sensors.get_active_alarms()
        gas_readings_for_log = {primary_zone: gas}
        shift_log = self.shift_log_gen.generate(
            t, plant_state_for_log, alarms, gas_readings_for_log, maint_state)

        # 13. CCTV events
        hc_concentrations = self.gas_sensors._zone_hc
        cctv_events = self.cctv_gen.generate(t, workers, zone_hc, hc_concentrations)

        # 14. Assemble output row
        row = self._assemble_row(
            t, process_values, scada, gas, equipment_states,
            workers, permit_state, maint_state, shift_log, cctv_events)

        # 15. Advance clock
        self.clock.advance()

        return row

    def _apply_equipment_coupling(self) -> None:
        """Couple equipment state to process model variables."""
        # Pump speed → process model
        pump = self.equipment.get("PMP-301")
        if pump and hasattr(pump, 'speed'):
            if pump.state == EquipmentState.FAILED:
                self.process_model.set_equipment_modifier("pump_speed", 0.0)
                self.process_model.set_equipment_modifier("pump_flow", 0.0)
                self.process_model.set_equipment_modifier("pump_power", 0.0)
            elif pump.state == EquipmentState.STOPPED:
                self.process_model.set_equipment_modifier("pump_speed", 0.0)
                self.process_model.set_equipment_modifier("pump_flow", 0.0)
                self.process_model.set_equipment_modifier("pump_power", 0.0)
            else:
                speed_ratio = pump.speed / 41.1 if pump.speed > 0 else 1.0
                self.process_model.set_equipment_modifier("pump_speed", speed_ratio)

        # Valve positions → process model
        valve = self.equipment.get("VLV-201")
        if valve and hasattr(valve, 'position'):
            self.process_model.set_equipment_modifier(
                "isolation_valve", valve.position / 24.6 if valve.position > 0 else 1.0)

    def _get_ventilation_effectiveness(self) -> float:
        """Calculate overall ventilation effectiveness."""
        vent_equip = [eq for eq_id, eq in self.equipment.items()
                      if eq_id.startswith("VENT")]
        if not vent_equip:
            return 1.0
        return sum(eq.airflow for eq in vent_equip) / len(vent_equip)

    def _get_zone_ventilation(self, zone_id: str) -> float:
        """Get ventilation effectiveness for a specific zone."""
        zone_cfg = ZONES.get(ZoneID(zone_id) if zone_id.startswith("Zone") else None)
        if zone_cfg is None:
            return 1.0
        vent_ids = [eid for eid in zone_cfg.equipment_ids if eid.startswith("VENT")]
        if not vent_ids:
            return 0.8  # Zones without dedicated ventilation
        total = 0.0
        for vid in vent_ids:
            eq = self.equipment.get(vid)
            if eq and hasattr(eq, 'airflow'):
                total += eq.airflow
        return total / len(vent_ids) if vent_ids else 0.8

    def _get_zone_leaks(self) -> dict[str, dict[str, float]]:
        """Collect leak rates per zone."""
        zone_leaks: dict[str, dict[str, float]] = {}
        for eq_id, eq in self.equipment.items():
            cfg = EQUIPMENT.get(eq_id)
            if cfg is None:
                continue
            zone = cfg.zone_id.value
            leak_rate = 0.0
            if hasattr(eq, 'leak_rate'):
                leak_rate = eq.leak_rate
            if hasattr(eq, 'seal_leak_rate'):
                leak_rate += eq.seal_leak_rate
            if leak_rate > 0:
                zone_leaks.setdefault(zone, {})[eq_id] = leak_rate
        return zone_leaks

    def _get_emergency_zones(self, gas: dict) -> list[str]:
        """Determine zones with emergency conditions."""
        zones = []
        if gas.get("hc_gas_lel", 0) > 20.0:
            zones.append(gas.get("zone_id", ""))
        if gas.get("oxygen_pct", 20.9) < 19.0:
            zones.append(gas.get("zone_id", ""))
        if gas.get("h2s_ppm", 0) > 10.0:
            zones.append(gas.get("zone_id", ""))
        return list(set(zones))

    def _assemble_row(self, tick: int, process_values: dict,
                      scada: dict, gas: dict,
                      equipment_states: dict,
                      workers: list[dict], permit_state: dict,
                      maint_state: dict, shift_log: dict | None,
                      cctv_events: list[dict]) -> dict:
        """Assemble all data into a flat output row."""
        row = {
            "timestamp": self.clock.timestamp,
            "tick": tick,
            "scenario_id": self.scenario.scenario_id if self.scenario else "normal",
            "event_label": self.scenario.get_label(tick) if self.scenario else "normal",
        }

        # SCADA sensors
        for key in ["pipeline_pressure", "tank_pressure", "pump_outlet_pressure",
                     "pipeline_temperature", "tank_temperature",
                     "pipeline_flow", "hydrocarbon_flow", "pump_flow",
                     "isolation_valve", "relief_valve", "steam_valve",
                     "pump_speed", "pump_power", "pump_temperature",
                     "ventilation_status", "esd_active"]:
            row[key] = scada.get(key)

        # Gas sensors
        for key in ["hc_gas_lel", "h2s_ppm", "voc_ppm", "oxygen_pct",
                     "hc_gas_lel_alarm", "h2s_ppm_alarm", "voc_ppm_alarm",
                     "oxygen_alarm"]:
            row[key] = gas.get(key)
        row["gas_zone_id"] = gas.get("zone_id")

        # Equipment state (aggregated)
        pump_301 = equipment_states.get("PMP-301", {})
        pump_302 = equipment_states.get("PMP-302", {})
        row["pump_running"] = pump_301.get("state") == "running" or \
                              pump_302.get("state") == "running"
        row["pump_failed"] = pump_301.get("state") == "failed"
        row["valve_failed"] = any(
            s.get("state") == "failed" for eid, s in equipment_states.items()
            if eid.startswith("VLV"))
        row["ventilation_failed"] = any(
            s.get("state") == "failed" for eid, s in equipment_states.items()
            if eid.startswith("VENT"))
        row["bearing_wear"] = round(1.0 - pump_301.get("health", 1.0), 4)
        row["maintenance_required"] = any(
            s.get("needs_maintenance") for s in equipment_states.values())

        # Worker data (first on-shift worker for flat row; full list in JSON)
        if workers:
            w = workers[0]
            row["worker_id"] = w.get("worker_id")
            row["worker_zone"] = w.get("current_zone")
            row["worker_task"] = w.get("task")
            row["ppe_compliant"] = w.get("ppe_compliant")
            row["time_in_zone"] = w.get("time_in_zone")
        else:
            row["worker_id"] = None
            row["worker_zone"] = None
            row["worker_task"] = None
            row["ppe_compliant"] = None
            row["time_in_zone"] = None

        # Permit state
        row["hot_work_active"] = permit_state.get("hot_work_active", False)
        row["confined_space_active"] = permit_state.get("confined_space_active", False)
        row["electrical_active"] = permit_state.get("electrical_active", False)
        row["line_breaking_active"] = permit_state.get("line_breaking_active", False)

        # Maintenance (first active activity)
        activities = maint_state.get("activities", [])
        if activities:
            a = activities[0]
            row["maintenance_equipment"] = a.get("equipment_id")
            row["isolation_complete"] = a.get("isolation_complete")
            row["maintenance_technician"] = a.get("technician")
            row["maintenance_remaining"] = a.get("remaining")
        else:
            row["maintenance_equipment"] = None
            row["isolation_complete"] = None
            row["maintenance_technician"] = None
            row["maintenance_remaining"] = None

        # Shift log
        if shift_log:
            row["log_severity"] = shift_log.get("severity")
            row["log_message"] = shift_log.get("message")
            row["log_operator"] = shift_log.get("operator")
        else:
            row["log_severity"] = None
            row["log_message"] = None
            row["log_operator"] = None

        # CCTV events (first event for flat row)
        if cctv_events:
            ev = cctv_events[0]
            row["cctv_camera_id"] = ev.get("camera_id")
            row["cctv_zone_id"] = ev.get("zone_id")
            row["cctv_event_type"] = ev.get("event_type")
            row["cctv_description"] = ev.get("description")
            row["cctv_confidence"] = ev.get("confidence")
        else:
            row["cctv_camera_id"] = None
            row["cctv_zone_id"] = None
            row["cctv_event_type"] = None
            row["cctv_description"] = None
            row["cctv_confidence"] = None

        return row
