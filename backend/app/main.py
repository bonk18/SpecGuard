from fastapi import FastAPI

from app.api.health import router as health_router
from app.api.sensor import router as sensor_router
from app.api.permit import router as permit_router
from app.api.maintenance import router as maintenance_router
from app.api.cctv import router as cctv_router
from app.api.alerts import router as alerts_router
from app.api.interventions import router as interventions_router

from app.database.database import engine
from app.database.base import Base

app= FastAPI(
    title="Sentinel AI Backend",
    description="Industrial Safety Intelligence Platform",
    version="1.0.0"
)

Base.metadata.create_all(bind=engine)

app.include_router(health_router)
app.include_router(sensor_router)
app.include_router(permit_router)
app.include_router(maintenance_router)
app.include_router(cctv_router)
app.include_router(alerts_router)
app.include_router(interventions_router)