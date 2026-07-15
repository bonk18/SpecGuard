from pydantic import BaseModel
from datetime import datetime


class Permit(BaseModel):
    permit_id: str
    permit_type: str

    zone_id: str

    issued_to: str

    status: str

    start_time: datetime
    end_time: datetime