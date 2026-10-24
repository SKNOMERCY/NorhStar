from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class EvolutionProposalCreate(BaseModel):
    goal_id: str
    session_id: Optional[str] = None
    rfc_title: str
    justification: str
    proposed_changes: Dict[str, Any]  # Updated invariant_constraints, acceptance_criteria, etc.

class EvolutionDecision(BaseModel):
    approved: bool
    reviewed_by: str = "HUMAN_SUPERVISOR"
    comment: Optional[str] = ""

class EvolutionProposalResponse(BaseModel):
    id: str
    goal_id: str
    session_id: Optional[str]
    rfc_title: str
    justification: str
    proposed_changes: Dict[str, Any]
    classification: str  # EVOLUTION vs DRIFT
    confidence: float
    status: str          # pending, approved, rejected
    created_at: str
