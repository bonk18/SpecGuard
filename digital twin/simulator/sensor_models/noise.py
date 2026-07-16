"""
Sensor noise models.

Provides Gaussian measurement noise, sensor drift, spike artifacts,
and sensor failure modes (stuck value, dropout).
"""

import numpy as np


class SensorNoise:
    """Realistic sensor noise generator."""

    def __init__(self, seed: int = 42):
        self._rng = np.random.default_rng(seed)
        # Drift accumulators per sensor
        self._drift: dict[str, float] = {}
        self._stuck_sensors: dict[str, float] = {}   # sensor_id → stuck value

    def add_noise(self, value: float, noise_std: float,
                  sensor_id: str = "") -> float:
        """Add Gaussian measurement noise to a sensor value."""
        # Check for stuck sensor
        if sensor_id in self._stuck_sensors:
            return self._stuck_sensors[sensor_id]

        noise = self._rng.normal(0, noise_std)

        # Drift (slow random walk)
        if sensor_id:
            if sensor_id not in self._drift:
                self._drift[sensor_id] = 0.0
            self._drift[sensor_id] += self._rng.normal(0, noise_std * 0.001)
            # Mean-revert drift
            self._drift[sensor_id] *= 0.9999
            noise += self._drift[sensor_id]

        # Rare spike artifact (0.01% probability)
        if self._rng.random() < 0.0001:
            spike = self._rng.normal(0, noise_std * 10)
            noise += spike

        return value + noise

    def add_quantization(self, value: float, resolution: float) -> float:
        """Quantize sensor value to given resolution."""
        return round(value / resolution) * resolution

    def set_stuck(self, sensor_id: str, value: float) -> None:
        """Simulate stuck sensor (frozen reading)."""
        self._stuck_sensors[sensor_id] = value

    def clear_stuck(self, sensor_id: str) -> None:
        """Clear stuck sensor condition."""
        self._stuck_sensors.pop(sensor_id, None)

    def dropout(self, probability: float = 0.0001) -> bool:
        """Returns True if sensor has a dropout (missing reading)."""
        return self._rng.random() < probability

    def reset(self, seed: int = 42) -> None:
        self._rng = np.random.default_rng(seed)
        self._drift.clear()
        self._stuck_sensors.clear()
