"""
SCADA sensor generation.

Wraps process_model outputs into SCADA sensor readings with noise,
alarm evaluation, and emergency shutdown state tracking.
"""

from simulator.sensor_models.noise import SensorNoise
from simulator.config import SENSOR_SPECS


class SCADASensors:
    """Generates SCADA sensor readings from process model state."""

    SCADA_VARIABLES = [
        "pipeline_pressure", "tank_pressure", "pump_outlet_pressure",
        "pipeline_temperature", "tank_temperature",
        "pipeline_flow", "hydrocarbon_flow", "pump_flow",
        "isolation_valve", "relief_valve", "steam_valve",
        "pump_speed", "pump_power", "pump_temperature",
    ]

    def __init__(self, seed: int = 42):
        self.noise = SensorNoise(seed)
        self.esd_state: bool = False        # Emergency Shutdown
        self.esd_trigger_tick: int = -1
        self._alarm_states: dict[str, str] = {}

    def generate(self, process_values: dict[str, float],
                 equipment_states: dict[str, dict],
                 ventilation_status: float = 1.0,
                 tick: int = 0) -> dict:
        """Generate one row of SCADA sensor data.

        Args:
            process_values: Output from ProcessModel.step()
            equipment_states: Dict of equipment_id → state dicts
            ventilation_status: Overall ventilation effectiveness (0-1)
            tick: Current simulation tick

        Returns:
            Dict of all SCADA sensor readings plus metadata
        """
        readings = {}

        for var in self.SCADA_VARIABLES:
            spec = SENSOR_SPECS.get(var)
            if spec is None:
                continue

            # Get base value from process model
            value = process_values.get(var, spec.nominal)

            # Apply ESD effects
            if self.esd_state:
                if var in ("pump_speed", "pump_power", "pump_flow"):
                    value = 0.0
                elif var in ("isolation_valve",):
                    value = 0.0  # Fully closed
                elif var in ("relief_valve",):
                    value = 100.0  # Fully open

            # Add realistic measurement noise
            noisy_value = self.noise.add_noise(value, spec.noise_std, var)

            # Clamp to physical bounds
            if var in ("pump_speed", "pump_power", "pump_flow",
                       "pipeline_flow", "hydrocarbon_flow"):
                noisy_value = max(0.0, noisy_value)
            elif var in ("isolation_valve", "relief_valve", "steam_valve"):
                noisy_value = max(0.0, min(100.0, noisy_value))

            # Check for dropout
            if self.noise.dropout():
                readings[var] = None
                readings[f"{var}_quality"] = "BAD"
                continue

            readings[var] = round(noisy_value, 4)

            # Alarm evaluation
            alarm = "NORMAL"
            if noisy_value >= spec.hihi_alarm:
                alarm = "HIHI"
            elif noisy_value >= spec.high_alarm:
                alarm = "HIGH"
            elif noisy_value <= spec.low_alarm:
                alarm = "LOW"
            self._alarm_states[var] = alarm
            readings[f"{var}_alarm"] = alarm

        # Ventilation status
        readings["ventilation_status"] = round(ventilation_status, 4)

        # ESD state
        readings["esd_active"] = self.esd_state

        return readings

    def trigger_esd(self, tick: int) -> None:
        """Activate Emergency Shutdown."""
        self.esd_state = True
        self.esd_trigger_tick = tick

    def reset_esd(self) -> None:
        """Reset Emergency Shutdown."""
        self.esd_state = False

    def get_active_alarms(self) -> dict[str, str]:
        """Return dict of sensors with non-NORMAL alarm states."""
        return {k: v for k, v in self._alarm_states.items() if v != "NORMAL"}

    def reset(self, seed: int = 42) -> None:
        self.noise.reset(seed)
        self.esd_state = False
        self.esd_trigger_tick = -1
        self._alarm_states.clear()
