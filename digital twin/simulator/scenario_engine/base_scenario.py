"""
Abstract base class for all scenarios.

Scenarios evolve through phases over time, modifying equipment state,
sensor outputs, worker assignments, and permit conditions.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class ScenarioPhase:
    """A single phase of a scenario's evolution."""
    name: str
    start_tick: int            # Tick when this phase begins
    duration: int              # Duration in ticks (seconds)
    description: str
    label: str                 # Event label for this phase


class BaseScenario(ABC):
    """Abstract base for all scenario types.

    Subclasses define phases and implement apply() to modify plant state
    at each tick.
    """

    def __init__(self, scenario_id: str, name: str, total_duration: int):
        self.scenario_id = scenario_id
        self.name = name
        self.total_duration = total_duration
        self.phases: list[ScenarioPhase] = []
        self._current_phase_idx: int = 0
        self._setup_phases()

    @abstractmethod
    def _setup_phases(self) -> None:
        """Define the phases of this scenario. Called during __init__."""
        ...

    @abstractmethod
    def apply(self, tick: int, plant) -> None:
        """Apply scenario effects for the current tick.

        Modifies equipment, sensors, events through the plant reference.

        Args:
            tick: Current simulation tick
            plant: Reference to the Plant object
        """
        ...

    def get_current_phase(self, tick: int) -> ScenarioPhase | None:
        """Return the active phase for the given tick."""
        for phase in reversed(self.phases):
            if tick >= phase.start_tick:
                if tick < phase.start_tick + phase.duration:
                    return phase
                # Check if we're past the last phase
                break
        # If past all phases, return last one
        if self.phases and tick >= self.phases[-1].start_tick:
            return self.phases[-1]
        return self.phases[0] if self.phases else None

    def get_label(self, tick: int) -> str:
        """Return the event label for the current tick."""
        phase = self.get_current_phase(tick)
        return phase.label if phase else "normal"

    def get_phase_progress(self, tick: int) -> float:
        """Return progress through current phase (0.0 to 1.0)."""
        phase = self.get_current_phase(tick)
        if phase is None:
            return 0.0
        elapsed = tick - phase.start_tick
        return min(1.0, elapsed / max(1, phase.duration))

    def ramp(self, tick: int, start_tick: int, duration: int,
             start_val: float = 0.0, end_val: float = 1.0) -> float:
        """Linear ramp function for gradual parameter changes."""
        if tick < start_tick:
            return start_val
        if tick >= start_tick + duration:
            return end_val
        progress = (tick - start_tick) / max(1, duration)
        return start_val + (end_val - start_val) * progress

    def sigmoid_ramp(self, tick: int, start_tick: int, duration: int,
                     start_val: float = 0.0, end_val: float = 1.0) -> float:
        """Sigmoid ramp for more realistic fault onset."""
        import math
        if tick < start_tick:
            return start_val
        if tick >= start_tick + duration:
            return end_val
        t = (tick - start_tick) / max(1, duration)
        s = 1.0 / (1.0 + math.exp(-12 * (t - 0.5)))
        return start_val + (end_val - start_val) * s

    def is_complete(self, tick: int) -> bool:
        """Check if scenario has completed all phases."""
        return tick >= self.total_duration
