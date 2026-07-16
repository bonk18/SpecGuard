"""
Scenario 1: Normal Operation.

100,000 seconds of baseline operation with natural variability,
diurnal temperature cycles, shift changes, and minor random perturbations.
"""

from simulator.scenario_engine.base_scenario import BaseScenario, ScenarioPhase


class NormalScenario(BaseScenario):
    """Normal steady-state operation of the refinery unit."""

    def __init__(self, duration: int = 100_000):
        super().__init__("normal", "Normal Operation", duration)

    def _setup_phases(self) -> None:
        self.phases = [
            ScenarioPhase("steady_state", 0, self.total_duration,
                          "Normal steady-state operation with natural variability",
                          "normal"),
        ]

    def apply(self, tick: int, plant) -> None:
        # Normal operation: no special modifications needed
        # The process model's natural AR(1) dynamics and diurnal cycle
        # provide sufficient variability.
        pass
