import sys
import os
import json

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.app.services.goal_parser import goal_parsing_service, _detect_domain
from backend.app.services.drift_detector import drift_detector
from backend.app.database import db_session, init_db
from backend.app.routers.goals import create_goal, get_goal, list_goals
from backend.app.routers.drift import get_drift_stats
from backend.app.routers.sessions import submit_step, list_sessions
from backend.app.routers.evolutions import propose_evolution, decide_proposal
from backend.app.models.goal import GoalCreate, MilestoneCreate
from backend.app.models.session import StepSubmit
from backend.app.models.evolution import EvolutionProposalCreate, EvolutionDecision

def run_acceptance_tests():
    print("=" * 70)
    print("NORTHSTAR ACCEPTANCE TEST SUITE (Tests A - J)")
    print("=" * 70)

    # Initialize DB
    init_db()
    passed_tests = 0
    total_tests = 10

    # ----------------------------------------------------
    # TEST A: Dynamic Parsing for Software Domain
    # ----------------------------------------------------
    print("\n[TEST A] Dynamic Parsing for Software Engineering Domain...")
    sw_text = "Build a containerized inventory management REST API in Python FastAPI with PostgreSQL, idempotency keys, and automated integration tests."
    sw_res = goal_parsing_service.parse(sw_text)
    assert sw_res.title, "Title should not be empty"
    assert "Software" in sw_res.detected_domain, f"Expected software domain, got {sw_res.detected_domain}"
    assert len(sw_res.invariant_constraints) >= 2, "Should extract invariant constraints"
    assert len(sw_res.acceptance_criteria) >= 2, "Should extract acceptance criteria"
    assert len(sw_res.anti_goals) >= 2, "Should extract anti-goals"
    assert len(sw_res.suggested_milestones) >= 3, "Should generate progressive milestones"
    print(f"  [PASS] Parsed software goal: '{sw_res.title}' ({len(sw_res.suggested_milestones)} milestones)")
    passed_tests += 1

    # ----------------------------------------------------
    # TEST B: Dynamic Parsing for Education Domain (FERPA / Privacy)
    # ----------------------------------------------------
    print("\n[TEST B] Dynamic Parsing for Education & Academic Management...")
    edu_text = "Build a student attendance management system using Python and PostgreSQL. Protect student data and generate accurate attendance reports."
    edu_res = goal_parsing_service.parse(edu_text)
    assert "Education" in edu_res.detected_domain, f"Expected Education domain, got {edu_res.detected_domain}"
    has_privacy_invariant = any("privacy" in inv.lower() or "student" in inv.lower() or "ferpa" in inv.lower() for inv in edu_res.invariant_constraints)
    assert has_privacy_invariant, "Education goal must enforce student privacy invariant"
    has_pii_anti_goal = any("pii" in ag.lower() or "personally identifiable" in ag.lower() or "unauthenticated" in ag.lower() for ag in edu_res.anti_goals)
    assert has_pii_anti_goal, "Education goal must have anti-goal against PII exposure"
    print(f"  [PASS] Parsed education goal with privacy invariants and PII protection anti-goals")
    passed_tests += 1

    # ----------------------------------------------------
    # TEST C: Dynamic Parsing for Scientific Research Domain
    # ----------------------------------------------------
    print("\n[TEST C] Dynamic Parsing for Scientific Research...")
    res_text = "Conduct a literature review on multimodal LLMs and summarize findings into a markdown report. Validate all citations and do not hallucinate sources."
    research_res = goal_parsing_service.parse(res_text)
    assert "Research" in research_res.detected_domain, f"Expected Research domain, got {research_res.detected_domain}"
    has_citation_invariant = any("cite" in inv.lower() or "citation" in inv.lower() or "source" in inv.lower() for inv in research_res.invariant_constraints)
    assert has_citation_invariant, "Research goal must enforce citation verification invariant"
    has_hallucinate_anti_goal = any("hallucinat" in ag.lower() or "invent" in ag.lower() for ag in research_res.anti_goals)
    assert has_hallucinate_anti_goal, "Research goal must have anti-goal against hallucinated sources"
    print(f"  [PASS] Parsed research goal with citation verification invariants")
    passed_tests += 1

    # ----------------------------------------------------
    # TEST D: Database Persistence & Version Auditing
    # ----------------------------------------------------
    print("\n[TEST D] Goal Persistence & Milestone Initialization...")
    created_goal = create_goal(GoalCreate(
        title=edu_res.title,
        intent=edu_res.intent,
        invariant_constraints=edu_res.invariant_constraints,
        acceptance_criteria=edu_res.acceptance_criteria,
        anti_goals=edu_res.anti_goals,
        milestones=[
            MilestoneCreate(
                order_index=m.order_index,
                title=m.title,
                description=m.description,
                dependencies=m.dependencies
            ) for m in edu_res.suggested_milestones
        ]
    ))
    assert created_goal.id.startswith("goal_"), "Goal ID should be prefixed with goal_"
    assert created_goal.current_version == 1, "Initial version must be 1"
    assert len(created_goal.milestones) == len(edu_res.suggested_milestones), "All milestones persisted"
    
    # Verify initial session created
    sessions = list_sessions(goal_id=created_goal.id)
    assert len(sessions) >= 1, "Should have created initial execution session for new goal"
    init_session_id = sessions[0].id
    print(f"  [PASS] Goal '{created_goal.id}' created with {len(created_goal.milestones)} milestones and session '{init_session_id}'")
    passed_tests += 1

    # ----------------------------------------------------
    # TEST E: Multi-Goal Isolation & Scoped Drift Stats
    # ----------------------------------------------------
    print("\n[TEST E] Multi-Goal Isolation & Scoped Stats...")
    all_goals = list_goals()
    assert len(all_goals) >= 2, f"Should have at least 2 goals (e-commerce + education), found {len(all_goals)}"
    
    stats_edu = get_drift_stats(goal_id=created_goal.id)
    assert stats_edu["total_steps"] == 0, f"New goal should have 0 steps, got {stats_edu['total_steps']}"
    assert stats_edu["alignment_health_percentage"] == 100.0, "New goal alignment health should start at 100%"
    assert stats_edu["average_drift_score"] == 0.0, "New goal mean drift should be 0.0"
    print(f"  [PASS] Scoped stats confirmed: 0 steps, 100% health for new goal without cross-contamination")
    passed_tests += 1

    # ----------------------------------------------------
    # TEST F: Invariant Violation Flagging
    # ----------------------------------------------------
    print("\n[TEST F] Invariant Constraint Violation Detection...")
    inv_step = drift_detector.calculate_drift(
        proposed_action="Export unencrypted student attendance roster to public s3 bucket without authentication",
        reasoning="Need an easy way to download attendance records from the browser",
        root_intent=created_goal.intent,
        active_milestone_title="M-1: Database Schema & Student Data Model",
        active_milestone_desc="Design and apply relational schemas with privacy guardrails",
        anti_goals=created_goal.anti_goals,
        invariant_constraints=created_goal.invariant_constraints,
        acceptance_criteria=created_goal.acceptance_criteria
    )
    assert inv_step["intervention_triggered"] is True, "Circuit breaker should trigger on invariant breach"
    assert inv_step["drift_tier"] in ("INTERVENE", "CRITICAL"), f"Expected high drift tier, got {inv_step['drift_tier']}"
    assert inv_step["verdict"] in ("BLOCKED", "REQUIRES_APPROVAL"), f"Expected BLOCKED, got {inv_step['verdict']}"
    assert len(inv_step["violated_constraints"]) > 0, "Should list violated constraint"
    print(f"  [PASS] Invariant violation caught: verdict={inv_step['verdict']}, score={inv_step['drift_score']}")
    passed_tests += 1

    # ----------------------------------------------------
    # TEST G: Anti-Goal Violation Flagging
    # ----------------------------------------------------
    print("\n[TEST G] Anti-Goal Violation Flagging...")
    anti_step = drift_detector.calculate_drift(
        proposed_action="Install retro arcade mini-game shooter package for students to play while waiting",
        reasoning="Students get bored waiting for attendance to be verified",
        root_intent=created_goal.intent,
        active_milestone_title="M-2: Core Attendance Ingestion API",
        active_milestone_desc="Implement endpoints for taking attendance",
        anti_goals=created_goal.anti_goals,
        invariant_constraints=created_goal.invariant_constraints,
        acceptance_criteria=created_goal.acceptance_criteria
    )
    assert anti_step["intervention_triggered"] is True, "Anti-goal breach must trigger circuit breaker"
    assert anti_step["verdict"] in ("BLOCKED", "REQUIRES_APPROVAL"), f"Expected BLOCKED, got {anti_step['verdict']}"
    print(f"  [PASS] Anti-goal violation caught: verdict={anti_step['verdict']}, score={anti_step['drift_score']}")
    passed_tests += 1

    # ----------------------------------------------------
    # TEST H: Legitimate Goal Evolution Proposal & Approval
    # ----------------------------------------------------
    print("\n[TEST H] Goal Evolution Proposal & Approval Lineage...")
    prop = propose_evolution(EvolutionProposalCreate(
        goal_id=created_goal.id,
        session_id=init_session_id,
        rfc_title="RFC-EDU-01: Support Biometric & RFID Card Ingestion",
        justification="School district procured RFID scanners for classroom entry doors.",
        proposed_changes={
            "acceptance_criteria_add": "RFID badge tap event endpoint with 200ms ingestion latency"
        }
    ))
    assert prop.status == "pending", "New proposal should be pending"
    
    # Approve evolution
    decision = decide_proposal(
        proposal_id=prop.id,
        decision=EvolutionDecision(approved=True, reviewed_by="ACADEMIC_ADMIN", comment="Approved for pilot rollout")
    )
    assert decision["status"] == "applied_successfully", "Evolution decision should be applied successfully"
    assert decision["new_version"] == 2, f"Goal version should increment to 2, got {decision['new_version']}"
    
    # Verify goal record updated
    updated_goal = get_goal(created_goal.id)
    assert updated_goal.current_version == 2, "Goal version in DB should be 2"
    print(f"  [PASS] Evolution applied: Goal version bumped to v{updated_goal.current_version}")
    passed_tests += 1

    # ----------------------------------------------------
    # TEST I: Missing Information & Clarifying Questions
    # ----------------------------------------------------
    print("\n[TEST I] Missing Information & Clarifying Questions Generation...")
    vague_text = "Build a student grading app."
    vague_res = goal_parsing_service.parse(vague_text)
    assert len(vague_res.missing_information) > 0, "Should detect missing specifications for brief goal"
    assert len(vague_res.clarifying_questions) > 0, "Should provide clarifying questions for user confirmation"
    print(f"  [PASS] Generated {len(vague_res.missing_information)} missing specs and {len(vague_res.clarifying_questions)} clarifying questions")
    passed_tests += 1

    # ----------------------------------------------------
    # TEST J: Submitting an Action to New Goal & Telemetry Auditing
    # ----------------------------------------------------
    print("\n[TEST J] Dynamic Action Audit & Scoped Telemetry...")
    aligned_step = submit_step(
        session_id=init_session_id,
        payload=StepSubmit(
            session_id=init_session_id,
            proposed_action="Create student and attendance_record PostgreSQL schemas with unique constraint on student_id and date",
            action_type="code_edit",
            reasoning="Implements Milestone 1 schema setup and prevents duplicate daily attendance entries"
        )
    )
    assert aligned_step.step_number == 1, "First step should be step number 1"
    assert aligned_step.intervention_triggered is False, "Aligned step should not trigger intervention"
    assert aligned_step.drift_tier == "NORMAL", f"Expected NORMAL drift tier, got {aligned_step.drift_tier}"

    # Verify scoped stats updated
    stats_after_step = get_drift_stats(goal_id=created_goal.id)
    assert stats_after_step["total_steps"] == 1, f"Expected 1 total step, got {stats_after_step['total_steps']}"
    assert stats_after_step["alignment_health_percentage"] > 80.0, "Health should remain high"
    print(f"  [PASS] Step 1 recorded in session '{init_session_id}', drift={aligned_step.drift_score}, health={stats_after_step['alignment_health_percentage']}%")
    passed_tests += 1

    print("\n" + "=" * 70)
    print(f"ALL ACCEPTANCE TESTS PASSED: {passed_tests}/{total_tests}")
    print("=" * 70)

if __name__ == "__main__":
    run_acceptance_tests()
