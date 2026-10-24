from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from backend.app.services.ai_provider import ai_provider
from backend.app.services.tool_guardrails import tool_guardrails
from backend.app.services.agent_orchestrator import agent_orchestrator

router = APIRouter(prefix="/api/orchestrator", tags=["orchestrator"])

class RunStepRequest(BaseModel):
    session_id: str
    manual_action: Optional[str] = None
    manual_reasoning: Optional[str] = None
    manual_tool_name: Optional[str] = None
    manual_tool_args: Optional[Dict[str, Any]] = None

class RunLoopRequest(BaseModel):
    session_id: str
    max_steps: Optional[int] = 3

@router.get("/status")
def get_orchestrator_status():
    provider_info = ai_provider.get_provider_status()
    tools = tool_guardrails.get_allowlist_specs()
    return {
        "status": "operational",
        "provider_info": provider_info,
        "allowlisted_tools": [t["name"] for t in tools],
        "tool_count": len(tools)
    }

@router.get("/tools")
def get_tools():
    return tool_guardrails.get_allowlist_specs()

@router.post("/step")
def run_orchestrator_step(payload: RunStepRequest):
    try:
        result = agent_orchestrator.execute_step(
            session_id=payload.session_id,
            manual_action=payload.manual_action,
            manual_reasoning=payload.manual_reasoning,
            manual_tool_name=payload.manual_tool_name,
            manual_tool_args=payload.manual_tool_args
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Orchestration failure: {str(e)}")

@router.post("/loop")
def run_orchestrator_loop(payload: RunLoopRequest):
    steps_executed = []
    max_count = min(5, payload.max_steps or 3)
    
    for _ in range(max_count):
        step_res = agent_orchestrator.execute_step(session_id=payload.session_id)
        steps_executed.append(step_res)
        if step_res.get("circuit_breaker_fired"):
            # Halt loop on circuit breaker
            break

    return {
        "session_id": payload.session_id,
        "steps_run": len(steps_executed),
        "steps": steps_executed
    }
