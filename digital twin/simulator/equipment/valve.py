"""
Valve equipment model.

Models valve position, stuck-valve failures, and partial closure degradation.
"""

from simulator.equipment.base import BaseEquipment
from simulator.config import EquipmentConfig, EquipmentState


class Valve(BaseEquipment):
    """Process valve with position control and failure modes."""

    def __init__(self, config: EquipmentConfig, initial_position: float = 50.0):
        super().__init__(config)
        self.position: float = initial_position    # 0-100%
        self.target_position: float = initial_position
        self.travel_speed: float = 2.0             # % per second
        self.is_stuck: bool = False
        self.stuck_position: float = 0.0
        self._stiction: float = 0.0                # Valve stiction (0-1)

    def _update_specific(self, tick: int, dt: float) -> dict:
        changes = {}

        # Stiction increases as valve degrades
        self._stiction = (1.0 - self.health) * 0.5

        if self.is_stuck:
            self.position = self.stuck_position
            changes["stuck"] = True
        elif self.state in (EquipmentState.RUNNING, EquipmentState.DEGRADED):
            # Move toward target with travel speed
            diff = self.target_position - self.position
            if abs(diff) > self._stiction * 5.0:
                # Overcome stiction threshold
                max_move = self.travel_speed * dt
                if abs(diff) <= max_move:
                    self.position = self.target_position
                else:
                    self.position += max_move * (1 if diff > 0 else -1)
            # Small random stiction jitter
            elif abs(diff) > 0.01 and self._stiction > 0.1:
                changes["stiction"] = True

        self.position = max(0.0, min(100.0, self.position))

        # Check stuck failure
        if self.health < 0.1 and not self.is_stuck:
            self.is_stuck = True
            self.stuck_position = self.position
            self.state = EquipmentState.FAILED
            changes["failure"] = True
            changes["failure_mode"] = "stuck_valve"

        return changes

    def set_position(self, position: float) -> None:
        """Set target valve position (0-100%)."""
        self.target_position = max(0.0, min(100.0, position))

    def force_stuck(self, position: float | None = None) -> None:
        """Force valve into stuck state at given or current position."""
        self.is_stuck = True
        self.stuck_position = position if position is not None else self.position
        self.state = EquipmentState.FAILED

    def unstick(self) -> None:
        """Clear stuck state."""
        self.is_stuck = False
        self.state = EquipmentState.RUNNING

    def get_state_dict(self) -> dict:
        d = super().get_state_dict()
        d.update({
            "position": round(self.position, 2),
            "target_position": round(self.target_position, 2),
            "is_stuck": self.is_stuck,
            "stiction": round(self._stiction, 4),
        })
        return d
