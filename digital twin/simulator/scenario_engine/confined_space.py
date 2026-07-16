"""
Scenario 6: Confined Space Incident.

O2 depletion in confined space → worker entry with/without gas test →
exposure symptoms → rescue scenario.
"""

from simulator.scenario_engine.base_scenario import BaseScenario, ScenarioPhase
from simulator.config import PermitType, ZoneID, EquipmentState


class ConfinedSpaceScenario(BaseScenario):
    """Confined space incident with oxygen depletion and rescue."""

    def __init__(self, duration: int = 5_000):
        super().__init__("confined_space", "Confined Space Incident", duration)

    def _setup_phases(self) -> None:
        self.phases = [
            ScenarioPhase("normal_baseline", 0, 600,
                          "Normal operation, confined space entry being planned",
                          "normal"),
            ScenarioPhase("permit_issued", 600, 400,
                          "Confined space permit issued, gas test pending",
                          "confined_space_permit"),
            ScenarioPhase("atmosphere_degrading", 1000, 800,
                          "O2 levels slowly dropping in confined space",
                          "confined_space_o2_dropping"),
            ScenarioPhase("entry_without_test", 1800, 600,
                          "Worker enters without completing gas test",
                          "confined_space_entry"),
            ScenarioPhase("exposure", 2400, 600,
                          "Worker experiences symptoms, O2 alarm triggers",
                          "confined_space_exposure"),
            ScenarioPhase("rescue", 3000, 1000,
                          "Rescue team deployed, worker extracted",
                          "confined_space_rescue"),
            ScenarioPhase("aftermath", 4000, 1000,
                          "Area secured, investigation initiated",
                          "confined_space_aftermath"),
        ]

    def apply(self, tick: int, plant) -> None:
        if tick < 600:
            return

        # Phase 2: Permit issued (600-1000s)
        if 600 <= tick < 1000:
            if tick == 600:
                plant.permit_mgr.create_permit(
                    PermitType.CONFINED_SPACE, ZoneID.ZONE_D.value,
                    "VENT-401", issuer="W005", holder="W003",
                    duration=3600, tick=tick)

        # Phase 3: Atmosphere degrading (1000-1800s)
        elif 1000 <= tick < 1800:
            intensity = self.sigmoid_ramp(tick, 1000, 800, 0.0, 0.7)
            # Ventilation in Zone D is insufficient
            vent = plant.equipment.get("VENT-401")
            if vent:
                vent.set_speed(100.0 * (1.0 - intensity * 0.8))
            # TEP Fault 7 + 14 composite
            plant.process_model.inject_fault("7", intensity * 0.3)
            plant.process_model.inject_fault("14", intensity * 0.2)

        # Phase 4: Entry without proper gas test (1800-2400s)
        elif 1800 <= tick < 2400:
            if tick == 1800:
                plant.worker_events.force_worker_to_zone(
                    "W003", ZoneID.ZONE_D.value, "confined_space_entry")
            vent = plant.equipment.get("VENT-401")
            if vent:
                vent.set_speed(20.0)  # Very low ventilation
            plant.process_model.inject_fault("7", 0.5)
            plant.process_model.inject_fault("14", 0.3)

        # Phase 5: Exposure (2400-3000s)
        elif 2400 <= tick < 3000:
            intensity = self.sigmoid_ramp(tick, 2400, 600, 0.0, 1.0)
            vent = plant.equipment.get("VENT-401")
            if vent:
                vent.force_health(0.1)
                vent.set_speed(5.0)  # Almost no ventilation
            plant.process_model.inject_fault("7", 0.5 + intensity * 0.3)
            plant.process_model.inject_fault("14", 0.3 + intensity * 0.3)

        # Phase 6: Rescue (3000-4000s)
        elif 3000 <= tick < 4000:
            rescue_progress = self.ramp(tick, 3000, 1000, 0.0, 1.0)
            if tick == 3000:
                # Rescue team sent in
                plant.worker_events.force_worker_to_zone(
                    "W004", ZoneID.ZONE_D.value, "emergency_response")
                plant.worker_events.force_worker_to_zone(
                    "W001", ZoneID.ZONE_D.value, "emergency_response")
            # Restore ventilation
            vent = plant.equipment.get("VENT-401")
            if vent:
                vent.force_health(0.3 + rescue_progress * 0.7)
                vent.set_speed(rescue_progress * 100.0)
            plant.process_model.inject_fault("7", 0.8 * (1.0 - rescue_progress))
            plant.process_model.inject_fault("14", 0.6 * (1.0 - rescue_progress))
            # Extract worker at 50% progress
            if tick == 3500:
                plant.worker_events.force_worker_to_zone(
                    "W003", ZoneID.ZONE_E.value, "medical_attention")

        # Phase 7: Aftermath (4000-5000s)
        elif tick >= 4000:
            resolution = self.ramp(tick, 4000, 1000, 0.0, 1.0)
            vent = plant.equipment.get("VENT-401")
            if vent:
                vent.boost()
            plant.process_model.inject_fault("7", 0.1 * (1.0 - resolution))
            plant.process_model.inject_fault("14", 0.05 * (1.0 - resolution))
