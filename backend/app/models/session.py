from pydantic import BaseModel, Field
from typing import List, Optional

class StepSubmit(BaseModel):
    session_id: str
    proposed_action: str
    action_type: str = "code_edit"  # code_edit, terminal_cmd, search, plan, message
    reasoning: str
    context_snapshot: Optional[str] = ""

class StepResponse(BaseModel):
    id: str
    session_id: str
    step_number: int
    proposed_action: str
    action_type: str
    reasoning: str
    context_snapshot: str
    drift_score: float
    drift_tier: str
    intervention_triggered: bool
    intervention_details: str
    execution_result: str
    timestamp: str

class SessionCreate(BaseModel):
    goal_id: str
    session_name: str
    session_number: Optional[int] = 1

class SessionResponse(BaseModel):
    id: str
    goal_id: str
    session_name: str
    session_number: int
    status: str
    started_at: str
    last_active_at: str
    summary: str
    steps_count: int = 0
    average_drift: float = 0.0
    interventions_count: int = 0

class DriftAuditResponse(BaseModel):
    id: str
    session_id: str
    step_id: str
    semantic_score: float
    constraint_score: float
    horizon_score: float
    aggregate_drift: float
    status: str
    feedback_prompt: str
    timestamp: str
