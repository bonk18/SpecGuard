"""
Shift log text generator.

Produces realistic operator shift log entries using parameterized templates
populated from live simulator state.
"""

import numpy as np


class ShiftLogGenerator:
    """Generates realistic shift log text entries."""

    NORMAL_TEMPLATES = [
        "Routine inspection of {equipment} completed. All readings nominal.",
        "Shift handover completed. No outstanding issues.",
        "Pressure readings on {sensor} within normal range at {value} {unit}.",
        "Temperature check on {equipment} — {value}°C, within limits.",
        "Flow rate on {sensor} steady at {value} {unit}.",
        "Valve {equipment} position verified at {value}%.",
        "Gas detection check in {zone} — all clear, {value} %LEL.",
        "PPE inspection completed for on-shift personnel.",
        "Safety shower and eyewash station tested — operational.",
        "Fire extinguisher inspection completed in {zone}.",
        "Routine sample collected from {equipment}.",
        "Control room instrument readings logged — all normal.",
        "Perimeter fence check completed — secure.",
        "Emergency exit routes verified — clear.",
        "Communication systems tested — operational.",
    ]

    WARNING_TEMPLATES = [
        "Pressure fluctuations observed on {sensor}. Value: {value} {unit}. Monitoring.",
        "Minor hydrocarbon smell reported near {zone}. Gas test: {value} %LEL.",
        "Slight temperature rise on {equipment}: {value}°C. Above normal baseline.",
        "Vibration increase noted on {equipment}. Reading: {value} mm/s RMS.",
        "Ventilation inspection pending for {zone}.",
        "Flow rate deviation on {sensor}: {value} {unit} vs nominal {nominal} {unit}.",
        "Valve {equipment} response sluggish. Position drifting.",
        "Bearing temperature trending upward on {equipment}: {value}°C.",
        "Minor oil sheen observed near {equipment}. Investigating.",
        "Worker {worker} reported unusual noise from {equipment}.",
        "Pump {equipment} current draw elevated: {value}A.",
        "Corrosion spot identified on {equipment} during visual inspection.",
    ]

    CRITICAL_TEMPLATES = [
        "HIGH alarm on {sensor}: {value} {unit}. Immediate investigation required.",
        "H2S alarm triggered in {zone}. Reading: {value} ppm. Area evacuated.",
        "Gas leak confirmed at {equipment}. HC reading: {value} %LEL.",
        "Pump {equipment} TRIPPED — bearing failure suspected. Vibration: {value} mm/s.",
        "Emergency shutdown initiated in {zone}. ESD activated.",
        "Ventilation failure in {zone}. Fan {equipment} not responding.",
        "Oxygen depletion alarm in {zone}: {value}%. Confined space entry halted.",
        "Fire detected near {equipment}. Emergency response activated.",
        "Hot work permit SUSPENDED in {zone} — gas detected at {value} %LEL.",
        "Worker {worker} reported exposure symptoms in {zone}.",
        "Pipeline pressure loss on {sensor}: {value} {unit}. Possible rupture.",
        "Multiple alarms active in {zone}. Initiating emergency protocol.",
    ]

    MAINTENANCE_TEMPLATES = [
        "Maintenance work order raised for {equipment}: {description}.",
        "Equipment isolation completed on {equipment} for maintenance.",
        "Technician {worker} commenced work on {equipment}.",
        "Maintenance on {equipment} completed. Returning to service.",
        "Lock-out tag-out verified on {equipment}.",
        "Spare parts received for {equipment} maintenance.",
    ]

    def __init__(self, seed: int = 42):
        self._rng = np.random.default_rng(seed + 500)
        self._log_interval = 300     # Generate log every ~300 seconds
        self._last_log_tick = -999

    def generate(self, tick: int, plant_state: dict,
                 alarms: dict, gas_readings: dict,
                 maintenance_state: dict,
                 force: bool = False) -> dict | None:
        """Generate a shift log entry if conditions are met.

        Args:
            tick: Current simulation tick
            plant_state: Dict with equipment states and sensor values
            alarms: Dict of active alarms
            gas_readings: Gas sensor readings by zone
            maintenance_state: Current maintenance activities
            force: Force generation regardless of interval

        Returns:
            Log entry dict or None if no log generated
        """
        # Check if it's time for a log
        if not force and (tick - self._last_log_tick) < self._log_interval:
            return None

        # Determine severity based on conditions
        has_critical = any(v in ("HIHI", "HIGH") for v in alarms.values())
        has_warning = any(v in ("HIGH",) for v in alarms.values())
        has_gas = any(gas_readings.get(z, {}).get("hc_gas_lel", 0) > 5.0
                      for z in gas_readings)
        active_maintenance = maintenance_state.get("active_count", 0) > 0

        # Select template category
        if has_critical or has_gas:
            templates = self.CRITICAL_TEMPLATES
            severity = "CRITICAL"
        elif has_warning:
            templates = self.WARNING_TEMPLATES
            severity = "WARNING"
        elif active_maintenance and self._rng.random() < 0.4:
            templates = self.MAINTENANCE_TEMPLATES
            severity = "INFO"
        else:
            templates = self.NORMAL_TEMPLATES
            severity = "INFO"

        template = self._rng.choice(templates)

        # Fill template parameters from plant state
        params = self._extract_params(plant_state, gas_readings, maintenance_state)
        try:
            message = template.format(**params)
        except (KeyError, IndexError):
            message = template.format(
                equipment="PMP-301", sensor="pipeline_pressure",
                zone="Zone_C", value="N/A", unit="kPa",
                nominal="2705", worker="W003", description="scheduled maintenance")

        self._last_log_tick = tick
        # Jitter the next interval
        self._log_interval = int(self._rng.integers(180, 600))

        return {
            "tick": tick,
            "severity": severity,
            "message": message,
            "operator": self._rng.choice(["W001", "W002", "W005", "W007", "W008", "W011"]),
        }

    def _extract_params(self, plant_state: dict, gas_readings: dict,
                        maintenance_state: dict) -> dict:
        """Extract template parameters from current state."""
        equipment_ids = list(plant_state.get("equipment", {}).keys())
        eq = self._rng.choice(equipment_ids) if equipment_ids else "PMP-301"

        sensors = ["pipeline_pressure", "tank_pressure", "pump_outlet_pressure",
                    "pipeline_temperature", "tank_temperature", "pipeline_flow"]
        sensor = self._rng.choice(sensors)

        zones = ["Zone_A", "Zone_B", "Zone_C", "Zone_D"]
        zone = self._rng.choice(zones)

        sensor_values = plant_state.get("scada", {})
        value = sensor_values.get(sensor, "N/A")
        if isinstance(value, float):
            value = f"{value:.1f}"

        units = {"pipeline_pressure": "kPa", "tank_pressure": "kPa",
                 "pump_outlet_pressure": "kPa", "pipeline_temperature": "°C",
                 "tank_temperature": "°C", "pipeline_flow": "m³/h"}
        unit = units.get(sensor, "")

        nominals = {"pipeline_pressure": "2705", "tank_pressure": "2634",
                    "pump_outlet_pressure": "3102", "pipeline_temperature": "120.4",
                    "tank_temperature": "80.1", "pipeline_flow": "42.3"}
        nominal = nominals.get(sensor, "N/A")

        workers = ["W001", "W002", "W003", "W004", "W005", "W006"]
        worker = self._rng.choice(workers)

        activities = maintenance_state.get("activities", [])
        description = activities[0]["description"] if activities else "scheduled maintenance"

        return {
            "equipment": eq, "sensor": sensor, "zone": zone,
            "value": value, "unit": unit, "nominal": nominal,
            "worker": worker, "description": description,
        }

    def reset(self, seed: int = 42) -> None:
        self._rng = np.random.default_rng(seed + 500)
        self._last_log_tick = -999
        self._log_interval = 300
