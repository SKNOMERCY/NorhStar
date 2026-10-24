import json
import uuid
from typing import List
from fastapi import APIRouter, HTTPException
from backend.app.database import db_session
from backend.app.models.evolution import (
    EvolutionProposalCreate, EvolutionDecision, EvolutionProposalResponse
)
from backend.app.services.evolution_service import evolution_service

router = APIRouter(prefix="/api/evolutions", tags=["evolutions"])

@router.get("", response_model=List[EvolutionProposalResponse])
def list_proposals(goal_id: str = None):
    with db_session() as conn:
        cursor = conn.cursor()
        query = "SELECT * FROM evolution_proposals"
        params = ()
        if goal_id:
            query += " WHERE goal_id = ?"
            params = (goal_id,)
        query += " ORDER BY created_at DESC"
        
        cursor.execute(query, params)
        rows = cursor.fetchall()

        return [
            EvolutionProposalResponse(
                id=r["id"],
                goal_id=r["goal_id"],
                session_id=r["session_id"],
                rfc_title=r["rfc_title"],
                justification=r["justification"],
                proposed_changes=json.loads(r["proposed_changes"]),
                classification=r["classification"],
                confidence=r["confidence"],
                status=r["status"],
                created_at=str(r["created_at"])
            ) for r in rows
        ]

@router.post("", response_model=EvolutionProposalResponse)
def propose_evolution(payload: EvolutionProposalCreate):
    with db_session() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM goals WHERE id = ?", (payload.goal_id,))
        goal = cursor.fetchone()
        if not goal:
            raise HTTPException(status_code=404, detail="Goal not found")

        # Classify Evolution vs Drift
        classification, confidence = evolution_service.classify_proposal(
            rfc_title=payload.rfc_title,
            justification=payload.justification,
            proposed_changes=payload.proposed_changes,
            root_intent=goal["intent"]
        )

        proposal_id = f"rfc_{uuid.uuid4().hex[:8]}"
        cursor.execute("""
        INSERT INTO evolution_proposals (id, goal_id, session_id, rfc_title, justification, proposed_changes, classification, confidence, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pending')
        """, (
            proposal_id,
            payload.goal_id,
            payload.session_id,
            payload.rfc_title,
            payload.justification,
            json.dumps(payload.proposed_changes),
            classification,
            confidence
        ))

        return EvolutionProposalResponse(
            id=proposal_id,
            goal_id=payload.goal_id,
            session_id=payload.session_id,
            rfc_title=payload.rfc_title,
            justification=payload.justification,
            proposed_changes=payload.proposed_changes,
            classification=classification,
            confidence=confidence,
            status="pending",
            created_at="now"
        )

@router.post("/{proposal_id}/decide")
def decide_proposal(proposal_id: str, decision: EvolutionDecision):
    with db_session() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM evolution_proposals WHERE id = ?", (proposal_id,))
        prop = cursor.fetchone()
        if not prop:
            raise HTTPException(status_code=404, detail="Proposal not found")

        if not decision.approved:
            cursor.execute("UPDATE evolution_proposals SET status = 'rejected' WHERE id = ?", (proposal_id,))
            return {"status": "rejected", "proposal_id": proposal_id}

    # If approved, apply evolution to goal
    result = evolution_service.apply_evolution(proposal_id, approved_by=decision.reviewed_by)
    return result
