"""
Permit-to-Work management.

Manages Hot Work, Confined Space, Electrical, and Line Breaking permits
with lifecycle tracking and conflict detection.
"""

import numpy as np

from simulator.config import PermitType, PermitStatus, ZoneID


class Permit:
    """Single permit-to-work instance."""
    __slots__ = ('permit_id', 'permit_type', 'zone_id', 'equipment_id',
                 'status', 'requested_tick', 'approved_tick', 'activated_tick',
                 'closed_tick', 'issuer', 'holder', 'duration',
                 'gas_test_required', 'gas_test_done', 'risk_assessment')

    def __init__(self, permit_id: str, permit_type: PermitType,
                 zone_id: str, equipment_id: str = "",
                 issuer: str = "", holder: str = "",
                 duration: int = 3600):
        self.permit_id = permit_id
        self.permit_type = permit_type
        self.zone_id = zone_id
        self.equipment_id = equipment_id
        self.status = PermitStatus.REQUESTED
        self.requested_tick = 0
        self.approved_tick = 0
        self.activated_tick = 0
        self.closed_tick = 0
        self.issuer = issuer
        self.holder = holder
        self.duration = duration
        self.gas_test_required = permit_type in (
            PermitType.HOT_WORK, PermitType.CONFINED_SPACE)
        self.gas_test_done = False
        self.risk_assessment = "standard"

    def to_dict(self) -> dict:
        return {
            "permit_id": self.permit_id,
            "permit_type": self.permit_type.value,
            "zone_id": self.zone_id,
            "equipment_id": self.equipment_id,
            "status": self.status.value,
            "issuer": self.issuer,
            "holder": self.holder,
            "gas_test_required": self.gas_test_required,
            "gas_test_done": self.gas_test_done,
            "risk_assessment": self.risk_assessment,
        }


class PermitToWorkManager:
    """Manages all active permits with conflict detection."""

    def __init__(self, seed: int = 42):
        self._rng = np.random.default_rng(seed + 300)
        self.permits: dict[str, Permit] = {}
        self._next_id = 1
        self._conflicts: list[dict] = []

    def create_permit(self, permit_type: PermitType, zone_id: str,
                      equipment_id: str = "", issuer: str = "W005",
                      holder: str = "W003", duration: int = 3600,
                      tick: int = 0) -> Permit:
        """Create a new permit."""
        pid = f"PTW-{self._next_id:04d}"
        self._next_id += 1
        permit = Permit(pid, permit_type, zone_id, equipment_id,
                        issuer, holder, duration)
        permit.requested_tick = tick
        self.permits[pid] = permit
        return permit

    def approve_permit(self, permit_id: str, tick: int) -> None:
        p = self.permits.get(permit_id)
        if p and p.status == PermitStatus.REQUESTED:
            p.status = PermitStatus.APPROVED
            p.approved_tick = tick

    def activate_permit(self, permit_id: str, tick: int) -> None:
        p = self.permits.get(permit_id)
        if p and p.status == PermitStatus.APPROVED:
            p.status = PermitStatus.ACTIVE
            p.activated_tick = tick

    def suspend_permit(self, permit_id: str) -> None:
        p = self.permits.get(permit_id)
        if p and p.status == PermitStatus.ACTIVE:
            p.status = PermitStatus.SUSPENDED

    def close_permit(self, permit_id: str, tick: int) -> None:
        p = self.permits.get(permit_id)
        if p:
            p.status = PermitStatus.CLOSED
            p.closed_tick = tick

    def update(self, tick: int, gas_levels: dict[str, float] | None = None) -> list[dict]:
        """Update permit states and detect conflicts.

        Args:
            tick: Current simulation tick
            gas_levels: Dict of zone_id → HC %LEL level

        Returns:
            List of conflict/event dicts
        """
        events = []
        gas_levels = gas_levels or {}

        for pid, permit in list(self.permits.items()):
            # Auto-approve after 300s
            if (permit.status == PermitStatus.REQUESTED and
                    tick - permit.requested_tick > 300):
                self.approve_permit(pid, tick)
                events.append({
                    "event": "permit_approved",
                    "permit_id": pid,
                    "permit_type": permit.permit_type.value,
                })

            # Auto-activate after approval
            if (permit.status == PermitStatus.APPROVED and
                    tick - permit.approved_tick > 60):
                self.activate_permit(pid, tick)
                events.append({
                    "event": "permit_activated",
                    "permit_id": pid,
                    "permit_type": permit.permit_type.value,
                })

            # Duration expiry
            if (permit.status == PermitStatus.ACTIVE and
                    tick - permit.activated_tick > permit.duration):
                self.close_permit(pid, tick)
                events.append({
                    "event": "permit_expired",
                    "permit_id": pid,
                })

            # Conflict detection: hot work + gas present
            if (permit.status == PermitStatus.ACTIVE and
                    permit.permit_type == PermitType.HOT_WORK):
                zone_hc = gas_levels.get(permit.zone_id, 0.0)
                if zone_hc > 5.0:  # >5% LEL with hot work = danger
                    self.suspend_permit(pid)
                    conflict = {
                        "event": "permit_conflict",
                        "type": "hot_work_gas_detected",
                        "permit_id": pid,
                        "zone_id": permit.zone_id,
                        "hc_level": zone_hc,
                        "severity": "CRITICAL",
                    }
                    events.append(conflict)
                    self._conflicts.append(conflict)

        return events

    def get_active_permits(self) -> list[dict]:
        """Return all active permits as dicts."""
        return [p.to_dict() for p in self.permits.values()
                if p.status in (PermitStatus.ACTIVE, PermitStatus.APPROVED)]

    def get_active_hot_work_zones(self) -> list[str]:
        """Return zones with active hot work permits."""
        return [p.zone_id for p in self.permits.values()
                if p.permit_type == PermitType.HOT_WORK and
                p.status == PermitStatus.ACTIVE]

    def has_active_permit(self, permit_type: PermitType,
                          zone_id: str | None = None) -> bool:
        """Check if a permit of given type is active."""
        for p in self.permits.values():
            if p.permit_type == permit_type and p.status == PermitStatus.ACTIVE:
                if zone_id is None or p.zone_id == zone_id:
                    return True
        return False

    def get_conflicts(self) -> list[dict]:
        return list(self._conflicts)

    def get_current_state(self, tick: int) -> dict:
        """Return summarized permit state for the current tick."""
        active = self.get_active_permits()
        return {
            "hot_work_active": any(p["permit_type"] == "hot_work" and
                                   p["status"] == "active" for p in active),
            "confined_space_active": any(p["permit_type"] == "confined_space" and
                                         p["status"] == "active" for p in active),
            "electrical_active": any(p["permit_type"] == "electrical" and
                                     p["status"] == "active" for p in active),
            "line_breaking_active": any(p["permit_type"] == "line_breaking" and
                                        p["status"] == "active" for p in active),
            "active_permits": active,
            "conflicts": [c for c in self._conflicts
                         if c.get("severity") == "CRITICAL"],
        }

    def reset(self, seed: int = 42) -> None:
        self._rng = np.random.default_rng(seed + 300)
        self.permits.clear()
        self._next_id = 1
        self._conflicts.clear()
