from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any
from backend.app.services.simulation_service import simulation_service

router = APIRouter(prefix="/api/simulations", tags=["simulations"])

@router.get("/scenarios", response_model=List[Dict[str, Any]])
def list_scenarios():
    return simulation_service.get_scenarios()

@router.post("/run/{scenario_id}")
def run_simulation(scenario_id: str):
    valid_ids = [s["id"] for s in simulation_service.get_scenarios()]
    if scenario_id not in valid_ids:
        raise HTTPException(status_code=404, detail="Scenario not found")
    return simulation_service.run_benchmark(scenario_id)
