import json
import uuid
from typing import List
from fastapi import APIRouter, HTTPException, Depends
from backend.app.database import db_session
from backend.app.models.goal import (
    GoalCreate, GoalUpdate, GoalResponse, MilestoneCreate, 
    MilestoneUpdate, MilestoneResponse, GoalVersionResponse,
    GoalParseRequest, GoalParseResponse
)
from backend.app.services.regrounding import regrounding_engine
from backend.app.services.goal_parser import goal_parsing_service

router = APIRouter(prefix="/api/goals", tags=["goals"])

@router.post("/parse", response_model=GoalParseResponse)
def parse_goal_endpoint(payload: GoalParseRequest):
    try:
        return goal_parsing_service.parse(payload.text)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Parsing error: {str(e)}")


@router.get("", response_model=List[GoalResponse])
def list_goals():
    with db_session() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM goals ORDER BY created_at DESC")
        goal_rows = cursor.fetchall()
        
        result = []
        for g in goal_rows:
            cursor.execute("SELECT * FROM milestones WHERE goal_id = ? ORDER BY order_index ASC", (g["id"],))
            ms_rows = cursor.fetchall()
            milestones = []
            total_progress = 0.0
            for m in ms_rows:
                milestones.append(MilestoneResponse(
                    id=m["id"],
                    goal_id=m["goal_id"],
                    order_index=m["order_index"],
                    title=m["title"],
                    description=m["description"],
                    status=m["status"],
                    progress=m["progress"],
                    dependencies=json.loads(m["dependencies"])
                ))
                total_progress += m["progress"]

            avg_progress = round(total_progress / len(milestones), 2) if milestones else 0.0
            result.append(GoalResponse(
                id=g["id"],
                title=g["title"],
                intent=g["intent"],
                invariant_constraints=json.loads(g["invariant_constraints"]),
                acceptance_criteria=json.loads(g["acceptance_criteria"]),
                anti_goals=json.loads(g["anti_goals"]),
                current_version=g["current_version"],
                status=g["status"],
                created_at=str(g["created_at"]),
                updated_at=str(g["updated_at"]),
                milestones=milestones,
                overall_progress=avg_progress
            ))
        return result

@router.get("/{goal_id}", response_model=GoalResponse)
def get_goal(goal_id: str):
    with db_session() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM goals WHERE id = ?", (goal_id,))
        g = cursor.fetchone()
        if not g:
            raise HTTPException(status_code=404, detail="Goal not found")
        
        cursor.execute("SELECT * FROM milestones WHERE goal_id = ? ORDER BY order_index ASC", (goal_id,))
        ms_rows = cursor.fetchall()
        milestones = []
        total_prog = 0.0
        for m in ms_rows:
            milestones.append(MilestoneResponse(
                id=m["id"],
                goal_id=m["goal_id"],
                order_index=m["order_index"],
                title=m["title"],
                description=m["description"],
                status=m["status"],
                progress=m["progress"],
                dependencies=json.loads(m["dependencies"])
            ))
            total_prog += m["progress"]

        avg_prog = round(total_prog / len(milestones), 2) if milestones else 0.0
        return GoalResponse(
            id=g["id"],
            title=g["title"],
            intent=g["intent"],
            invariant_constraints=json.loads(g["invariant_constraints"]),
            acceptance_criteria=json.loads(g["acceptance_criteria"]),
            anti_goals=json.loads(g["anti_goals"]),
            current_version=g["current_version"],
            status=g["status"],
            created_at=str(g["created_at"]),
            updated_at=str(g["updated_at"]),
            milestones=milestones,
            overall_progress=avg_prog
        )

@router.post("", response_model=GoalResponse)
def create_goal(payload: GoalCreate):
    with db_session() as conn:
        cursor = conn.cursor()
        goal_id = f"goal_{uuid.uuid4().hex[:8]}"
        cursor.execute("""
        INSERT INTO goals (id, title, intent, invariant_constraints, acceptance_criteria, anti_goals, current_version, status)
        VALUES (?, ?, ?, ?, ?, ?, 1, 'active')
        """, (
            goal_id,
            payload.title,
            payload.intent,
            json.dumps(payload.invariant_constraints),
            json.dumps(payload.acceptance_criteria),
            json.dumps(payload.anti_goals)
        ))

        # Record initial version
        cursor.execute("""
        INSERT INTO goal_versions (id, goal_id, version_num, reason, diff_summary, approved_by)
        VALUES (?, ?, 1, 'Initial Baseline Goal Definition', 'Created initial invariants and criteria.', 'USER')
        """, (str(uuid.uuid4()), goal_id))

        # Insert milestones if provided
        created_milestones = []
        if payload.milestones:
            for idx, m in enumerate(payload.milestones):
                ms_id = f"ms_{uuid.uuid4().hex[:6]}"
                init_status = "in_progress" if idx == 0 else "pending"
                cursor.execute("""
                INSERT INTO milestones (id, goal_id, order_index, title, description, status, progress, dependencies)
                VALUES (?, ?, ?, ?, ?, ?, 0.0, ?)
                """, (ms_id, goal_id, m.order_index, m.title, m.description, init_status, json.dumps(m.dependencies)))
                created_milestones.append(MilestoneResponse(
                    id=ms_id,
                    goal_id=goal_id,
                    order_index=m.order_index,
                    title=m.title,
                    description=m.description,
                    status=init_status,
                    progress=0.0,
                    dependencies=m.dependencies
                ))

        # Create initial execution session for this goal
        init_session_id = f"session_{goal_id}_init"
        cursor.execute("""
        INSERT INTO sessions (id, goal_id, session_name, session_number, status, summary)
        VALUES (?, ?, 'Mission Initialization Session', 1, 'active', 'Initial execution environment for goal.')
        """, (init_session_id, goal_id))


        return GoalResponse(
            id=goal_id,
            title=payload.title,
            intent=payload.intent,
            invariant_constraints=payload.invariant_constraints,
            acceptance_criteria=payload.acceptance_criteria,
            anti_goals=payload.anti_goals,
            current_version=1,
            status="active",
            created_at="now",
            updated_at="now",
            milestones=created_milestones,
            overall_progress=0.0
        )

@router.get("/{goal_id}/versions", response_model=List[GoalVersionResponse])
def get_goal_versions(goal_id: str):
    with db_session() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM goal_versions WHERE goal_id = ? ORDER BY version_num DESC", (goal_id,))
        rows = cursor.fetchall()
        return [
            GoalVersionResponse(
                id=r["id"],
                goal_id=r["goal_id"],
                version_num=r["version_num"],
                reason=r["reason"],
                diff_summary=r["diff_summary"],
                approved_by=r["approved_by"],
                created_at=str(r["created_at"])
            ) for r in rows
        ]

@router.get("/{goal_id}/grounding-prompt")
def get_grounding_prompt(goal_id: str):
    with db_session() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM goals WHERE id = ?", (goal_id,))
        g = cursor.fetchone()
        if not g:
            raise HTTPException(status_code=404, detail="Goal not found")

        cursor.execute("SELECT * FROM milestones WHERE goal_id = ? AND status = 'in_progress' LIMIT 1", (goal_id,))
        active_ms = cursor.fetchone()
        if not active_ms:
            cursor.execute("SELECT * FROM milestones WHERE goal_id = ? AND status = 'pending' ORDER BY order_index ASC LIMIT 1", (goal_id,))
            active_ms = cursor.fetchone()

        active_dict = dict(active_ms) if active_ms else {"title": "General Execution", "description": "Complete core requirements", "progress": 0.0}

        prompt = regrounding_engine.generate_grounding_prompt(
            goal_title=g["title"],
            goal_intent=g["intent"],
            invariant_constraints=json.loads(g["invariant_constraints"]),
            active_milestone=active_dict,
            anti_goals=json.loads(g["anti_goals"])
        )
        return {"goal_id": goal_id, "grounding_prompt": prompt}

@router.put("/milestones/{milestone_id}")
def update_milestone(milestone_id: str, payload: MilestoneUpdate):
    with db_session() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM milestones WHERE id = ?", (milestone_id,))
        ms = cursor.fetchone()
        if not ms:
            raise HTTPException(status_code=404, detail="Milestone not found")

        title = payload.title if payload.title is not None else ms["title"]
        desc = payload.description if payload.description is not None else ms["description"]
        status = payload.status if payload.status is not None else ms["status"]
        progress = payload.progress if payload.progress is not None else ms["progress"]

        cursor.execute("""
        UPDATE milestones SET title = ?, description = ?, status = ?, progress = ? WHERE id = ?
        """, (title, desc, status, progress, milestone_id))

        return {"status": "success", "milestone_id": milestone_id}
