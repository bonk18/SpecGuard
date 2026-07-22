from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import os

from app.api.health import router as health_router
from app.api.sensor import router as sensor_router
from app.api.permit import router as permit_router
from app.api.maintenance import router as maintenance_router
from app.api.cctv import router as cctv_router
from app.api.alerts import router as alerts_router
from app.api.interventions import router as interventions_router
from app.api.intelligence import router as intelligence_router
from app.api.simulation import router as simulation_router

from app.database.database import engine
from app.database.base import Base

app= FastAPI(
    title="Sentinel AI Backend",
    description="Industrial Safety Intelligence Platform",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Base.metadata.create_all(bind=engine)

app.include_router(health_router)
app.include_router(sensor_router)
app.include_router(permit_router)
app.include_router(maintenance_router)
app.include_router(cctv_router)
app.include_router(alerts_router)
app.include_router(interventions_router)
app.include_router(intelligence_router)
app.include_router(simulation_router)

# Mount frontend
FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "frontend")
if os.path.exists(FRONTEND_DIR):
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
else:
    print(f"Warning: frontend directory not found at {FRONTEND_DIR}")