"""
Scenario 2: Small Gas Leak.

Pump seal degradation → small leak → HC concentration rise →
gas alarm → worker response → isolation → ventilation boost → resolution.
"""

from simulator.scenario_engine.base_scenario import BaseScenario, ScenarioPhase
from simulator.config import EquipmentState, ZoneID, PermitType


class GasLeakScenario(BaseScenario):
    """Small gas leak developing from pump seal degradation."""

    def __init__(self, duration: int = 5_000):
        super().__init__("gas_leak", "Small Gas Leak", duration)

    def _setup_phases(self) -> None:
        self.phases = [
            ScenarioPhase("normal_baseline", 0, 600,
                          "Normal operation before fault onset",
                          "normal"),
            ScenarioPhase("seal_degradation", 600, 600,
                          "Pump seal begins degrading, minor vibration increase",
                          "incipient_fault"),
            ScenarioPhase("leak_onset", 1200, 600,
                          "Small leak develops, HC concentration slowly rises",
                          "gas_leak_developing"),
            ScenarioPhase("gas_detection", 1800, 600,
                          "Gas alarm triggers, control room alerted",
                          "gas_leak_detected"),
            ScenarioPhase("emergency_response", 2400, 1200,
                          "Workers respond, area isolated, ventilation boosted",
                          "gas_leak_response"),
            ScenarioPhase("resolution", 3600, 1400,
                          "Leak contained, readings normalizing",
                          "gas_leak_resolving"),
        ]

    def apply(self, tick: int, plant) -> None:
        # Phase 1: Normal baseline (0-600s)
        if tick < 600:
            return

        # Phase 2: Seal degradation (600-1200s)
        if 600 <= tick < 1200:
            # Gradually increase pump seal wear
            intensity = self.sigmoid_ramp(tick, 600, 600, 0.0, 0.5)
            pump = plant.equipment.get("PMP-301")
            if pump:
                pump.accelerate_seal_wear(1 + intensity * 50)
                # Inject TEP fault signature (Fault 4 — cooling/seal anomaly)
                plant.process_model.inject_fault("4", intensity * 0.3)

        # Phase 3: Leak onset (1200-1800s)
        elif 1200 <= tick < 1800:
            intensity = self.sigmoid_ramp(tick, 1200, 600, 0.0, 1.0)
            pump = plant.equipment.get("PMP-301")
            if pump:
                pump.seal_leak_rate = intensity * 0.001  # Growing leak
            # Pipeline leak develops
            pipeline = plant.equipment.get("PL-201")
            if pipeline:
                pipeline.set_leak(intensity * 0.0005)
            # TEP fault intensifies
            plant.process_model.inject_fault("4", 0.3 + intensity * 0.5)

        # Phase 4: Gas detection (1800-2400s)
        elif 1800 <= tick < 2400:
            # Leak at full small-leak rate
            pump = plant.equipment.get("PMP-301")
            if pump:
                pump.seal_leak_rate = 0.001
            pipeline = plant.equipment.get("PL-201")
            if pipeline:
                pipeline.set_leak(0.0005)
            plant.process_model.inject_fault("4", 0.8)

            # Workers alerted — send operator to investigate
            if tick == 1800:
                plant.worker_events.force_worker_to_zone(
                    "W001", ZoneID.ZONE_C.value, "emergency_response")

        # Phase 5: Emergency response (2400-3600s)
        elif 2400 <= tick < 3600:
            resolution = self.ramp(tick, 2400, 1200, 0.0, 1.0)
            # Gradually close isolation valve
            valve = plant.equipment.get("VLV-301")
            if valve:
                valve.set_position(100.0 * (1.0 - resolution))
            # Reduce leak as isolation takes effect
            pump = plant.equipment.get("PMP-301")
            if pump:
                pump.seal_leak_rate = 0.001 * (1.0 - resolution)
            pipeline = plant.equipment.get("PL-201")
            if pipeline:
                pipeline.set_leak(0.0005 * (1.0 - resolution))
            # Boost ventilation
            vent = plant.equipment.get("VENT-301")
            if vent:
                vent.boost()
            # Fault resolving
            plant.process_model.inject_fault("4", 0.8 * (1.0 - resolution))

        # Phase 6: Resolution (3600-5000s)
        elif tick >= 3600:
            # Clean up — leak stopped, readings normalizing
            pump = plant.equipment.get("PMP-301")
            if pump:
                pump.seal_leak_rate = 0.0
                pump.force_state(EquipmentState.STOPPED)
            pipeline = plant.equipment.get("PL-201")
            if pipeline:
                pipeline.set_leak(0.0)
            resolution = self.ramp(tick, 3600, 1400, 0.0, 1.0)
            plant.process_model.inject_fault("4", 0.1 * (1.0 - resolution))
