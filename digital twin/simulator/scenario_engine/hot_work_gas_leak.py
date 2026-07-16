"""
Scenario 5: Hot Work During Gas Leak.

Compound scenario: Gas leak develops while hot work permit is active.
Ignition probability calculated from HC concentration + ignition source proximity.
"""

from simulator.scenario_engine.base_scenario import BaseScenario, ScenarioPhase
from simulator.config import PermitType, ZoneID, EquipmentState


class HotWorkGasLeakScenario(BaseScenario):
    """Compound scenario — gas leak develops during active hot work."""

    def __init__(self, duration: int = 5_000):
        super().__init__("hot_work_gas_leak", "Hot Work During Gas Leak", duration)
        self._hot_work_permit_id: str | None = None
        self._ignition_probability: float = 0.0

    def _setup_phases(self) -> None:
        self.phases = [
            ScenarioPhase("normal_with_permit", 0, 800,
                          "Hot work permit issued and active in Zone C",
                          "normal_hot_work"),
            ScenarioPhase("leak_onset", 800, 600,
                          "Undetected gas leak begins nearby",
                          "hot_work_leak_onset"),
            ScenarioPhase("gas_rising", 1400, 600,
                          "HC concentration rising in hot work zone",
                          "hot_work_gas_rising"),
            ScenarioPhase("gas_detected", 2000, 400,
                          "Gas alarm triggers, conflict with hot work permit",
                          "hot_work_gas_detected"),
            ScenarioPhase("permit_suspended", 2400, 600,
                          "Hot work suspended, area evacuation initiated",
                          "hot_work_suspended"),
            ScenarioPhase("emergency_response", 3000, 1000,
                          "Full emergency response, leak isolation",
                          "hot_work_emergency"),
            ScenarioPhase("resolution", 4000, 1000,
                          "Leak secured, area made safe",
                          "hot_work_resolved"),
        ]

    def apply(self, tick: int, plant) -> None:
        # Phase 1: Normal with active hot work permit (0-800s)
        if tick < 800:
            # Create hot work permit at start
            if tick == 0:
                permit = plant.permit_mgr.create_permit(
                    PermitType.HOT_WORK, ZoneID.ZONE_C.value,
                    "PMP-301", issuer="W005", holder="W004",
                    duration=7200, tick=tick)
                self._hot_work_permit_id = permit.permit_id
                plant.permit_mgr.approve_permit(permit.permit_id, tick)
                plant.permit_mgr.activate_permit(permit.permit_id, tick + 1)
                # Send worker for hot work
                plant.worker_events.force_worker_to_zone(
                    "W004", ZoneID.ZONE_C.value, "hot_work")
            return

        # Phase 2: Leak onset (800-1400s)
        if 800 <= tick < 1400:
            intensity = self.sigmoid_ramp(tick, 800, 600, 0.0, 0.6)
            pipeline = plant.equipment.get("PL-201")
            if pipeline:
                pipeline.set_leak(intensity * 0.0008)
            # TEP Fault 5 (condenser cooling anomaly — compound analog)
            plant.process_model.inject_fault("5", intensity * 0.4)

        # Phase 3: Gas rising (1400-2000s)
        elif 1400 <= tick < 2000:
            intensity = self.sigmoid_ramp(tick, 1400, 600, 0.6, 1.0)
            pipeline = plant.equipment.get("PL-201")
            if pipeline:
                pipeline.set_leak(0.0008 + intensity * 0.0004)
            plant.process_model.inject_fault("5", 0.4 + intensity * 0.4)

            # Calculate ignition probability
            gas_conc = plant.gas_sensors._zone_hc.get(ZoneID.ZONE_C.value, 0.0)
            hot_work_active = plant.permit_mgr.has_active_permit(
                PermitType.HOT_WORK, ZoneID.ZONE_C.value)
            if hot_work_active and gas_conc > 5.0:
                self._ignition_probability = min(0.8,
                    (gas_conc - 5.0) / 20.0 * 0.5)

        # Phase 4: Gas detected (2000-2400s)
        elif 2000 <= tick < 2400:
            pipeline = plant.equipment.get("PL-201")
            if pipeline:
                pipeline.set_leak(0.0012)
            plant.process_model.inject_fault("5", 0.8)

            # Permit conflict should be auto-detected by PTW manager
            # Force suspension if not already handled
            if tick == 2100 and self._hot_work_permit_id:
                plant.permit_mgr.suspend_permit(self._hot_work_permit_id)

        # Phase 5: Permit suspended, evacuation (2400-3000s)
        elif 2400 <= tick < 3000:
            # Evacuate Zone C workers
            if tick == 2400:
                for wid in plant.worker_events.get_workers_in_zone(ZoneID.ZONE_C.value):
                    plant.worker_events.force_worker_to_zone(
                        wid, ZoneID.ZONE_E.value, "emergency_response")
            resolution = self.ramp(tick, 2400, 600, 0.0, 0.5)
            pipeline = plant.equipment.get("PL-201")
            if pipeline:
                pipeline.set_leak(0.0012 * (1.0 - resolution))
            plant.process_model.inject_fault("5", 0.8)

        # Phase 6: Emergency response (3000-4000s)
        elif 3000 <= tick < 4000:
            resolution = self.ramp(tick, 3000, 1000, 0.0, 1.0)
            pipeline = plant.equipment.get("PL-201")
            if pipeline:
                pipeline.set_leak(0.0006 * (1.0 - resolution))
            # Boost ventilation
            vent = plant.equipment.get("VENT-301")
            if vent:
                vent.boost()
            # Close isolation valve
            valve = plant.equipment.get("VLV-301")
            if valve:
                valve.set_position(100.0 * (1.0 - resolution))
            plant.process_model.inject_fault("5", 0.8 * (1.0 - resolution))

        # Phase 7: Resolution (4000-5000s)
        elif tick >= 4000:
            resolution = self.ramp(tick, 4000, 1000, 0.0, 1.0)
            pipeline = plant.equipment.get("PL-201")
            if pipeline:
                pipeline.set_leak(0.0)
            plant.process_model.inject_fault("5", 0.1 * (1.0 - resolution))
            self._ignition_probability = 0.0
