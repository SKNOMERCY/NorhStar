import json
import uuid
from typing import Dict, Any, Tuple
from backend.app.database import db_session

class EvolutionService:
    @staticmethod
    def classify_proposal(
        rfc_title: str,
        justification: str,
        proposed_changes: Dict[str, Any],
        root_intent: str
    ) -> Tuple[str, float]:
        """
        Classifies whether a proposed modification represents legitimate
        Goal Evolution or Unsanctioned Drift.
        
        Criteria for Legitimate Evolution:
        - Mentions external constraints, API deprecation, security advisories, or updated specifications.
        - Preserves core purpose while adapting boundaries.
        - Has specific justification.
        
        Criteria for Drift:
        - Vanity features (games, cosmetic rewrites, unrelated utilities).
        - Weak justification ("thought it would be cool", "wanted to try a new library").
        - Directly conflicts with fundamental invariants without valid external trigger.
        """
        combined = f"{rfc_title} {justification}".lower()

        # Keywords indicating legitimate environmental triggers
        evolution_indicators = [
            "deprecated", "compliance", "security vulnerability", "api change", 
            "upstream", "performance bottleneck", "specification update", 
            "user requested", "schema revision", "requirement", "migration necessity"
        ]
        
        # Keywords indicating agent distraction / drift
        drift_indicators = [
            "cool", "fun", "game", "side project", "unrelated", "arcade", 
            "experimental rewrite", "bored", "novel idea", "custom engine"
        ]

        evolution_matches = sum(1 for w in evolution_indicators if w in combined)
        drift_matches = sum(1 for w in drift_indicators if w in combined)

        if drift_matches > 0:
            return "DRIFT", round(min(0.95, 0.65 + 0.15 * drift_matches), 2)

        if evolution_matches >= 1:
            return "EVOLUTION", round(min(0.98, 0.70 + 0.10 * evolution_matches), 2)

        # Default classification based on length and structure of justification
        if len(justification.strip()) > 80:
            return "EVOLUTION", 0.60
        else:
            return "DRIFT", 0.55

    @staticmethod
    def apply_evolution(proposal_id: str, approved_by: str = "HUMAN_SUPERVISOR") -> Dict[str, Any]:
        """
        Applies an approved evolution proposal to the persistent Goal representation layer.
        Increments the version number and records version diff history.
        """
        with db_session() as conn:
            cursor = conn.cursor()
            
            # Fetch proposal
            cursor.execute("SELECT * FROM evolution_proposals WHERE id = ?", (proposal_id,))
            prop = cursor.fetchone()
            if not prop:
                raise ValueError("Evolution proposal not found")

            goal_id = prop["goal_id"]
            changes = json.loads(prop["proposed_changes"])
            
            # Fetch current goal
            cursor.execute("SELECT * FROM goals WHERE id = ?", (goal_id,))
            goal = cursor.fetchone()
            if not goal:
                raise ValueError("Target goal not found")

            new_version = goal["current_version"] + 1

            # Update goal attributes if provided in changes
            new_title = changes.get("title", goal["title"])
            new_intent = changes.get("intent", goal["intent"])
            new_constraints = json.dumps(changes.get("invariant_constraints", json.loads(goal["invariant_constraints"])))
            new_criteria = json.dumps(changes.get("acceptance_criteria", json.loads(goal["acceptance_criteria"])))
            new_anti = json.dumps(changes.get("anti_goals", json.loads(goal["anti_goals"])))

            cursor.execute("""
            UPDATE goals 
            SET title = ?, intent = ?, invariant_constraints = ?, acceptance_criteria = ?, anti_goals = ?, current_version = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """, (new_title, new_intent, new_constraints, new_criteria, new_anti, new_version, goal_id))

            # Record version history
            version_id = str(uuid.uuid4())
            diff_summary = f"RFC '{prop['rfc_title']}' applied: {prop['justification']}"
            cursor.execute("""
            INSERT INTO goal_versions (id, goal_id, version_num, reason, diff_summary, approved_by)
            VALUES (?, ?, ?, ?, ?, ?)
            """, (version_id, goal_id, new_version, prop["rfc_title"], diff_summary, approved_by))

            # Mark proposal as approved
            cursor.execute("""
            UPDATE evolution_proposals SET status = 'approved' WHERE id = ?
            """, (proposal_id,))

            return {
                "goal_id": goal_id,
                "new_version": new_version,
                "rfc_title": prop["rfc_title"],
                "status": "applied_successfully"
            }

evolution_service = EvolutionService()
