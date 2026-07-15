from pydantic import BaseModel
from datetime import datetime


class CCTVEvent(BaseModel):
    event_id: str

    camera_id: str

    zone_id: str

    workers_detected: int

    ppe_compliance: bool

    timestamp: datetime