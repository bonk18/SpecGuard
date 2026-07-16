"""
Scenario 4: Pump Failure.

Bearing wear progression → vibration increase → overheating →
seizure → flow rate decline → pressure instability → auto-shutdown.
"""

from simulator.scenario_engine.base_scenario import BaseScenario, ScenarioPhase
from simulator.config import EquipmentState, ZoneID


class PumpFailureScenario(BaseScenario):
    """Pump bearing failure with gradual degradation."""

    def __init__(self, duration: int = 5_000):
        super().__init__("pump_failure", "Pump Failure", duration)

    def _setup_phases(self) -> None:
        self.phases = [
            ScenarioPhase("normal_baseline", 0, 600,
                          "Normal operation", "normal"),
            ScenarioPhase("bearing_wear", 600, 800,
                          "Bearing wear begins, vibration slowly increases",
                          "pump_bearing_wear"),
            ScenarioPhase("vibration_increase", 1400, 600,
                          "Vibration exceeds normal threshold",
                          "pump_high_vibration"),
            ScenarioPhase("overheating", 2000, 600,
                          "Bearing overheating, temperature rising rapidly",
                          "pump_overheating"),
            ScenarioPhase("seizure", 2600, 400,
                          "Bearing seizes, pump trips",
                          "pump_tripped"),
            ScenarioPhase("switchover", 3000, 800,
                          "Switching to standby pump",
                          "pump_switchover"),
            ScenarioPhase("stabilization", 3800, 1200,
                          "System stabilizing with standby pump",
                          "pump_stabilizing"),
        ]

    def apply(self, tick: int, plant) -> None:
        if tick < 600:
            return

        pump_main = plant.equipment.get("PMP-301")
        pump_standby = plant.equipment.get("PMP-302")

        # Phase 2: Bearing wear (600-1400s)
        if 600 <= tick < 1400:
            intensity = self.sigmoid_ramp(tick, 600, 800, 0.0, 0.5)
            if pump_main:
                pump_main.accelerate_bearing_wear(1 + intensity * 200)
            # TEP Fault 1 (feed ratio step change analog)
            plant.process_model.inject_fault("1", intensity * 0.3)

        # Phase 3: High vibration (1400-2000s)
        elif 1400 <= tick < 2000:
            intensity = self.sigmoid_ramp(tick, 1400, 600, 0.5, 0.8)
            if pump_main:
                pump_main.accelerate_bearing_wear(1 + intensity * 500)
            plant.process_model.inject_fault("1", 0.3 + intensity * 0.3)
            # Generate maintenance alert
            if tick == 1400:
                plant.maintenance_mgr.schedule_maintenance(
                    "PMP-301", "pump", tick,
                    "Emergency bearing inspection on PMP-301 — high vibration alert",
                    duration=3600)

        # Phase 4: Overheating (2000-2600s)
        elif 2000 <= tick < 2600:
            intensity = self.sigmoid_ramp(tick, 2000, 600, 0.8, 1.0)
            if pump_main:
                pump_main.accelerate_bearing_wear(1 + 1000)
                pump_main.temperature = 65.8 + intensity * 40.0
            plant.process_model.inject_fault("1", 0.6 + intensity * 0.4)

        # Phase 5: Seizure (2600-3000s)
        elif 2600 <= tick < 3000:
            if pump_main:
                pump_main.force_state(EquipmentState.FAILED)
                pump_main.speed = 0.0
                pump_main.flow_rate = 0.0
                pump_main.power = 0.0
                # Temperature slowly cools
                pump_main.temperature = max(65.8,
                    pump_main.temperature * 0.999)
            plant.process_model.inject_fault("1", 1.0)
            # Pressure/flow disruption via equipment modifier
            plant.process_model.set_equipment_modifier("pump_speed", 0.1)
            plant.process_model.set_equipment_modifier("pump_flow", 0.1)

        # Phase 6: Switchover (3000-3800s)
        elif 3000 <= tick < 3800:
            switchover = self.ramp(tick, 3000, 800, 0.0, 1.0)
            if pump_standby:
                pump_standby.force_state(EquipmentState.RUNNING)
                pump_standby.set_speed(41.1 * switchover)
            plant.process_model.set_equipment_modifier(
                "pump_speed", 0.1 + switchover * 0.9)
            plant.process_model.set_equipment_modifier(
                "pump_flow", 0.1 + switchover * 0.9)
            plant.process_model.inject_fault("1", 1.0 * (1.0 - switchover * 0.7))

        # Phase 7: Stabilization (3800-5000s)
        elif tick >= 3800:
            stabilization = self.ramp(tick, 3800, 1200, 0.0, 1.0)
            if pump_standby:
                pump_standby.set_speed(41.1)
            plant.process_model.set_equipment_modifier("pump_speed", 1.0)
            plant.process_model.set_equipment_modifier("pump_flow", 1.0)
            plant.process_model.inject_fault("1", 0.3 * (1.0 - stabilization))
