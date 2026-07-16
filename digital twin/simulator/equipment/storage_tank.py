"""
Storage tank equipment model.

Models level, pressure, and temperature with thermal inertia.
Pressure is a function of level, temperature, and gas composition.
"""

import math

from simulator.equipment.base import BaseEquipment
from simulator.config import EquipmentConfig


class StorageTank(BaseEquipment):
    """Petroleum storage tank with level/pressure/temperature dynamics."""

    def __init__(self, config: EquipmentConfig):
        super().__init__(config)
        # Tank state
        self.level: float = 65.0          # % fill (0-100)
        self.temperature: float = 80.0     # °C (TEP-scaled)
        self.pressure: float = 2634.0      # kPa (TEP-scaled)
        self.integrity: float = 1.0        # Structural integrity

        # Dynamics
        self.fill_rate: float = 0.001      # % per second during fill
        self.drain_rate: float = 0.0008    # % per second during drain
        self._thermal_inertia: float = 0.998  # Temperature smoothing
        self._ambient_temp: float = 35.0

        # Leak state
        self.leak_rate: float = 0.0        # m³/s (0 = no leak)

    def _update_specific(self, tick: int, dt: float) -> dict:
        changes = {}

        # Level dynamics: slow fill/drain cycle
        cycle = math.sin(tick * 2 * math.pi / 36000) * 0.0005
        self.level += (self.fill_rate - self.drain_rate + cycle) * dt
        self.level = max(5.0, min(95.0, self.level))

        # Leak reduces level
        if self.leak_rate > 0:
            self.level -= self.leak_rate * 10 * dt
            self.level = max(0.0, self.level)
            changes["leaking"] = True

        # Temperature: thermal inertia + slight heating from contents
        target_temp = 78.0 + (self.level / 100.0) * 4.0
        self.temperature = (self._thermal_inertia * self.temperature +
                           (1 - self._thermal_inertia) * target_temp)

        # Pressure: f(level, temperature, integrity)
        # Higher level = higher pressure, higher temp = higher pressure
        base_pressure = 2600.0 + (self.level / 100.0) * 50.0
        temp_effect = (self.temperature - 78.0) * 2.0
        integrity_effect = (1.0 - self.integrity) * -30.0
        leak_effect = -self.leak_rate * 500.0
        self.pressure = base_pressure + temp_effect + integrity_effect + leak_effect

        # Integrity degrades with health
        self.integrity = min(1.0, 0.5 + 0.5 * self.health)

        return changes

    def set_leak(self, rate: float) -> None:
        """Set leak rate in m³/s."""
        self.leak_rate = max(0.0, rate)

    def get_state_dict(self) -> dict:
        d = super().get_state_dict()
        d.update({
            "level": round(self.level, 2),
            "temperature": round(self.temperature, 3),
            "pressure": round(self.pressure, 2),
            "integrity": round(self.integrity, 4),
            "leak_rate": round(self.leak_rate, 6),
        })
        return d
