import json
import uuid
from typing import List
from fastapi import APIRouter, HTTPException
from backend.app.database import db_session
from backend.app.models.session import (
    SessionCreate, SessionResponse, StepSubmit, StepResponse, DriftAuditResponse
)
from backend.app.services.drift_detector import drift_detector
from backend.app.services.regrounding import regrounding_engine

router = APIRouter(prefix="/api/sessions", tags=["sessions"])

@router.get("", response_model=List[SessionResponse])
def list_sessions(goal_id: str = None):
    with db_session() as conn:
        cursor = conn.cursor()
        query = "SELECT * FROM sessions"
        params = ()
        if goal_id:
            query += " WHERE goal_id = ?"
            params = (goal_id,)
        query += " ORDER BY session_number DESC, started_at DESC"
        
        cursor.execute(query, params)
        rows = cursor.fetchall()

        result = []
        for r in rows:
            cursor.execute("SELECT COUNT(*), AVG(drift_score), SUM(intervention_triggered) FROM steps WHERE session_id = ?", (r["id"],))
            s_count, avg_drift, interventions = cursor.fetchone()
            result.append(SessionResponse(
                id=r["id"],
                goal_id=r["goal_id"],
                session_name=r["session_name"],
                session_number=r["session_number"],
                status=r["status"],
                started_at=str(r["started_at"]),
                last_active_at=str(r["last_active_at"]),
                summary=r["summary"] or "",
                steps_count=s_count or 0,
                average_drift=round(avg_drift or 0.0, 3),
                interventions_count=interventions or 0
            ))
        return result

@router.post("", response_model=SessionResponse)
def create_session(payload: SessionCreate):
    with db_session() as conn:
        cursor = conn.cursor()
        session_id = f"session_{uuid.uuid4().hex[:8]}"
        cursor.execute("""
        INSERT INTO sessions (id, goal_id, session_name, session_number, status, summary)
        VALUES (?, ?, ?, ?, 'active', '')
        """, (session_id, payload.goal_id, payload.session_name, payload.session_number or 1))

        return SessionResponse(
            id=session_id,
            goal_id=payload.goal_id,
            session_name=payload.session_name,
            session_number=payload.session_number or 1,
            status="active",
            started_at="now",
            last_active_at="now",
            summary="",
            steps_count=0,
            average_drift=0.0,
            interventions_count=0
        )

@router.get("/{session_id}/steps", response_model=List[StepResponse])
def get_session_steps(session_id: str):
    with db_session() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM steps WHERE session_id = ? ORDER BY step_number ASC", (session_id,))
        rows = cursor.fetchall()
        return [
            StepResponse(
                id=r["id"],
                session_id=r["session_id"],
                step_number=r["step_number"],
                proposed_action=r["proposed_action"],
                action_type=r["action_type"],
                reasoning=r["reasoning"],
                context_snapshot=r["context_snapshot"] or "",
                drift_score=r["drift_score"],
                drift_tier=r["drift_tier"],
                intervention_triggered=bool(r["intervention_triggered"]),
                intervention_details=r["intervention_details"] or "",
                execution_result=r["execution_result"] or "",
                timestamp=str(r["timestamp"])
            ) for r in rows
        ]

@router.post("/{session_id}/step", response_model=StepResponse)
def submit_step(session_id: str, payload: StepSubmit):
    with db_session() as conn:
        cursor = conn.cursor()
        
        # 1. Fetch Session and associated Goal
        cursor.execute("SELECT * FROM sessions WHERE id = ?", (session_id,))
        sess = cursor.fetchone()
        if not sess:
            raise HTTPException(status_code=404, detail="Session not found")

        cursor.execute("SELECT * FROM goals WHERE id = ?", (sess["goal_id"],))
        goal = cursor.fetchone()
        if not goal:
            raise HTTPException(status_code=404, detail="Associated Goal not found")

        # 2. Fetch Active Milestone
        cursor.execute("SELECT * FROM milestones WHERE goal_id = ? AND status = 'in_progress' LIMIT 1", (sess["goal_id"],))
        active_ms = cursor.fetchone()
        if not active_ms:
            cursor.execute("SELECT * FROM milestones WHERE goal_id = ? AND status = 'pending' ORDER BY order_index ASC LIMIT 1", (sess["goal_id"],))
            active_ms = cursor.fetchone()

        ms_title = active_ms["title"] if active_ms else "General Objective"
        ms_desc = active_ms["description"] if active_ms else ""

        # Count current steps in session
        cursor.execute("SELECT COUNT(*) FROM steps WHERE session_id = ?", (session_id,))
        step_count = cursor.fetchone()[0] + 1

        # 3. Drift Analysis
        analysis = drift_detector.calculate_drift(
            proposed_action=payload.proposed_action,
            reasoning=payload.reasoning,
            root_intent=goal["intent"],
            active_milestone_title=ms_title,
            active_milestone_desc=ms_desc,
            anti_goals=json.loads(goal["anti_goals"]),
            invariant_constraints=json.loads(goal["invariant_constraints"]),
            acceptance_criteria=json.loads(goal["acceptance_criteria"]),
            session_step_count=step_count
        )

        step_id = str(uuid.uuid4())
        exec_result = "Action approved and executed." if not analysis["intervention_triggered"] else "Intervention applied: Execution blocked."

        # 4. Insert Step
        cursor.execute("""
        INSERT INTO steps (id, session_id, step_number, proposed_action, action_type, reasoning, context_snapshot, drift_score, drift_tier, intervention_triggered, intervention_details, execution_result)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            step_id,
            session_id,
            step_count,
            payload.proposed_action,
            payload.action_type,
            payload.reasoning,
            payload.context_snapshot or "",
            analysis["aggregate_drift"],
            analysis["drift_tier"],
            1 if analysis["intervention_triggered"] else 0,
            analysis["intervention_details"],
            exec_result
        ))

        # 5. Insert Detailed Drift Audit Record
        audit_id = str(uuid.uuid4())
        cursor.execute("""
        INSERT INTO drift_audits (id, session_id, step_id, semantic_score, constraint_score, horizon_score, aggregate_drift, status, feedback_prompt)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            audit_id,
            session_id,
            step_id,
            analysis["semantic_score"],
            analysis["constraint_score"],
            analysis["horizon_score"],
            analysis["aggregate_drift"],
            analysis["drift_tier"],
            analysis["intervention_details"]
        ))

        # Update session last_active_at
        cursor.execute("UPDATE sessions SET last_active_at = CURRENT_TIMESTAMP WHERE id = ?", (session_id,))

        return StepResponse(
            id=step_id,
            session_id=session_id,
            step_number=step_count,
            proposed_action=payload.proposed_action,
            action_type=payload.action_type,
            reasoning=payload.reasoning,
            context_snapshot=payload.context_snapshot or "",
            drift_score=analysis["aggregate_drift"],
            drift_tier=analysis["drift_tier"],
            intervention_triggered=analysis["intervention_triggered"],
            intervention_details=analysis["intervention_details"],
            execution_result=exec_result,
            timestamp="now"
        )
