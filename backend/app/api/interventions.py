from fastapi import APIRouter
from pydantic import BaseModel
import time

router = APIRouter(
    prefix="/interventions",
    tags=["Interventions"]
)

class InterventionRequest(BaseModel):
    zone_id: str
    action_taken: str

@router.get("/")
def get_interventions():
    return {
        "message": "Coming Soon"
    }

@router.post("/")
def trigger_intervention(req: InterventionRequest):
    return {
        "intervention_id": f"INT-{int(time.time())}",
        "status": "success",
        "action": req.action_taken,
        "zone": req.zone_id
    }