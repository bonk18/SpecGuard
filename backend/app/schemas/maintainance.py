from pydantic import BaseModel
from datetime import datetime


class MaintenanceEvent(BaseModel):
    maintenance_id: str

    equipment_id: str
    equipment_name: str

    zone_id: str

    maintenance_type: str

    status: str

    assigned_team: str

    timestamp: datetime