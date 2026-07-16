"""
Pump equipment model.

Models speed/power/flow relationship, bearing wear, seal integrity,
and multiple failure modes (bearing seizure, seal failure, cavitation).
"""

import math

from simulator.equipment.base import BaseEquipment
from simulator.config import EquipmentConfig, EquipmentState


class Pump(BaseEquipment):
    """Centrifugal pump with bearing/seal degradation and failure modes."""

    def __init__(self, config: EquipmentConfig):
        super().__init__(config)
        # Pump operating parameters
        self.speed: float = 41.1            # RPM (TEP-scaled)
        self.target_speed: float = 41.1
        self.power: float = 341.4           # kW (TEP-scaled)
        self.flow_rate: float = 22.95       # m³/h (TEP-scaled)
        self.outlet_pressure: float = 3102.0  # kPa (TEP-scaled)
        self.temperature: float = 65.8       # °C (TEP-scaled)

        # Component health
        self.bearing_health: float = 1.0     # 0-1
        self.seal_health: float = 1.0        # 0-1
        self.vibration: float = 0.5          # mm/s RMS (normal < 2.0)

        # Degradation rates (per second)
        self._bearing_degradation: float = 3e-7
        self._seal_degradation: float = 2e-7

        # Leak from seal
        self.seal_leak_rate: float = 0.0     # m³/s

    def _update_specific(self, tick: int, dt: float) -> dict:
        changes = {}

        if self.state in (EquipmentState.RUNNING, EquipmentState.DEGRADED):
            # Speed control (ramp toward target)
            speed_diff = self.target_speed - self.speed
            self.speed += speed_diff * 0.01 * dt
            self.speed = max(0.0, self.speed)

            # Component degradation
            self.bearing_health -= self._bearing_degradation * dt
            self.bearing_health = max(0.0, self.bearing_health)
            self.seal_health -= self._seal_degradation * dt
            self.seal_health = max(0.0, self.seal_health)

            # Vibration increases as bearing wears
            base_vibration = 0.5
            wear_vibration = (1.0 - self.bearing_health) * 15.0
            self.vibration = base_vibration + wear_vibration

            # Power = f(speed, bearing friction)
            friction_factor = 1.0 + (1.0 - self.bearing_health) * 0.3
            self.power = 341.4 * (self.speed / 41.1) ** 2 * friction_factor

            # Flow = f(speed, seal health)
            seal_loss = (1.0 - self.seal_health) * 0.2
            self.flow_rate = 22.95 * (self.speed / 41.1) * (1.0 - seal_loss)
            self.flow_rate = max(0.0, self.flow_rate)

            # Outlet pressure = f(speed, flow)
            self.outlet_pressure = 3102.0 * (self.speed / 41.1) ** 2

            # Temperature: increases with friction and bearing wear
            target_temp = 65.8 + (1.0 - self.bearing_health) * 30.0
            self.temperature = 0.999 * self.temperature + 0.001 * target_temp

            # Seal leak
            if self.seal_health < 0.5:
                self.seal_leak_rate = (0.5 - self.seal_health) * 0.002
                changes["seal_leak"] = True

            # Bearing failure check
            if self.bearing_health < 0.1:
                self.state = EquipmentState.FAILED
                self.speed = 0.0
                self.flow_rate = 0.0
                self.power = 0.0
                changes["failure"] = True
                changes["failure_mode"] = "bearing_seizure"

            # Seal failure check
            if self.seal_health < 0.05:
                changes["seal_failure"] = True

            # Overall health is min of components
            self.health = min(self.bearing_health, self.seal_health)

        elif self.state == EquipmentState.FAILED:
            self.speed = 0.0
            self.flow_rate = 0.0
            self.power = 0.0
            # Temperature cools down
            self.temperature = 0.9999 * self.temperature + 0.0001 * 35.0

        elif self.state == EquipmentState.STOPPED:
            self.speed = 0.0
            self.flow_rate = 0.0
            self.power = 0.0
            self.temperature = 0.9999 * self.temperature + 0.0001 * 35.0

        return changes

    def set_speed(self, speed: float) -> None:
        """Set target pump speed."""
        self.target_speed = max(0.0, speed)

    def accelerate_bearing_wear(self, factor: float) -> None:
        """Multiply bearing degradation rate."""
        self._bearing_degradation = 3e-7 * factor

    def accelerate_seal_wear(self, factor: float) -> None:
        """Multiply seal degradation rate."""
        self._seal_degradation = 2e-7 * factor

    def get_state_dict(self) -> dict:
        d = super().get_state_dict()
        d.update({
            "speed": round(self.speed, 3),
            "power": round(self.power, 2),
            "flow_rate": round(self.flow_rate, 3),
            "outlet_pressure": round(self.outlet_pressure, 2),
            "temperature": round(self.temperature, 3),
            "bearing_health": round(self.bearing_health, 4),
            "seal_health": round(self.seal_health, 4),
            "vibration": round(self.vibration, 3),
            "seal_leak_rate": round(self.seal_leak_rate, 6),
        })
        return d
