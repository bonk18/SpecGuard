"""
CCTV event generator.

Produces structured CCTV detection events derived from worker state
and zone conditions.
"""

import numpy as np

from simulator.config import ZoneID, ZONES


class CCTVEventGenerator:
    """Generates CCTV camera detection events from worker and zone state."""

    EVENT_TEMPLATES = {
        "worker_detected": "Worker {worker_id} detected in {zone_name}",
        "worker_entered": "Worker {worker_id} entered {zone_name}",
        "worker_exited": "Worker {worker_id} exited {zone_name}",
        "ppe_violation": "PPE non-compliance detected: Worker {worker_id} missing {missing_item} in {zone_name}",
        "restricted_entry": "Unauthorized entry: Worker {worker_id} in restricted {zone_name}",
        "confined_space_entry": "Worker {worker_id} entered confined space in {zone_name}",
        "vehicle_detected": "Vehicle detected in {zone_name}",
        "crowd_detected": "Multiple workers ({count}) detected in {zone_name}",
        "worker_down": "Possible worker down detected in {zone_name}",
        "smoke_detected": "Smoke/haze detected by camera in {zone_name}",
        "ppe_compliant": "PPE compliance confirmed: Worker {worker_id} in {zone_name}",
    }

    CAMERA_IDS = {
        ZoneID.ZONE_A.value: ["CAM-A01", "CAM-A02"],
        ZoneID.ZONE_B.value: ["CAM-B01", "CAM-B02"],
        ZoneID.ZONE_C.value: ["CAM-C01", "CAM-C02"],
        ZoneID.ZONE_D.value: ["CAM-D01"],
        ZoneID.ZONE_E.value: ["CAM-E01"],
    }

    def __init__(self, seed: int = 42):
        self._rng = np.random.default_rng(seed + 600)
        self._last_events: dict[str, int] = {}  # event_key → last_tick
        self._event_interval = 30  # Min seconds between same event type

    def generate(self, tick: int, worker_events: list[dict],
                 gas_levels: dict[str, float],
                 hc_concentration: dict[str, float] | None = None) -> list[dict]:
        """Generate CCTV events for current tick.

        Args:
            tick: Current simulation tick
            worker_events: List of worker state dicts
            gas_levels: Per-zone gas levels
            hc_concentration: Per-zone HC concentrations

        Returns:
            List of CCTV event dicts
        """
        events = []
        hc_concentration = hc_concentration or {}

        # Group workers by zone
        zone_workers: dict[str, list[dict]] = {}
        for w in worker_events:
            zone = w.get("current_zone", "")
            if zone and zone != "off_site" and not w.get("is_traveling"):
                zone_workers.setdefault(zone, []).append(w)

        for zone_id, workers in zone_workers.items():
            zone_cfg = ZONES.get(ZoneID(zone_id) if zone_id.startswith("Zone") else None)
            zone_name = zone_cfg.name if zone_cfg else zone_id
            cameras = self.CAMERA_IDS.get(zone_id, ["CAM-GEN"])

            # Worker detection events (periodic, not every tick)
            for w in workers:
                wid = w["worker_id"]

                # Worker detected (every ~60s)
                if self._should_emit(f"detect_{wid}_{zone_id}", tick, 60):
                    events.append(self._make_event(
                        tick, "worker_detected", cameras, zone_id, zone_name,
                        worker_id=wid))

                # PPE violation
                if not w.get("ppe_compliant", True):
                    missing_items = [k for k, v in w.get("ppe_items", {}).items() if not v]
                    missing = missing_items[0] if missing_items else "PPE item"
                    if self._should_emit(f"ppe_{wid}_{zone_id}", tick, 120):
                        events.append(self._make_event(
                            tick, "ppe_violation", cameras, zone_id, zone_name,
                            worker_id=wid, missing_item=missing.replace("_", " ")))
                else:
                    # Occasional compliance confirmation
                    if self._should_emit(f"ppec_{wid}_{zone_id}", tick, 300):
                        if self._rng.random() < 0.3:
                            events.append(self._make_event(
                                tick, "ppe_compliant", cameras, zone_id, zone_name,
                                worker_id=wid))

                # Restricted area entry
                if zone_cfg and zone_cfg.hazard_rating >= 4:
                    if self._should_emit(f"restricted_{wid}_{zone_id}", tick, 300):
                        events.append(self._make_event(
                            tick, "restricted_entry", cameras, zone_id, zone_name,
                            worker_id=wid))

                # Confined space entry
                if zone_cfg and zone_cfg.is_confined:
                    if w.get("task") == "confined_space_entry":
                        if self._should_emit(f"confined_{wid}_{zone_id}", tick, 120):
                            events.append(self._make_event(
                                tick, "confined_space_entry", cameras, zone_id, zone_name,
                                worker_id=wid))

            # Crowd detection
            if len(workers) >= 3:
                if self._should_emit(f"crowd_{zone_id}", tick, 120):
                    events.append(self._make_event(
                        tick, "crowd_detected", cameras, zone_id, zone_name,
                        count=len(workers)))

        # Vehicle events (random, ~every 10 min)
        if self._rng.random() < 0.002:
            zone_id = self._rng.choice([ZoneID.ZONE_A.value, ZoneID.ZONE_B.value])
            zone_cfg = ZONES.get(ZoneID(zone_id))
            zone_name = zone_cfg.name if zone_cfg else zone_id
            cameras = self.CAMERA_IDS.get(zone_id, ["CAM-GEN"])
            events.append(self._make_event(
                tick, "vehicle_detected", cameras, zone_id, zone_name))

        # Smoke detection (if high HC)
        for zone_id, hc_level in hc_concentration.items():
            if hc_level > 15.0:  # High HC can trigger visual detection
                if self._should_emit(f"smoke_{zone_id}", tick, 60):
                    zone_cfg = ZONES.get(ZoneID(zone_id) if zone_id.startswith("Zone") else None)
                    zone_name = zone_cfg.name if zone_cfg else zone_id
                    cameras = self.CAMERA_IDS.get(zone_id, ["CAM-GEN"])
                    events.append(self._make_event(
                        tick, "smoke_detected", cameras, zone_id, zone_name))

        return events

    def _should_emit(self, key: str, tick: int, interval: int) -> bool:
        """Check if enough time has passed to emit this event type again."""
        last = self._last_events.get(key, -9999)
        if tick - last >= interval:
            self._last_events[key] = tick
            return True
        return False

    def _make_event(self, tick: int, event_type: str,
                    cameras: list[str], zone_id: str, zone_name: str,
                    **kwargs) -> dict:
        template = self.EVENT_TEMPLATES.get(event_type, "Unknown event in {zone_name}")
        try:
            description = template.format(zone_name=zone_name, **kwargs)
        except KeyError:
            description = f"{event_type} in {zone_name}"

        return {
            "tick": tick,
            "camera_id": self._rng.choice(cameras),
            "zone_id": zone_id,
            "event_type": event_type,
            "description": description,
            "confidence": round(float(0.85 + self._rng.random() * 0.15), 2),
            **{k: v for k, v in kwargs.items() if k not in ("zone_name",)},
        }

    def reset(self, seed: int = 42) -> None:
        self._rng = np.random.default_rng(seed + 600)
        self._last_events.clear()
