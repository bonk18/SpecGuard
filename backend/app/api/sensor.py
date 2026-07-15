from fastapi import APIRouter

router= APIRouter(
    prefix="/sensors",
    tags=["Sensors"]
)

@router.post("/")
def receive_sensor_data():
    return {
        "message": "Coming Soon"
    }