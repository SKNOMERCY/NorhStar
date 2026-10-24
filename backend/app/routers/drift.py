from fastapi import APIRouter
from typing import List, Dict, Any, Optional
from backend.app.database import db_session
from backend.app.models.session import DriftAuditResponse

router = APIRouter(prefix="/api/drift", tags=["drift"])

@router.get("/stats")
def get_drift_stats(goal_id: Optional[str] = None) -> Dict[str, Any]:
    with db_session() as conn:
        cursor = conn.cursor()
        
        if goal_id:
            cursor.execute("SELECT COUNT(*) FROM goals WHERE id = ? AND status = 'active'", (goal_id,))
            active_goals = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM sessions WHERE goal_id = ?", (goal_id,))
            total_sessions = cursor.fetchone()[0]

            cursor.execute("""
            SELECT COUNT(st.id), AVG(st.drift_score), SUM(st.intervention_triggered)
            FROM steps st
            JOIN sessions s ON st.session_id = s.id
            WHERE s.goal_id = ?
            """, (goal_id,))
            row = cursor.fetchone()
            total_steps = row[0] or 0
            avg_drift = row[1]
            total_interventions = row[2] or 0

            cursor.execute("SELECT COUNT(*) FROM evolution_proposals WHERE goal_id = ? AND status = 'approved'", (goal_id,))
            approved_evolutions = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM evolution_proposals WHERE goal_id = ? AND status = 'pending'", (goal_id,))
            pending_evolutions = cursor.fetchone()[0]

            if total_steps == 0:
                mean_drift = 0.0
                alignment_health = 100.0
            else:
                mean_drift = avg_drift if avg_drift is not None else 0.0
                alignment_health = round(max(0.0, min(100.0, (1.0 - mean_drift) * 100.0)), 1)
        else:
            cursor.execute("SELECT COUNT(*) FROM goals WHERE status = 'active'")
            active_goals = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM sessions")
            total_sessions = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*), AVG(drift_score), SUM(intervention_triggered) FROM steps")
            total_steps, avg_drift, total_interventions = cursor.fetchone()
            total_steps = total_steps or 0
            total_interventions = total_interventions or 0

            cursor.execute("SELECT COUNT(*) FROM evolution_proposals WHERE status = 'approved'")
            approved_evolutions = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM evolution_proposals WHERE status = 'pending'")
            pending_evolutions = cursor.fetchone()[0]

            mean_drift = avg_drift if avg_drift is not None else 0.12
            alignment_health = round(max(0.0, min(100.0, (1.0 - mean_drift) * 100.0)), 1)

        return {
            "active_goals": active_goals,
            "total_sessions": total_sessions,
            "total_steps": total_steps,
            "average_drift_score": round(mean_drift, 3),
            "alignment_health_percentage": alignment_health,
            "total_interventions": total_interventions,
            "approved_evolutions": approved_evolutions,
            "pending_evolutions": pending_evolutions
        }

@router.get("/audits", response_model=List[DriftAuditResponse])
def get_drift_audits(goal_id: Optional[str] = None, limit: int = 50):
    with db_session() as conn:
        cursor = conn.cursor()
        if goal_id:
            cursor.execute("""
            SELECT da.* FROM drift_audits da
            JOIN sessions s ON da.session_id = s.id
            WHERE s.goal_id = ?
            ORDER BY da.timestamp DESC LIMIT ?
            """, (goal_id, limit))
        else:
            cursor.execute("""
            SELECT * FROM drift_audits ORDER BY timestamp DESC LIMIT ?
            """, (limit,))
        rows = cursor.fetchall()
        return [
            DriftAuditResponse(
                id=r["id"],
                session_id=r["session_id"],
                step_id=r["step_id"],
                semantic_score=r["semantic_score"],
                constraint_score=r["constraint_score"],
                horizon_score=r["horizon_score"],
                aggregate_drift=r["aggregate_drift"],
                status=r["status"],
                feedback_prompt=r["feedback_prompt"] or "",
                timestamp=str(r["timestamp"])
            ) for r in rows
        ]
