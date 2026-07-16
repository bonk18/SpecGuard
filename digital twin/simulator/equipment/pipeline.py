"""
Pipeline network equipment model.

Models pressure drop, flow, and leak potential across pipeline segments.
"""

import math

from simulator.equipment.base import BaseEquipment
from simulator.config import EquipmentConfig


class Pipeline(BaseEquipment):
    """Pipeline segment with pressure-flow dynamics and leak modeling."""

    def __init__(self, config: EquipmentConfig):
        super().__init__(config)
        # Pipeline state
        self.inlet_pressure: float = 2750.0    # kPa
        self.outlet_pressure: float = 2700.0   # kPa
        self.flow_rate: float = 42.3           # m³/h (TEP-scaled)
        self.temperature: float = 120.4         # °C (TEP-scaled)

        # Physical properties
        self.diameter: float = 0.3             # meters
        self.length: float = 200.0             # meters
        self.friction_factor: float = 0.02     # Darcy friction factor
        self.wall_thickness: float = 1.0       # relative (1.0 = nominal)

        # Leak state
        self.leak_rate: float = 0.0            # m³/s
        self.leak_location: float = 0.5        # fractional position along pipe

    def _update_specific(self, tick: int, dt: float) -> dict:
        changes = {}

        # Pressure drop across pipeline (simplified Darcy-Weisbach)
        velocity = self.flow_rate / (3600 * math.pi * (self.diameter / 2) ** 2)
        dp = self.friction_factor * (self.length / self.diameter) * 0.5 * velocity ** 2
        self.outlet_pressure = self.inlet_pressure - dp * 0.01

        # Leak effect
        if self.leak_rate > 0:
            flow_loss = self.leak_rate * 3600  # convert to m³/h
            self.flow_rate = max(0.0, self.flow_rate - flow_loss * 0.1)
            self.outlet_pressure -= self.leak_rate * 200
            changes["leaking"] = True

        # Wall thickness degrades with health
        self.wall_thickness = 0.3 + 0.7 * self.health

        # Temperature: slight cooling along pipeline
        ambient = 35.0
        self.temperature = self.temperature * 0.9999 + ambient * 0.0001

        return changes

    def set_inlet_conditions(self, pressure: float, flow: float) -> None:
        """Set inlet pressure and flow from upstream equipment."""
        self.inlet_pressure = pressure
        self.flow_rate = flow

    def set_leak(self, rate: float, location: float = 0.5) -> None:
        """Set leak rate and location."""
        self.leak_rate = max(0.0, rate)
        self.leak_location = max(0.0, min(1.0, location))

    def get_state_dict(self) -> dict:
        d = super().get_state_dict()
        d.update({
            "inlet_pressure": round(self.inlet_pressure, 2),
            "outlet_pressure": round(self.outlet_pressure, 2),
            "flow_rate": round(self.flow_rate, 3),
            "temperature": round(self.temperature, 3),
            "leak_rate": round(self.leak_rate, 6),
            "wall_thickness": round(self.wall_thickness, 4),
        })
        return d
