from pydantic import BaseModel, Field
from typing import List, Optional

class MilestoneCreate(BaseModel):
    title: str
    description: str
    order_index: int
    dependencies: List[str] = Field(default_factory=list)

class MilestoneUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None  # pending, in_progress, completed, skipped
    progress: Optional[float] = None
    dependencies: Optional[List[str]] = None

class MilestoneResponse(BaseModel):
    id: str
    goal_id: str
    order_index: int
    title: str
    description: str
    status: str
    progress: float
    dependencies: List[str]

class MilestoneParseItem(BaseModel):
    title: str
    description: str
    order_index: int
    dependencies: List[str] = Field(default_factory=list)

class GoalParseRequest(BaseModel):
    text: str

class GoalParseResponse(BaseModel):
    title: str
    intent: str
    invariant_constraints: List[str]
    acceptance_criteria: List[str]
    anti_goals: List[str]
    suggested_milestones: List[MilestoneParseItem]
    initial_active_milestone: str
    missing_information: List[str] = Field(default_factory=list)
    clarifying_questions: List[str] = Field(default_factory=list)
    analysis_mode: str
    detected_domain: str

class GoalCreate(BaseModel):
    title: str
    intent: str
    invariant_constraints: List[str]
    acceptance_criteria: List[str]
    anti_goals: List[str]
    milestones: Optional[List[MilestoneCreate]] = None

class GoalUpdate(BaseModel):
    title: Optional[str] = None
    intent: Optional[str] = None
    invariant_constraints: Optional[List[str]] = None
    acceptance_criteria: Optional[List[str]] = None
    anti_goals: Optional[List[str]] = None
    status: Optional[str] = None

class GoalResponse(BaseModel):
    id: str
    title: str
    intent: str
    invariant_constraints: List[str]
    acceptance_criteria: List[str]
    anti_goals: List[str]
    current_version: int
    status: str
    created_at: str
    updated_at: str
    milestones: List[MilestoneResponse] = Field(default_factory=list)
    overall_progress: float = 0.0

class GoalVersionResponse(BaseModel):
    id: str
    goal_id: str
    version_num: int
    reason: str
    diff_summary: str
    approved_by: str
    created_at: str

