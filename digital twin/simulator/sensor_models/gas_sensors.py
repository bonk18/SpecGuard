"""
Gas detection sensor models.

Generates HC gas (%LEL), H2S, VOC, and O2 readings based on
equipment state, leak rates, ventilation effectiveness, and zone properties.
"""

import math

import numpy as np

from simulator.sensor_models.noise import SensorNoise
from simulator.config import SENSOR_SPECS, ZoneID


class GasSensors:
    """Zone-based gas detection derived from equipment state and leaks."""

    def __init__(self, seed: int = 42):
        self.noise = SensorNoise(seed + 100)
        self._rng = np.random.default_rng(seed + 100)

        # Per-zone gas concentrations
        self._zone_hc: dict[str, float] = {z.value: 0.5 for z in ZoneID}
        self._zone_h2s: dict[str, float] = {z.value: 0.2 for z in ZoneID}
        self._zone_voc: dict[str, float] = {z.value: 1.0 for z in ZoneID}
        self._zone_o2: dict[str, float] = {z.value: 20.9 for z in ZoneID}

        # Zone volumes (relative) for concentration calculations
        self._zone_volumes = {
            ZoneID.ZONE_A.value: 5000.0,   # Large tank area
            ZoneID.ZONE_B.value: 2000.0,   # Pipeline corridor
            ZoneID.ZONE_C.value: 1500.0,   # Pump station
            ZoneID.ZONE_D.value: 500.0,    # Smaller workshop (confined)
            ZoneID.ZONE_E.value: 300.0,    # Control room (sealed)
        }

    def generate(self, zone_id: str,
                 leak_rates: dict[str, float],
                 ventilation_effectiveness: float = 1.0,
                 temperature: float = 35.0,
                 tick: int = 0) -> dict:
        """Generate gas sensor readings for a given zone.

        Args:
            zone_id: Zone identifier
            leak_rates: Dict of equipment_id → leak rate (m³/s)
            ventilation_effectiveness: 0-1 (0=no ventilation, 1=full)
            temperature: Ambient temperature in the zone
            tick: Current tick

        Returns:
            Dict with gas sensor readings
        """
        volume = self._zone_volumes.get(zone_id, 1000.0)
        total_leak = sum(leak_rates.values())

        # --- Hydrocarbon Gas (%LEL) ---
        # HC accumulates from leaks, dissipates with ventilation
        hc_input = total_leak * 50000.0 / volume   # Convert leak → %LEL contribution
        hc_dissipation = ventilation_effectiveness * 0.05
        natural_dissipation = 0.005  # Even without ventilation, some natural loss
        current_hc = self._zone_hc.get(zone_id, 0.5)
        current_hc += (hc_input - (hc_dissipation + natural_dissipation) * current_hc)
        current_hc = max(0.0, min(100.0, current_hc))
        # Baseline noise even at zero leak
        if current_hc < 1.0:
            current_hc = max(0.0, 0.5 + self._rng.normal(0, 0.3))
        self._zone_hc[zone_id] = current_hc

        # --- H2S (ppm) ---
        # H2S is a trace component in hydrocarbon streams
        h2s_from_leak = total_leak * 2000.0 / volume
        current_h2s = self._zone_h2s.get(zone_id, 0.2)
        current_h2s += (h2s_from_leak - (hc_dissipation + natural_dissipation) * current_h2s)
        current_h2s = max(0.0, min(100.0, current_h2s))
        if current_h2s < 0.5:
            current_h2s = max(0.0, 0.2 + self._rng.normal(0, 0.1))
        self._zone_h2s[zone_id] = current_h2s

        # --- VOC (ppm) ---
        # VOC increases with temperature and leaks
        temp_factor = 1.0 + (temperature - 35.0) * 0.02
        voc_from_leak = total_leak * 10000.0 / volume * temp_factor
        current_voc = self._zone_voc.get(zone_id, 1.0)
        current_voc += (voc_from_leak - (hc_dissipation + natural_dissipation) * current_voc)
        current_voc = max(0.0, min(500.0, current_voc))
        if current_voc < 2.0:
            current_voc = max(0.0, 1.0 + self._rng.normal(0, 0.5))
        self._zone_voc[zone_id] = current_voc

        # --- Oxygen (%) ---
        # O2 is displaced by hydrocarbon gas
        hc_displacement = current_hc * 0.005  # Each %LEL displaces some O2
        vent_restoration = ventilation_effectiveness * 0.01
        current_o2 = self._zone_o2.get(zone_id, 20.9)
        target_o2 = 20.9 - hc_displacement
        current_o2 += (target_o2 - current_o2) * (vent_restoration + 0.001)
        current_o2 = max(0.0, min(23.5, current_o2))
        self._zone_o2[zone_id] = current_o2

        # Add sensor noise
        hc_spec = SENSOR_SPECS["hc_gas_lel"]
        h2s_spec = SENSOR_SPECS["h2s_ppm"]
        voc_spec = SENSOR_SPECS["voc_ppm"]
        o2_spec = SENSOR_SPECS["oxygen_pct"]

        readings = {
            "hc_gas_lel": round(max(0.0, self.noise.add_noise(
                current_hc, hc_spec.noise_std, f"{zone_id}_hc")), 2),
            "h2s_ppm": round(max(0.0, self.noise.add_noise(
                current_h2s, h2s_spec.noise_std, f"{zone_id}_h2s")), 2),
            "voc_ppm": round(max(0.0, self.noise.add_noise(
                current_voc, voc_spec.noise_std, f"{zone_id}_voc")), 2),
            "oxygen_pct": round(max(0.0, self.noise.add_noise(
                current_o2, o2_spec.noise_std, f"{zone_id}_o2")), 2),
        }

        # Alarm evaluation
        for sensor, spec in [("hc_gas_lel", hc_spec), ("h2s_ppm", h2s_spec),
                              ("voc_ppm", voc_spec)]:
            val = readings[sensor]
            if val >= spec.hihi_alarm:
                readings[f"{sensor}_alarm"] = "HIHI"
            elif val >= spec.high_alarm:
                readings[f"{sensor}_alarm"] = "HIGH"
            else:
                readings[f"{sensor}_alarm"] = "NORMAL"

        # O2 alarm (low is dangerous)
        o2_val = readings["oxygen_pct"]
        if o2_val <= o2_spec.low_alarm:
            readings["oxygen_alarm"] = "LOW"
        elif o2_val >= o2_spec.high_alarm:
            readings["oxygen_alarm"] = "HIGH"
        else:
            readings["oxygen_alarm"] = "NORMAL"

        readings["zone_id"] = zone_id
        return readings

    def get_zone_concentrations(self) -> dict:
        """Return raw concentrations for all zones (for cross-zone diffusion)."""
        return {
            "hc": dict(self._zone_hc),
            "h2s": dict(self._zone_h2s),
            "voc": dict(self._zone_voc),
            "o2": dict(self._zone_o2),
        }

    def reset(self, seed: int = 42) -> None:
        self.noise.reset(seed + 100)
        self._rng = np.random.default_rng(seed + 100)
        self._zone_hc = {z.value: 0.5 for z in ZoneID}
        self._zone_h2s = {z.value: 0.2 for z in ZoneID}
        self._zone_voc = {z.value: 1.0 for z in ZoneID}
        self._zone_o2 = {z.value: 20.9 for z in ZoneID}
