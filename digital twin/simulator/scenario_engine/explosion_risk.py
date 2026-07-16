"""
Scenario 7: Compound Explosion Risk.

Maximum compound risk scenario — multiple simultaneous failures:
Pump seal failure → gas leak + ventilation failure + hot work active →
gas concentration reaches explosive range → ESD response.

Uses composite TEP faults (2+4+6) for maximum process disruption.
"""

from simulator.scenario_engine.base_scenario import BaseScenario, ScenarioPhase
from simulator.config import PermitType, ZoneID, EquipmentState


class ExplosionRiskScenario(BaseScenario):
    """Compound explosion risk with multiple simultaneous failures."""

    def __init__(self, duration: int = 5_000):
        super().__init__("explosion_risk", "Compound Explosion Risk", duration)
        self._explosion_probability: float = 0.0

    def _setup_phases(self) -> None:
        self.phases = [
            ScenarioPhase("normal_baseline", 0, 500,
                          "Normal operation, multiple work activities",
                          "normal"),
            ScenarioPhase("multiple_onset", 500, 500,
                          "Multiple systems begin degrading simultaneously",
                          "compound_onset"),
            ScenarioPhase("pump_seal_failure", 1000, 500,
                          "Pump seal fails, gas leak begins",
                          "compound_pump_leak"),
            ScenarioPhase("ventilation_failure", 1500, 500,
                          "Ventilation fails, gas cannot dissipate",
                          "compound_vent_failure"),
            ScenarioPhase("gas_in_explosive_range", 2000, 500,
                          "HC concentration enters explosive range",
                          "compound_explosive_range"),
            ScenarioPhase("hot_work_conflict", 2500, 500,
                          "Hot work ignition source detected — maximum risk",
                          "compound_maximum_risk"),
            ScenarioPhase("esd_activation", 3000, 500,
                          "Emergency Shutdown activated",
                          "compound_esd"),
            ScenarioPhase("emergency_response", 3500, 750,
                          "Full emergency response, fire team deployed",
                          "compound_emergency"),
            ScenarioPhase("stabilization", 4250, 750,
                          "Situation being brought under control",
                          "compound_stabilizing"),
        ]

    def apply(self, tick: int, plant) -> None:
        if tick < 500:
            # Setup: hot work permit active
            if tick == 0:
                permit = plant.permit_mgr.create_permit(
                    PermitType.HOT_WORK, ZoneID.ZONE_C.value,
                    "PMP-301", issuer="W005", holder="W004",
                    duration=7200, tick=tick)
                plant.permit_mgr.approve_permit(permit.permit_id, tick)
                plant.permit_mgr.activate_permit(permit.permit_id, tick + 1)
                plant.worker_events.force_worker_to_zone(
                    "W004", ZoneID.ZONE_C.value, "hot_work")
                plant.worker_events.force_worker_to_zone(
                    "W001", ZoneID.ZONE_B.value, "routine_inspection")
            return

        # Phase 2: Multiple onset (500-1000s)
        if 500 <= tick < 1000:
            intensity = self.sigmoid_ramp(tick, 500, 500, 0.0, 0.5)
            # Pump degradation
            pump = plant.equipment.get("PMP-301")
            if pump:
                pump.accelerate_bearing_wear(1 + intensity * 200)
                pump.accelerate_seal_wear(1 + intensity * 300)
            # Ventilation degradation
            vent = plant.equipment.get("VENT-301")
            if vent:
                vent.accelerate_degradation(1 + intensity * 200)
            # Composite TEP faults
            plant.process_model.inject_fault("2", intensity * 0.3)
            plant.process_model.inject_fault("4", intensity * 0.3)
            plant.process_model.inject_fault("6", intensity * 0.2)

        # Phase 3: Pump seal failure (1000-1500s)
        elif 1000 <= tick < 1500:
            intensity = self.sigmoid_ramp(tick, 1000, 500, 0.5, 1.0)
            pump = plant.equipment.get("PMP-301")
            if pump:
                pump.seal_health = max(0.0, 0.3 - intensity * 0.3)
                pump.seal_leak_rate = intensity * 0.002
            pipeline = plant.equipment.get("PL-201")
            if pipeline:
                pipeline.set_leak(intensity * 0.001)
            plant.process_model.inject_fault("2", 0.3 + intensity * 0.3)
            plant.process_model.inject_fault("4", 0.3 + intensity * 0.4)
            plant.process_model.inject_fault("6", 0.2 + intensity * 0.2)

        # Phase 4: Ventilation failure (1500-2000s)
        elif 1500 <= tick < 2000:
            intensity = self.sigmoid_ramp(tick, 1500, 500, 0.0, 1.0)
            vent = plant.equipment.get("VENT-301")
            if vent:
                vent.force_health(max(0.0, 0.3 - intensity * 0.3))
                if intensity > 0.8:
                    vent.force_state(EquipmentState.FAILED)
            # Leak continues
            pump = plant.equipment.get("PMP-301")
            if pump:
                pump.seal_leak_rate = 0.002
            pipeline = plant.equipment.get("PL-201")
            if pipeline:
                pipeline.set_leak(0.001)
            plant.process_model.inject_fault("2", 0.6)
            plant.process_model.inject_fault("4", 0.7)
            plant.process_model.inject_fault("6", 0.4 + intensity * 0.4)

        # Phase 5: Explosive range (2000-2500s)
        elif 2000 <= tick < 2500:
            # Gas at dangerous levels
            pump = plant.equipment.get("PMP-301")
            if pump:
                pump.seal_leak_rate = 0.003
            pipeline = plant.equipment.get("PL-201")
            if pipeline:
                pipeline.set_leak(0.0015)
            vent = plant.equipment.get("VENT-301")
            if vent:
                vent.force_state(EquipmentState.FAILED)
            plant.process_model.inject_fault("2", 0.8)
            plant.process_model.inject_fault("4", 0.9)
            plant.process_model.inject_fault("6", 0.8)
            # Explosion probability
            gas_conc = plant.gas_sensors._zone_hc.get(ZoneID.ZONE_C.value, 0.0)
            self._explosion_probability = min(0.95, gas_conc / 25.0)

        # Phase 6: Hot work conflict — maximum risk (2500-3000s)
        elif 2500 <= tick < 3000:
            pump = plant.equipment.get("PMP-301")
            if pump:
                pump.seal_leak_rate = 0.003
            pipeline = plant.equipment.get("PL-201")
            if pipeline:
                pipeline.set_leak(0.0015)
            plant.process_model.inject_fault("2", 1.0)
            plant.process_model.inject_fault("4", 1.0)
            plant.process_model.inject_fault("6", 1.0)
            self._explosion_probability = 0.95

        # Phase 7: ESD activation (3000-3500s)
        elif 3000 <= tick < 3500:
            if tick == 3000:
                plant.scada_sensors.trigger_esd(tick)
                # Stop all pumps
                for eq_id, eq in plant.equipment.items():
                    if eq_id.startswith("PMP"):
                        eq.force_state(EquipmentState.STOPPED)
                # Close all valves
                for eq_id, eq in plant.equipment.items():
                    if eq_id.startswith("VLV"):
                        eq.set_position(0.0)
                # Evacuate all hazardous zones
                for zone_id in [ZoneID.ZONE_A.value, ZoneID.ZONE_B.value,
                                ZoneID.ZONE_C.value]:
                    for wid in plant.worker_events.get_workers_in_zone(zone_id):
                        plant.worker_events.force_worker_to_zone(
                            wid, ZoneID.ZONE_E.value, "emergency_response")
            resolution = self.ramp(tick, 3000, 500, 0.0, 0.5)
            pump = plant.equipment.get("PMP-301")
            if pump:
                pump.seal_leak_rate = 0.003 * (1.0 - resolution)
                pump.force_state(EquipmentState.STOPPED)
            pipeline = plant.equipment.get("PL-201")
            if pipeline:
                pipeline.set_leak(0.0015 * (1.0 - resolution))
            self._explosion_probability *= (1.0 - resolution)

        # Phase 8: Emergency response (3500-4250s)
        elif 3500 <= tick < 4250:
            resolution = self.ramp(tick, 3500, 750, 0.0, 0.8)
            pump = plant.equipment.get("PMP-301")
            if pump:
                pump.seal_leak_rate = 0.001 * (1.0 - resolution)
            pipeline = plant.equipment.get("PL-201")
            if pipeline:
                pipeline.set_leak(0.0005 * (1.0 - resolution))
            plant.process_model.inject_fault("2", 1.0 * (1.0 - resolution))
            plant.process_model.inject_fault("4", 1.0 * (1.0 - resolution))
            plant.process_model.inject_fault("6", 1.0 * (1.0 - resolution))
            self._explosion_probability *= 0.99

        # Phase 9: Stabilization (4250-5000s)
        elif tick >= 4250:
            resolution = self.ramp(tick, 4250, 750, 0.0, 1.0)
            # Clear all leaks
            pump = plant.equipment.get("PMP-301")
            if pump:
                pump.seal_leak_rate = 0.0
            pipeline = plant.equipment.get("PL-201")
            if pipeline:
                pipeline.set_leak(0.0)
            plant.process_model.inject_fault("2", 0.2 * (1.0 - resolution))
            plant.process_model.inject_fault("4", 0.2 * (1.0 - resolution))
            plant.process_model.inject_fault("6", 0.2 * (1.0 - resolution))
            self._explosion_probability = 0.0
            # Partial ventilation recovery
            vent = plant.equipment.get("VENT-301")
            if vent:
                vent.force_health(resolution * 0.6)
                if resolution > 0.3:
                    vent.force_state(EquipmentState.RUNNING)
                    vent.boost()
