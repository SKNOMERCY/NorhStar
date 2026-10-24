import re
import math
from typing import Dict, Any, List, Tuple, Optional
from backend.app.config import settings

def _tokenize(text: str) -> List[str]:
    # Lowercase and split on non-alphanumeric chars
    words = re.findall(r'[a-zA-Z0-9_\-\.]+', text.lower())
    # Exclude common stop words
    stop_words = {
        'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'with', 
        'about', 'against', 'between', 'into', 'through', 'during', 'before', 'after', 
        'above', 'below', 'is', 'am', 'are', 'was', 'were', 'be', 'been', 'being', 
        'have', 'has', 'had', 'do', 'does', 'did', 'can', 'could', 'will', 'would', 
        'should', 'must', 'it', 'its', 'this', 'that', 'these', 'those'
    }
    return [w for w in words if w not in stop_words and len(w) > 1]

def _vectorize(tokens: List[str]) -> Dict[str, float]:
    counts: Dict[str, float] = {}
    for t in tokens:
        counts[t] = counts.get(t, 0.0) + 1.0
    # Euclidean normalize
    norm = math.sqrt(sum(v * v for v in counts.values()))
    if norm == 0:
        return {}
    return {k: v / norm for k, v in counts.items()}

def _cosine_similarity(v1: Dict[str, float], v2: Dict[str, float]) -> float:
    if not v1 or not v2:
        return 0.0
    common = set(v1.keys()).intersection(set(v2.keys()))
    dot = sum(v1[k] * v2[k] for k in common)
    return max(0.0, min(1.0, dot))

class DriftDetector:
    @staticmethod
    def calculate_drift(
        proposed_action: str,
        reasoning: str,
        root_intent: str,
        active_milestone_title: str,
        active_milestone_desc: str,
        anti_goals: List[str],
        invariant_constraints: List[str],
        acceptance_criteria: Optional[List[str]] = None,
        session_step_count: int = 1
    ) -> Dict[str, Any]:
        """
        Calculates multi-factor drift score:
        1. Semantic distance from root goal intent and active milestone.
        2. Invariant constraints and anti-goal breach penalties.
        3. Horizon decay penalty (steps without milestone progress).
        Returns structured results: alignment_score, drift_score, verdict, explanation, etc.
        """
        combined_agent_text = f"{proposed_action} {reasoning}".lower()
        agent_tokens = _tokenize(combined_agent_text)
        agent_vec = _vectorize(agent_tokens)

        # 1. Semantic alignment with Root Intent & Active Milestone
        criteria_text = " ".join(acceptance_criteria or [])
        target_context = f"{root_intent} {active_milestone_title} {active_milestone_desc} {criteria_text}"
        target_tokens = _tokenize(target_context)
        target_vec = _vectorize(target_tokens)
        
        raw_similarity = _cosine_similarity(agent_vec, target_vec)
        # Invert similarity to get semantic distance (0 = identical, 1 = completely orthogonal)
        semantic_distance = 1.0 - raw_similarity
        
        # Soften semantic distance: agent actions (e.g. terminal commands, specific code diffs)
        # naturally have specialized vocabulary, so map raw similarity gracefully.
        if raw_similarity > 0.15:
            semantic_score = max(0.05, 0.45 * (1.0 - raw_similarity))
        else:
            semantic_score = min(1.0, 0.50 + 0.8 * (0.15 - raw_similarity))

        # 2. Anti-Goal & Invariant Constraint Breach Check
        constraint_score = 0.0
        breached_rules: List[str] = []

        # Check anti-goals
        for anti in anti_goals:
            anti_lower = anti.lower()
            anti_tokens = _tokenize(anti)
            overlap = set(agent_tokens).intersection(set(anti_tokens))
            
            # Direct keyword or phrase triggers
            forbidden_triggers = [
                "game", "arcade", "retro", "shooter", "crypto", "miner", "wallpaper", 
                "music player", "bypass auth", "disable security", "mock test always pass",
                "delete test", "drop table", "ignore constraint", "plaintext", "unencrypted",
                "fabricate", "hallucinate citation", "unverified citation", "drop database"
            ]
            triggered_phrase = any(term in combined_agent_text for term in forbidden_triggers if term in anti_lower)
            if len(overlap) >= 2 or triggered_phrase:
                constraint_score = max(constraint_score, 0.88)
                breached_rules.append(f"Anti-Goal Violation: {anti}")

        # Check invariant constraints (negative / security rules)
        for inv in invariant_constraints:
            inv_lower = inv.lower()
            if "privacy" in inv_lower or "ferpa" in inv_lower or "hipaa" in inv_lower or "phi" in inv_lower or "pii" in inv_lower:
                if any(x in combined_agent_text for x in ["public s3", "unencrypted", "dump pii", "log plaintext", "disable ssl"]):
                    constraint_score = max(constraint_score, 0.90)
                    breached_rules.append(f"Invariant Constraint Breach: {inv}")
            if "double-entry" in inv_lower or "ledger" in inv_lower:
                if any(x in combined_agent_text for x in ["float ", "float(", "round trip float", "single sided entry"]):
                    constraint_score = max(constraint_score, 0.85)
                    breached_rules.append(f"Invariant Constraint Breach: {inv}")
            if "cite verified" in inv_lower or "primary academic" in inv_lower:
                if any(x in combined_agent_text for x in ["fake citation", "invented doi", "synthetic paper", "placeholder source"]):
                    constraint_score = max(constraint_score, 0.85)
                    breached_rules.append(f"Invariant Constraint Breach: {inv}")

        # Check negative constraint keywords / suspicious tangents
        suspicious_tangents = [
            "play sound", "custom renderer", "physics engine", "easter egg", 
            "unrelated refactor", "random animation", "overhaul theme", "bitcoin"
        ]
        for tangent in suspicious_tangents:
            if tangent in combined_agent_text:
                constraint_score = max(constraint_score, 0.70)
                breached_rules.append(f"Detected Unsanctioned Tangent: '{tangent}'")

        # 3. Horizon Decay Penalty
        # If an agent spends > 6 consecutive steps without advancing a milestone, penalize loop spinning
        horizon_penalty = 0.0
        if session_step_count > 6:
            horizon_penalty = min(0.35, (session_step_count - 6) * 0.05)

        # Composite Aggregate Drift Score
        aggregate_drift = (
            settings.WEIGHT_SEMANTIC * semantic_score +
            settings.WEIGHT_CONSTRAINT * constraint_score +
            settings.WEIGHT_HORIZON_DECAY * horizon_penalty
        )
        aggregate_drift = round(max(0.0, min(1.0, aggregate_drift)), 3)
        alignment_score = round(max(0.0, min(1.0, 1.0 - aggregate_drift)), 3)

        # Assign Severity Tier & Verdict
        # Verdict: ALLOWED, WARNED, BLOCKED, REQUIRES_APPROVAL
        if aggregate_drift < settings.DRIFT_NORMAL_MAX:
            tier = "NORMAL"
            verdict = "ALLOWED"
            intervention = False
            details = "Aligned with North Star objective and active milestone."
            recommendation = "Proceed with autonomous step execution."
        elif aggregate_drift < settings.DRIFT_WARNING_MAX:
            tier = "WARNING"
            verdict = "WARNED"
            intervention = False
            details = "Mild drift detected: Proposed action is straying from primary milestone focus. Grounding reminder advised."
            recommendation = f"Ensure alignment with active milestone '{active_milestone_title}' before expanding scope."
        elif aggregate_drift < settings.DRIFT_INTERVENE_MAX:
            tier = "INTERVENE"
            verdict = "BLOCKED"
            intervention = True
            details = (
                f"NORTHSTAR CIRCUIT BREAKER: Substantial drift detected (Score: {aggregate_drift}). "
                f"Violations: {', '.join(breached_rules) if breached_rules else 'Tangential divergence from milestone'}. "
                f"Action execution halted. Steering agent back to active milestone."
            )
            recommendation = "Revert to verified persistent state and re-anchor on active milestone requirements."
        else:
            tier = "CRITICAL"
            verdict = "REQUIRES_APPROVAL"
            intervention = True
            details = (
                f"NORTHSTAR CRITICAL DIVERGENCE: Extreme contradiction or anti-goal breach (Score: {aggregate_drift}). "
                f"Violations: {', '.join(breached_rules) if breached_rules else 'Incompatible action'}. "
                f"Action aborted immediately. Human operator approval or Evolution RFC required."
            )
            recommendation = "Halt execution. Submit an Evolution RFC or obtain manual operator approval."

        return {
            "semantic_score": round(semantic_score, 3),
            "constraint_score": round(constraint_score, 3),
            "horizon_score": round(horizon_penalty, 3),
            "aggregate_drift": aggregate_drift,
            "drift_score": aggregate_drift,
            "alignment_score": alignment_score,
            "drift_tier": tier,
            "verdict": verdict,
            "explanation": details,
            "violated_constraints": breached_rules,
            "recommended_corrective_action": recommendation,
            "intervention_triggered": intervention,
            "intervention_details": details,
            "breached_rules": breached_rules,
            "analysis_mode": "DETERMINISTIC_MULTI_FACTOR_EVALUATOR"
        }


drift_detector = DriftDetector()
