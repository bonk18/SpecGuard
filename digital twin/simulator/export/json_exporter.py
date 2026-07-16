"""
JSON Lines exporter for simulation output.

Writes one JSON object per line with nested structure grouping by category.
"""

import json
import os


class JSONExporter:
    """Exports simulation data in JSON Lines format."""

    def __init__(self, output_dir: str):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        self._filepath = os.path.join(output_dir, "simulation_data.jsonl")
        self._file = open(self._filepath, 'w')

    def write_row(self, row: dict, tick: int) -> None:
        """Write a single row as a JSON line with nested structure."""
        structured = {
            "timestamp": row.get("timestamp"),
            "tick": row.get("tick"),
            "scenario_id": row.get("scenario_id"),
            "event_label": row.get("event_label"),
            "scada": {
                "pipeline_pressure": row.get("pipeline_pressure"),
                "tank_pressure": row.get("tank_pressure"),
                "pump_outlet_pressure": row.get("pump_outlet_pressure"),
                "pipeline_temperature": row.get("pipeline_temperature"),
                "tank_temperature": row.get("tank_temperature"),
                "pipeline_flow": row.get("pipeline_flow"),
                "hydrocarbon_flow": row.get("hydrocarbon_flow"),
                "pump_flow": row.get("pump_flow"),
                "isolation_valve": row.get("isolation_valve"),
                "relief_valve": row.get("relief_valve"),
                "steam_valve": row.get("steam_valve"),
                "pump_speed": row.get("pump_speed"),
                "pump_power": row.get("pump_power"),
                "pump_temperature": row.get("pump_temperature"),
                "ventilation_status": row.get("ventilation_status"),
                "esd_active": row.get("esd_active"),
            },
            "gas": {
                "hc_gas_lel": row.get("hc_gas_lel"),
                "h2s_ppm": row.get("h2s_ppm"),
                "voc_ppm": row.get("voc_ppm"),
                "oxygen_pct": row.get("oxygen_pct"),
            },
            "equipment": {
                "pump_running": row.get("pump_running"),
                "pump_failed": row.get("pump_failed"),
                "valve_failed": row.get("valve_failed"),
                "ventilation_failed": row.get("ventilation_failed"),
                "bearing_wear": row.get("bearing_wear"),
                "maintenance_required": row.get("maintenance_required"),
            },
            "worker": {
                "worker_id": row.get("worker_id"),
                "zone": row.get("worker_zone"),
                "task": row.get("worker_task"),
                "ppe_compliant": row.get("ppe_compliant"),
                "time_in_zone": row.get("time_in_zone"),
            },
            "permits": {
                "hot_work_active": row.get("hot_work_active"),
                "confined_space_active": row.get("confined_space_active"),
                "electrical_active": row.get("electrical_active"),
                "line_breaking_active": row.get("line_breaking_active"),
            },
            "maintenance": {
                "equipment": row.get("maintenance_equipment"),
                "isolation_complete": row.get("isolation_complete"),
                "technician": row.get("maintenance_technician"),
                "remaining": row.get("maintenance_remaining"),
            },
            "shift_log": {
                "severity": row.get("log_severity"),
                "message": row.get("log_message"),
                "operator": row.get("log_operator"),
            } if row.get("log_message") else None,
            "cctv": {
                "camera_id": row.get("cctv_camera_id"),
                "zone_id": row.get("cctv_zone_id"),
                "event_type": row.get("cctv_event_type"),
                "description": row.get("cctv_description"),
                "confidence": row.get("cctv_confidence"),
            } if row.get("cctv_event_type") else None,
        }

        # Remove None nested objects
        structured = {k: v for k, v in structured.items() if v is not None}

        self._file.write(json.dumps(structured, default=str) + '\n')

    def close(self) -> None:
        self._file.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
