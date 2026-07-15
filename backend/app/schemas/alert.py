from pydantic import BaseModel
from datetime import datetime
from typing import List


class RiskAlert(BaseModel):
    alert_id: str

    zone_id: str

    risk_score: float

    severity: str

    predicted_incident: str

    contributing_signals: List[str]

    timestamp: datetime