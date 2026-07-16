"""
CSV exporter for simulation output.

Writes streaming CSV with all sensor, event, and state data.
Supports both monolithic and split-by-category output modes.
"""

import csv
import os
from typing import TextIO


class CSVExporter:
    """Exports simulation data to CSV files."""

    def __init__(self, output_dir: str, split: bool = False):
        self.output_dir = output_dir
        self.split = split
        os.makedirs(output_dir, exist_ok=True)

        self._files: dict[str, TextIO] = {}
        self._writers: dict[str, csv.DictWriter] = {}
        self._headers_written: dict[str, bool] = {}
        self._combined_headers: list[str] | None = None

    def write_row(self, row: dict, tick: int) -> None:
        """Write a single row of data.

        Args:
            row: Complete data dict for this tick
            tick: Current tick number
        """
        if self.split:
            self._write_split(row, tick)
        else:
            self._write_combined(row, tick)

    def _write_combined(self, row: dict, tick: int) -> None:
        """Write to single combined CSV file."""
        if "combined" not in self._files:
            filepath = os.path.join(self.output_dir, "simulation_data.csv")
            self._files["combined"] = open(filepath, 'w', newline='')
            self._combined_headers = sorted(row.keys())
            self._writers["combined"] = csv.DictWriter(
                self._files["combined"], fieldnames=self._combined_headers,
                extrasaction='ignore')
            self._writers["combined"].writeheader()

        self._writers["combined"].writerow(row)

    def _write_split(self, row: dict, tick: int) -> None:
        """Write to category-specific CSV files."""
        # Define category → column prefix mapping
        categories = {
            "scada": ["timestamp", "tick", "scenario_id", "event_label",
                      "pipeline_pressure", "tank_pressure", "pump_outlet_pressure",
                      "pipeline_temperature", "tank_temperature",
                      "pipeline_flow", "hydrocarbon_flow", "pump_flow",
                      "isolation_valve", "relief_valve", "steam_valve",
                      "pump_speed", "pump_power", "pump_temperature",
                      "ventilation_status", "esd_active"],
            "gas": ["timestamp", "tick", "scenario_id", "event_label",
                    "hc_gas_lel", "h2s_ppm", "voc_ppm", "oxygen_pct",
                    "hc_gas_lel_alarm", "h2s_ppm_alarm", "voc_ppm_alarm",
                    "oxygen_alarm", "gas_zone_id"],
            "equipment": ["timestamp", "tick", "scenario_id", "event_label",
                          "pump_running", "pump_failed", "valve_failed",
                          "ventilation_failed", "bearing_wear",
                          "maintenance_required", "esd_active"],
            "workers": ["timestamp", "tick", "scenario_id", "event_label",
                        "worker_id", "worker_zone", "worker_task",
                        "ppe_compliant", "time_in_zone"],
            "permits": ["timestamp", "tick", "scenario_id", "event_label",
                        "hot_work_active", "confined_space_active",
                        "electrical_active", "line_breaking_active"],
            "maintenance": ["timestamp", "tick", "scenario_id", "event_label",
                           "maintenance_equipment", "isolation_complete",
                           "maintenance_technician", "maintenance_remaining"],
            "shift_logs": ["timestamp", "tick", "scenario_id",
                          "log_severity", "log_message", "log_operator"],
            "cctv": ["timestamp", "tick", "scenario_id",
                    "cctv_camera_id", "cctv_zone_id", "cctv_event_type",
                    "cctv_description", "cctv_confidence"],
        }

        for category, columns in categories.items():
            # Filter row to only relevant columns
            cat_row = {k: row.get(k) for k in columns if k in row}
            if not cat_row or len(cat_row) <= 4:  # Only metadata columns
                continue

            if category not in self._files:
                filepath = os.path.join(self.output_dir, f"{category}.csv")
                self._files[category] = open(filepath, 'w', newline='')
                self._writers[category] = csv.DictWriter(
                    self._files[category], fieldnames=columns,
                    extrasaction='ignore')
                self._writers[category].writeheader()

            self._writers[category].writerow(cat_row)

    def close(self) -> None:
        """Close all open file handles."""
        for f in self._files.values():
            f.close()
        self._files.clear()
        self._writers.clear()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
