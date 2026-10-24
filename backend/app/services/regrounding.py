from typing import List, Dict, Any

class RegroundingEngine:
    @staticmethod
    def generate_grounding_prompt(
        goal_title: str,
        goal_intent: str,
        invariant_constraints: List[str],
        active_milestone: Dict[str, Any],
        anti_goals: List[str],
        drift_feedback: str = ""
    ) -> str:
        """
        Synthesizes the Northstar Invariant Grounding context prompt.
        This prompt survives context truncation and resets context decay.
        """
        constraints_str = "\n".join([f"  - [INVARIANT] {c}" for c in invariant_constraints])
        anti_goals_str = "\n".join([f"  - [FORBIDDEN] {ag}" for ag in anti_goals])
        
        milestone_info = (
            f"ID: {active_milestone.get('id', 'N/A')}\n"
            f"Title: {active_milestone.get('title', 'None')}\n"
            f"Description: {active_milestone.get('description', 'None')}\n"
            f"Current Progress: {int(active_milestone.get('progress', 0.0) * 100)}%"
        )

        warning_block = ""
        if drift_feedback:
            warning_block = (
                f"\n>>> [NORTHSTAR CORRECTIVE INTERVENTION REQUIRED] <<<\n"
                f"{drift_feedback}\n"
                f">>> RE-GROUND IMMEDIATELY: Halt the tangential sub-task and re-align with the active milestone below.\n"
            )

        prompt = f"""
================================================================================
                    NORTHSTAR PERSISTENT GOAL LAYER
================================================================================
OVERARCHING NORTH STAR OBJECTIVE:
  Title:  {goal_title}
  Intent: {goal_intent}

MANDATORY INVARIANT CONSTRAINTS (Never Violate):
{constraints_str}

STRICT ANTI-GOALS (Do Not Implement / Diverge Into):
{anti_goals_str}

CURRENT ACTIVE MILESTONE FOCUS:
{milestone_info}
{warning_block}
OPERATIONAL DIRECTIVE:
Your next action MUST directly advance the active milestone without violating any 
invariant constraints or pursuing any anti-goals.
================================================================================
""".strip()
        return prompt

regrounding_engine = RegroundingEngine()
