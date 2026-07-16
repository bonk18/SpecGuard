"""
Ventilation system equipment model.

Models fan speed, airflow, and its effect on gas concentration dissipation.
"""

from simulator.equipment.base import BaseEquipment
from simulator.config import EquipmentConfig, EquipmentState


class VentilationSystem(BaseEquipment):
    """Ventilation fan with airflow modeling and gas dissipation effect."""

    def __init__(self, config: EquipmentConfig):
        super().__init__(config)
        # Operating parameters
        self.fan_speed: float = 100.0         # % of max (0-100)
        self.target_fan_speed: float = 100.0
        self.airflow: float = 1.0             # Relative airflow (0-1)
        self.motor_current: float = 15.0       # Amps (nominal)

        # Effectiveness
        self.gas_dissipation_rate: float = 0.05  # fraction of gas removed per second
        self.temperature_reduction: float = 2.0   # °C below ambient with full vent

    def _update_specific(self, tick: int, dt: float) -> dict:
        changes = {}

        if self.state in (EquipmentState.RUNNING, EquipmentState.DEGRADED):
            # Fan speed ramps toward target
            diff = self.target_fan_speed - self.fan_speed
            self.fan_speed += diff * 0.05 * dt
            self.fan_speed = max(0.0, min(100.0, self.fan_speed))

            # Airflow proportional to fan speed and health
            self.airflow = (self.fan_speed / 100.0) * self.health
            self.airflow = max(0.0, min(1.0, self.airflow))

            # Motor current increases with degradation
            self.motor_current = 15.0 * (self.fan_speed / 100.0)
            self.motor_current *= (1.0 + (1.0 - self.health) * 0.5)

            # Gas dissipation effectiveness
            self.gas_dissipation_rate = 0.05 * self.airflow

            # Motor failure at very low health
            if self.health < 0.05:
                self.state = EquipmentState.FAILED
                self.fan_speed = 0.0
                self.airflow = 0.0
                self.gas_dissipation_rate = 0.0
                changes["failure"] = True
                changes["failure_mode"] = "motor_failure"

        elif self.state == EquipmentState.FAILED:
            self.fan_speed = 0.0
            self.airflow = 0.0
            self.gas_dissipation_rate = 0.001   # Natural convection only
            self.motor_current = 0.0

        elif self.state == EquipmentState.STOPPED:
            self.fan_speed = 0.0
            self.airflow = 0.0
            self.gas_dissipation_rate = 0.001
            self.motor_current = 0.0

        return changes

    def set_speed(self, speed: float) -> None:
        """Set target fan speed (0-100%)."""
        self.target_fan_speed = max(0.0, min(100.0, speed))

    def boost(self) -> None:
        """Emergency boost to full speed."""
        self.target_fan_speed = 100.0

    def get_state_dict(self) -> dict:
        d = super().get_state_dict()
        d.update({
            "fan_speed": round(self.fan_speed, 2),
            "airflow": round(self.airflow, 4),
            "motor_current": round(self.motor_current, 2),
            "gas_dissipation_rate": round(self.gas_dissipation_rate, 4),
        })
        return d
