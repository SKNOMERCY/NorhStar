import json
import uuid
import logging
from typing import Dict, Any, Optional, List
from backend.app.database import db_session
from backend.app.services.ai_provider import ai_provider
from backend.app.services.drift_detector import drift_detector
from backend.app.services.regrounding import regrounding_engine
from backend.app.services.tool_guardrails import tool_guardrails

logger = logging.getLogger("northstar.orchestrator")

class AgentOrchestrator:
    def execute_step(
        self,
        session_id: str,
        manual_action: Optional[str] = None,
        manual_reasoning: Optional[str] = None,
        manual_tool_name: Optional[str] = None,
        manual_tool_args: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Executes a controlled, audited, pre-execution guardrailed step:
        1. Loads goal & active milestone.
        2. Retrieves session context & prior steps.
        3. Gets proposed action from AI Model (or manual input).
        4. Calculates multi-factor drift score.
        5. Validates tool call through Pre-Execution Guardrails.
        6. Intercepts if drift is high or tool is forbidden.
        7. Persists execution telemetry in SQLite.
        """
        with db_session() as conn:
            cursor = conn.cursor()

            # 1. Load Session & Goal
            cursor.execute("SELECT * FROM sessions WHERE id = ?", (session_id,))
            session_row = cursor.fetchone()
            if not session_row:
                raise ValueError(f"Session '{session_id}' not found.")
            session = dict(session_row)

            cursor.execute("SELECT * FROM goals WHERE id = ?", (session["goal_id"],))
            goal_row = cursor.fetchone()
            if not goal_row:
                raise ValueError("Associated Goal not found.")
            goal = dict(goal_row)

            # 2. Load Active Milestone
            cursor.execute(
                "SELECT * FROM milestones WHERE goal_id = ? AND status = 'in_progress' LIMIT 1",
                (goal["id"],)
            )
            active_ms = cursor.fetchone()
            if not active_ms:
                cursor.execute(
                    "SELECT * FROM milestones WHERE goal_id = ? AND status = 'pending' ORDER BY order_index ASC LIMIT 1",
                    (goal["id"],)
                )
                active_ms = cursor.fetchone()

            ms_dict = dict(active_ms) if active_ms else {
                "id": "ms_general", "title": "General Objective", "description": "Execute core requirements", "progress": 0.0
            }

            # 3. Retrieve Prior Steps
            cursor.execute("SELECT * FROM steps WHERE session_id = ? ORDER BY step_number ASC", (session_id,))
            prior_steps = [dict(r) for r in cursor.fetchall()]
            step_count = len(prior_steps) + 1

            # Check if previous step had an intervention (for corrective steering)
            last_intervention = None
            if prior_steps and prior_steps[-1].get("intervention_triggered"):
                last_intervention = prior_steps[-1].get("intervention_details")

        # 4. Synthesize Grounding Context Prompt
        grounding_prompt = regrounding_engine.generate_grounding_prompt(
            goal_title=goal["title"],
            goal_intent=goal["intent"],
            invariant_constraints=json.loads(goal["invariant_constraints"]),
            active_milestone=ms_dict,
            anti_goals=json.loads(goal["anti_goals"]),
            drift_feedback=last_intervention or ""
        )

        # 5. Propose Next Action via AI Model or Manual Input
        if manual_action:
            proposal = {
                "thought": manual_reasoning or "Manual test input",
                "proposed_action": manual_action,
                "tool_name": manual_tool_name or "write_file",
                "tool_args": manual_tool_args or {"path": "test_patch.py", "content": "# patch"},
                "confidence": 0.95,
                "provider": "USER_MANUAL_INPUT",
                "model": "Operator-Input"
            }
        else:
            available_tools = tool_guardrails.get_allowlist_specs()
            proposal = ai_provider.propose_next_action(
                grounding_prompt=grounding_prompt,
                session_history=prior_steps,
                available_tools=available_tools,
                injected_steering=last_intervention
            )

        proposed_action = proposal.get("proposed_action", "Proceed with active milestone")
        reasoning = proposal.get("thought", "Advancing milestone")
        tool_name = proposal.get("tool_name", "write_file")
        tool_args = proposal.get("tool_args", {})

        # 6. Evaluate Multi-Factor Drift
        drift_analysis = drift_detector.calculate_drift(
            proposed_action=proposed_action,
            reasoning=reasoning,
            root_intent=goal["intent"],
            active_milestone_title=ms_dict["title"],
            active_milestone_desc=ms_dict["description"],
            anti_goals=json.loads(goal["anti_goals"]),
            invariant_constraints=json.loads(goal["invariant_constraints"]),
            session_step_count=step_count
        )

        # 7. Pre-Execution Tool Guardrail Inspection
        guardrail_result = tool_guardrails.validate_and_execute(
            tool_name=tool_name,
            tool_args=tool_args,
            anti_goals=json.loads(goal["anti_goals"]),
            invariant_constraints=json.loads(goal["invariant_constraints"])
        )

        # 8. Decision Branching: Circuit Breaker vs Approved Execution
        circuit_breaker = drift_analysis["intervention_triggered"] or not guardrail_result["allowed"]
        
        if circuit_breaker:
            intervention_details = (
                guardrail_result.get("reason")
                if not guardrail_result["allowed"]
                else drift_analysis["intervention_details"]
            )
            exec_result = f"CIRCUIT BREAKER: Tool '{tool_name}' blocked before execution. Re-grounding directive issued."
            tier = "INTERVENE" if drift_analysis["drift_tier"] == "NORMAL" else drift_analysis["drift_tier"]
        else:
            intervention_details = ""
            exec_result = guardrail_result["output"] or "Action authorized and executed successfully."
            tier = drift_analysis["drift_tier"]

        # 9. Persist Step & Telemetry in SQLite
        step_id = str(uuid.uuid4())
        audit_id = str(uuid.uuid4())

        with db_session() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
            INSERT INTO steps (
                id, session_id, step_number, proposed_action, action_type, 
                reasoning, context_snapshot, drift_score, drift_tier, 
                intervention_triggered, intervention_details, execution_result
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                step_id, session_id, step_count, proposed_action, tool_name,
                reasoning, f"Model: {proposal.get('model', 'Northstar')}",
                drift_analysis["aggregate_drift"], tier,
                1 if circuit_breaker else 0, intervention_details, exec_result
            ))

            cursor.execute("""
            INSERT INTO drift_audits (
                id, session_id, step_id, semantic_score, constraint_score, 
                horizon_score, aggregate_drift, status, feedback_prompt
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                audit_id, session_id, step_id,
                drift_analysis["semantic_score"],
                drift_analysis["constraint_score"],
                drift_analysis["horizon_score"],
                drift_analysis["aggregate_drift"],
                tier, intervention_details
            ))

            # Progress milestone if action was approved and aligned
            if not circuit_breaker and ms_dict.get("id") != "ms_general":
                new_progress = min(1.0, round(ms_dict.get("progress", 0.0) + 0.15, 2))
                cursor.execute(
                    "UPDATE milestones SET progress = ? WHERE id = ?",
                    (new_progress, ms_dict["id"])
                )

            cursor.execute("UPDATE sessions SET last_active_at = CURRENT_TIMESTAMP WHERE id = ?", (session_id,))

        return {
            "step_id": step_id,
            "step_number": step_count,
            "model": proposal.get("model", "Northstar"),
            "provider": proposal.get("provider", "Heuristic"),
            "proposed_action": proposed_action,
            "reasoning": reasoning,
            "tool_call": {"name": tool_name, "args": tool_args},
            "guardrail_status": guardrail_result["status"],
            "drift_score": drift_analysis["aggregate_drift"],
            "drift_tier": tier,
            "circuit_breaker_fired": circuit_breaker,
            "intervention_details": intervention_details,
            "execution_result": exec_result
        }

agent_orchestrator = AgentOrchestrator()
