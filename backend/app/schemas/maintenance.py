"""Canonical maintenance-event contract.

The misspelled ``maintainance`` module remains as a compatibility shim for
existing imports. New code should import this correctly named module.
"""

from datetime import datetime

from pydantic import BaseModel


class MaintenanceEvent(BaseModel):
    maintenance_id: str
    equipment_id: str
    equipment_name: str
    zone_id: str
    maintenance_type: str
    status: str
    assigned_team: str
    timestamp: datetime


__all__ = ["MaintenanceEvent"]
