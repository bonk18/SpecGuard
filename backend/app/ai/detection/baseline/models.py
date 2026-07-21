from pydantic import BaseModel
from typing import Optional

class BaselineResult(BaseModel):
    alarm_triggered: bool
    alarm_level: Optional[str]
    sensor: str
    value: float
    threshold: float
    detection_time: str
    zone: str
    equipment: Optional[str]
    data_quality: str
