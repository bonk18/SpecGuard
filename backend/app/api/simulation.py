import os
import sys
import time
from typing import Dict, Any, List
from pathlib import Path
from pydantic import BaseModel, Field
from fastapi import APIRouter
from datetime import datetime

# Setup paths for digital twin
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
digital_twin_path = os.path.join(BASE_DIR, "digital twin")
if os.path.exists(digital_twin_path):
    sys.path.append(digital_twin_path)
else:
    print(f"Warning: digital twin directory not found at {digital_twin_path}")

try:
    from simulator.plant import Plant, SCENARIO_CLASSES
    from simulator.config import ScenarioID
except ImportError as e:
    print(f"Warning: digital twin could not be imported. {e}")
    Plant = None

# Intelligence Integration
from app.api.intelligence import get_intelligence_service
from app.schemas import RiskEngineInput

router = APIRouter(prefix="/simulation", tags=["simulation"])

class SimulationController:
    def __init__(self):
        self.plant = Plant() if Plant else None
        self.is_running = True
        self.current_scenario = "normal"
        self.speed = 1.0
        self.last_state = None
        self.last_tick_time = time.time()
        self.zones_data = {}
        self.history = {} # type: Dict[str, List[float]]
        self.alerts = []
        
        # Intelligence cache
        self.last_ai_update = 0
        self.ai_cache = {}
        
        # Thread safety
        import threading
        self.lock = threading.Lock()
        
        # Instantiate intelligence service once
        self.intelligence_service = get_intelligence_service()

        if self.plant:
            self._set_scenario(self.current_scenario)

    def _set_scenario(self, scenario_id: str):
        self.current_scenario = scenario_id
        self.last_ai_update = 0  # Force immediate AI update on scenario change
        self.history = {}  # Clear history
        self.ai_cache = {} # Clear AI cache
        if Plant:
            sc_cls = SCENARIO_CLASSES.get(scenario_id, SCENARIO_CLASSES["normal"])
            self.plant.reset()
            self.plant.set_scenario(sc_cls(duration=10000))

    def tick(self):
        with self.lock:
            if not self.is_running or not self.plant or self.speed <= 0:
                return
            
            now = time.time()
            if now - self.last_tick_time >= (1.0 / self.speed):
                row = self.plant.tick()
                self._process_row(row)
                self.last_tick_time = now

    def _process_row(self, row: dict):
        self.last_state = row
        
        zone_ids = ["ZONE_A", "ZONE_B", "ZONE_C", "ZONE_D", "ZONE_E"]
        
        for zid in zone_ids:
            if zid not in self.zones_data:
                self.zones_data[zid] = {
                    "risk_score": 0,
                    "worker_count": 0,
                    "sensors": {
                        "hydrocarbon": {"value": 0.0},
                        "h2s": {"value": 0.0},
                        "oxygen": {"value": 20.9},
                        "pressure": {"value": 1.01},
                        "temperature": {"value": 30.0}
                    },
                    "cctv": [],
                    "workers": [],
                    "ai_fusion": {}
                }
            if zid not in self.history:
                self.history[zid] = []
        
        # Map some digital twin properties to Zone D for display
        base_risk = 5
        if self.current_scenario == "gas_leak":
            base_risk = 60
        elif self.current_scenario == "explosion_risk":
            base_risk = 90
        elif self.current_scenario == "ventilation_failure":
            base_risk = 55
        elif self.current_scenario == "pump_failure":
            base_risk = 70
        elif self.current_scenario == "hot_work_gas_leak":
            base_risk = 85
        elif self.current_scenario == "confined_space":
            base_risk = 65
            
        self.zones_data["ZONE_D"]["risk_score"] = base_risk
        self.zones_data["ZONE_D"]["worker_count"] = 3 if self.current_scenario != "normal" else 2
        
        import math
        t = time.time()
        
        hc_val = row.get("hc_gas_lel", 0.0)
        h2s_val = row.get("h2s_ppm", 0.0)
        pressure_val = row.get("pipeline_pressure", 1.01)
        temp_val = row.get("pipeline_temperature", 120.0)
        
        # Normalize wild pressure values from digital twin
        if pressure_val > 100:
            pressure_val = 1.0 + (pressure_val % 2.0)
            
        # Apply scenario-specific realistic boosts
        if self.current_scenario in ["gas_leak", "ventilation_failure"]:
            hc_val += 25.0 + math.sin(t * 0.5) * 5.0
            h2s_val += 50.0 + math.cos(t * 0.3) * 10.0
        elif self.current_scenario in ["explosion_risk", "hot_work_gas_leak"]:
            pressure_val += 8.0 + math.sin(t * 0.8) * 2.0
            hc_val += 10.0 + math.sin(t * 0.2) * 2.0
            temp_val += 40.0 + math.cos(t * 0.5) * 5.0
        elif self.current_scenario == "confined_space":
            h2s_val += 20.0 + math.sin(t * 0.4) * 5.0
            pressure_val += 3.0 + math.cos(t * 0.6) * 1.0
            
        hc_val = max(0.0, hc_val)
        h2s_val = max(0.0, h2s_val)
        pressure_val = max(0.0, pressure_val)
        
        self.zones_data["ZONE_D"]["sensors"]["hydrocarbon"]["value"] = hc_val
        self.history["ZONE_D"].append(hc_val)
        if len(self.history["ZONE_D"]) > 20:
            self.history["ZONE_D"].pop(0)
            
        self.zones_data["ZONE_D"]["sensors"]["h2s"]["value"] = h2s_val
        self.zones_data["ZONE_D"]["sensors"]["oxygen"]["value"] = row.get("oxygen_pct", 20.9)
        self.zones_data["ZONE_D"]["sensors"]["temperature"]["value"] = temp_val
        self.zones_data["ZONE_D"]["sensors"]["pressure"]["value"] = pressure_val

        self.alerts = []
        if base_risk > 50:
            self.alerts.append({
                "zone_id": "ZONE_D",
                "primary_hazard": self.current_scenario.replace("_", " ").upper(),
                "explanation": row.get("event_label", "Anomalous readings detected"),
                "alert_id": "ALT-" + str(int(time.time()))
            })

sim_ctrl = SimulationController()

class StartRequest(BaseModel):
    scenario: str
    speed: float = Field(1.0, gt=0.0)

@router.post("/start")
def start_sim(req: StartRequest):
    with sim_ctrl.lock:
        sim_ctrl._set_scenario(req.scenario)
        sim_ctrl.speed = req.speed
        sim_ctrl.is_running = True
    return {"status": "started"}

@router.post("/pause")
def pause_sim():
    with sim_ctrl.lock:
        sim_ctrl.is_running = False
    return {"status": "paused"}

@router.post("/resume")
def resume_sim():
    with sim_ctrl.lock:
        sim_ctrl.is_running = True
    return {"status": "resumed"}

@router.post("/step")
def step_sim():
    sim_ctrl.tick()
    return {"status": "stepped"}

@router.get("/state")
def get_state(zone_id: str = "ZONE_D"):
    with sim_ctrl.lock:
        sim_ctrl.tick()
        
        # Intelligence trigger for selected zone
        now = time.time()
        if now - sim_ctrl.last_ai_update > 2.0:  # Update AI every 2 seconds
            sim_ctrl.last_ai_update = now
            if zone_id in sim_ctrl.zones_data:
                zdata = sim_ctrl.zones_data[zone_id]
                base_risk = float(zdata["risk_score"])
                
                if base_risk > 50:
                    # Map simulation scenarios to RiskType
                    mapped_risk = "UNKNOWN"
                    if sim_ctrl.current_scenario == "ventilation_failure":
                        mapped_risk = "TOXIC_EXPOSURE"
                    elif sim_ctrl.current_scenario == "gas_leak":
                        mapped_risk = "FIRE"
                    elif sim_ctrl.current_scenario == "explosion_risk":
                        mapped_risk = "FIRE_EXPLOSION"
                    elif sim_ctrl.current_scenario == "hot_work_gas_leak":
                        mapped_risk = "FIRE_EXPLOSION"
                    elif sim_ctrl.current_scenario == "pump_failure":
                        mapped_risk = "EQUIPMENT_FAILURE"
                    elif sim_ctrl.current_scenario == "confined_space":
                        mapped_risk = "CONFINED_SPACE"
                        
                    factor_mapping = {
                        "ventilation_failure": "VENTILATION_OFF",
                        "gas_leak": "RISING_H2S",
                        "pump_failure": "ABNORMAL_FLOW",
                        "hot_work_gas_leak": "HOT_WORK_ACTIVE",
                        "confined_space": "CONFINED_SPACE_ACTIVE",
                        "explosion_risk": "RISING_LEL"
                    }
                    mapped_factor = factor_mapping.get(sim_ctrl.current_scenario, "UNKNOWN")

                    # Construct input
                    risk_input = RiskEngineInput(
                        alert_id="ALT-" + str(int(now)),
                        timestamp=datetime.fromtimestamp(now),
                        zone_id=zone_id,
                        equipment_ids=["DC-100"],
                        risk_type=mapped_risk,
                        risk_score=float(zdata["risk_score"]) / 100.0,
                        severity="HIGH",
                        predicted_incident=sim_ctrl.current_scenario.replace("_", " ").title() + " Potential Incident",
                        contributing_factors=[mapped_factor],
                        sensor_evidence={
                            "hydrocarbon": zdata["sensors"]["hydrocarbon"]["value"],
                            "temperature": zdata["sensors"]["temperature"]["value"]
                        },
                        estimated_lead_time_minutes=2.0
                    )
                    
                    try:
                        # Call Intelligence Service
                        response = sim_ctrl.intelligence_service.generate(risk_input)
                        
                        sim_ctrl.ai_cache[zone_id] = {
                            "triggered_rules": [a.title for a in response.recommended_actions[:2]],
                            "primary_hazard": response.executive_summary.split(".")[0],
                            "explanation": response.risk_explanation,
                            "confidence": response.intelligence_confidence,
                            "lead_time_vs_baseline": risk_input.estimated_lead_time_minutes * 60
                        }
                    except Exception as e:
                        sim_ctrl.ai_cache[zone_id] = {
                            "triggered_rules": ["AI_ERROR"],
                            "primary_hazard": "Intelligence Unavailable",
                            "explanation": f"Failed to generate intelligence: {str(e)}",
                            "confidence": 0.0,
                            "lead_time_vs_baseline": 0.0
                        }
                else:
                    sim_ctrl.ai_cache[zone_id] = {
                        "triggered_rules": [],
                        "primary_hazard": "NONE / HEALTHY",
                        "explanation": "Sensors reporting normal operations. No hazard indicators detected.",
                        "confidence": 1.0,
                        "lead_time_vs_baseline": 0.0
                    }
                    
            if zone_id in sim_ctrl.zones_data:
                sim_ctrl.zones_data[zone_id]["ai_fusion"] = sim_ctrl.ai_cache.get(zone_id, {})
            
        return {
            "simulation": {
                "scenario": sim_ctrl.current_scenario,
                "is_running": sim_ctrl.is_running
            },
            "zones": {k: {"risk_score": v["risk_score"], "worker_count": v["worker_count"]} for k,v in sim_ctrl.zones_data.items()},
            "selected_zone": sim_ctrl.zones_data.get(zone_id, {}),
            "history": sim_ctrl.history,
            "alerts": sim_ctrl.alerts
        }
