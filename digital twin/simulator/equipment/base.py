"""
Abstract base class for all equipment models.
"""

from abc import ABC, abstractmethod

from simulator.config import EquipmentConfig, EquipmentState


class BaseEquipment(ABC):
    """Base class for all refinery equipment.

    Tracks health (0.0 = destroyed, 1.0 = perfect), operational state,
    and degradation over time.
    """

    def __init__(self, config: EquipmentConfig):
        self.config = config
        self.equipment_id = config.equipment_id
        self.zone_id = config.zone_id
        self.name = config.name
        self.health: float = 1.0
        self.state: EquipmentState = EquipmentState.RUNNING
        self.degradation_rate: float = config.base_degradation_rate
        self.failure_threshold: float = config.failure_threshold
        self._maintenance_flag: bool = False
        self._forced_state: EquipmentState | None = None

    def update(self, tick: int, dt: float = 1.0) -> dict:
        """Advance equipment state by one tick.

        Returns a dict of state changes for downstream consumers.
        """
        changes = {}

        # Apply forced state from scenario engine
        if self._forced_state is not None:
            if self.state != self._forced_state:
                changes["state_change"] = (self.state, self._forced_state)
                self.state = self._forced_state
            self._forced_state = None

        # Natural degradation (only when running)
        if self.state == EquipmentState.RUNNING:
            self.health -= self.degradation_rate * dt
            self.health = max(0.0, self.health)

            # Check failure
            if self.health < self.failure_threshold:
                changes["state_change"] = (self.state, EquipmentState.FAILED)
                self.state = EquipmentState.FAILED
                changes["failure"] = True

            # Check degraded
            elif self.health < self.failure_threshold * 2.0:
                if self.state != EquipmentState.DEGRADED:
                    changes["state_change"] = (self.state, EquipmentState.DEGRADED)
                    self.state = EquipmentState.DEGRADED
                    self._maintenance_flag = True

        # Equipment-specific update
        specific = self._update_specific(tick, dt)
        changes.update(specific)

        return changes

    @abstractmethod
    def _update_specific(self, tick: int, dt: float) -> dict:
        """Equipment-specific update logic."""
        ...

    def force_state(self, state: EquipmentState) -> None:
        """Force equipment into a specific state (used by scenario engine)."""
        self._forced_state = state

    def force_health(self, health: float) -> None:
        """Force equipment health value (used by scenario engine)."""
        self.health = max(0.0, min(1.0, health))

    def accelerate_degradation(self, factor: float) -> None:
        """Multiply degradation rate (used by scenarios for accelerated wear)."""
        self.degradation_rate = self.config.base_degradation_rate * factor

    def repair(self, amount: float = 1.0) -> None:
        """Restore health and return to running state."""
        self.health = min(1.0, self.health + amount)
        if self.health > self.failure_threshold * 2.0:
            self.state = EquipmentState.RUNNING
            self._maintenance_flag = False
        self.degradation_rate = self.config.base_degradation_rate

    @property
    def needs_maintenance(self) -> bool:
        return self._maintenance_flag

    def get_state_dict(self) -> dict:
        """Return current state as a flat dictionary."""
        return {
            "equipment_id": self.equipment_id,
            "state": self.state.value,
            "health": round(self.health, 4),
            "needs_maintenance": self._maintenance_flag,
        }
