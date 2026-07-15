from pydantic import BaseModel
from datetime import datetime
from typing import List


class Intervention(BaseModel):
    intervention_id: str

    alert_id: str

    recommended_actions: List[str]

    priority: str

    status: str

    generated_at: datetime