from pydantic import BaseModel
from datetime import datetime


class SensorReading(BaseModel):
    sensor_id: str
    zone_id: str

    gas_level: float
    temperature: float
    pressure: float

    ventilation_status: bool
    equipment_status: str

    timestamp: datetime