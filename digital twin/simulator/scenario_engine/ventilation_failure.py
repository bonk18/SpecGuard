"""
Scenario 3: Ventilation Failure.

Fan motor degradation → speed reduction → failure →
gas accumulation → temperature rise → response.
"""

from simulator.scenario_engine.base_scenario import BaseScenario, ScenarioPhase
from simulator.config import EquipmentState, ZoneID


class VentilationFailureScenario(BaseScenario):
    """Ventilation system failure leading to gas accumulation."""

    def __init__(self, duration: int = 5_000):
        super().__init__("ventilation_failure", "Ventilation Failure", duration)

    def _setup_phases(self) -> None:
        self.phases = [
            ScenarioPhase("normal_baseline", 0, 800,
                          "Normal operation", "normal"),
            ScenarioPhase("motor_degradation", 800, 800,
                          "Ventilation motor begins degrading",
                          "ventilation_degrading"),
            ScenarioPhase("partial_failure", 1600, 600,
                          "Fan speed drops significantly",
                          "ventilation_partial_failure"),
            ScenarioPhase("complete_failure", 2200, 800,
                          "Ventilation fails completely, gas accumulates",
                          "ventilation_failed"),
            ScenarioPhase("gas_accumulation", 3000, 800,
                          "Gas levels rising in affected zone",
                          "gas_accumulating"),
            ScenarioPhase("response_recovery", 3800, 1200,
                          "Emergency response, backup ventilation activated",
                          "ventilation_recovery"),
        ]

    def apply(self, tick: int, plant) -> None:
        if tick < 800:
            return

        vent_a = plant.equipment.get("VENT-101")  # Zone A ventilation
        vent_c = plant.equipment.get("VENT-301")  # Zone C ventilation

        # Phase 2: Motor degradation (800-1600s)
        if 800 <= tick < 1600:
            intensity = self.sigmoid_ramp(tick, 800, 800, 0.0, 0.6)
            if vent_a:
                vent_a.accelerate_degradation(1 + intensity * 100)
                vent_a.set_speed(100.0 * (1.0 - intensity * 0.5))
            # TEP Fault 6 (feed loss → flow disruption analog)
            plant.process_model.inject_fault("6", intensity * 0.2)

        # Phase 3: Partial failure (1600-2200s)
        elif 1600 <= tick < 2200:
            intensity = self.sigmoid_ramp(tick, 1600, 600, 0.6, 0.9)
            if vent_a:
                vent_a.set_speed(100.0 * (1.0 - intensity))
                vent_a.force_health(1.0 - intensity)
            plant.process_model.inject_fault("6", 0.2 + intensity * 0.4)

        # Phase 4: Complete failure (2200-3000s)
        elif 2200 <= tick < 3000:
            if vent_a:
                vent_a.force_state(EquipmentState.FAILED)
                vent_a.force_health(0.0)
            plant.process_model.inject_fault("6", 0.7)
            # Workers in Zone A warned
            if tick == 2200:
                plant.worker_events.force_worker_to_zone(
                    "W002", ZoneID.ZONE_E.value, "emergency_response")

        # Phase 5: Gas accumulation (3000-3800s)
        elif 3000 <= tick < 3800:
            if vent_a:
                vent_a.force_state(EquipmentState.FAILED)
            plant.process_model.inject_fault("6", 0.8)
            # Evacuate Zone A
            if tick == 3000:
                for wid in plant.worker_events.get_workers_in_zone(ZoneID.ZONE_A.value):
                    plant.worker_events.force_worker_to_zone(
                        wid, ZoneID.ZONE_E.value, "emergency_response")

        # Phase 6: Recovery (3800-5000s)
        elif tick >= 3800:
            recovery = self.ramp(tick, 3800, 1200, 0.0, 1.0)
            if vent_a:
                vent_a.force_health(recovery * 0.8)
                if recovery > 0.3:
                    vent_a.force_state(EquipmentState.RUNNING)
                    vent_a.set_speed(recovery * 100.0)
            # Zone C vent boosted as backup
            if vent_c:
                vent_c.boost()
            plant.process_model.inject_fault("6", 0.8 * (1.0 - recovery))
