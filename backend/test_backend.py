import sys
import os

# Ensure backend can be imported
sys.path.insert(0, os.path.abspath("."))

from backend.app.database import init_db, db_session
from backend.app.services.drift_detector import drift_detector
from backend.app.services.evolution_service import evolution_service
from backend.app.services.simulation_service import simulation_service
from backend.app.services.regrounding import regrounding_engine

def test_all():
    print("[1/5] Testing Database Initialization...")
    init_db()
    with db_session() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM goals")
        goals_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM milestones")
        ms_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM steps")
        steps_count = cursor.fetchone()[0]
        print(f"       -> Goals: {goals_count}, Milestones: {ms_count}, Steps: {steps_count}")
        assert goals_count >= 1, "Expected at least 1 seeded goal"

    print("[2/5] Testing Drift Detection Engine...")
    aligned_res = drift_detector.calculate_drift(
        proposed_action="Build Dockerfile for catalog service with multi-stage build",
        reasoning="Containerize catalog microservice to complete Milestone 2",
        root_intent="Migrate legacy monolithic e-commerce catalog to containerized microservice",
        active_milestone_title="Containerize Core Catalog Microservice",
        active_milestone_desc="Develop Dockerfile and configure API",
        anti_goals=["Building custom GUI games or unrelated utilities"],
        invariant_constraints=["Must maintain backward compatibility"]
    )
    print(f"       -> Aligned Action Drift Score: {aligned_res['aggregate_drift']} (Tier: {aligned_res['drift_tier']})")
    assert aligned_res["drift_tier"] == "NORMAL", f"Expected NORMAL tier, got {aligned_res['drift_tier']}"

    drift_res = drift_detector.calculate_drift(
        proposed_action="Start coding a retro space shooter arcade game for user waiting screens",
        reasoning="Users get bored during checkout loading so I want to build a mini-game",
        root_intent="Migrate legacy monolithic e-commerce catalog to containerized microservice",
        active_milestone_title="Containerize Core Catalog Microservice",
        active_milestone_desc="Develop Dockerfile and configure API",
        anti_goals=["Building custom GUI games or unrelated utilities"],
        invariant_constraints=["Must maintain backward compatibility"]
    )
    print(f"       -> Tangent Action Drift Score: {drift_res['aggregate_drift']} (Tier: {drift_res['drift_tier']})")
    assert drift_res["intervention_triggered"] is True, "Expected intervention for anti-goal breach"
    print(f"       -> Intervention Triggered: {drift_res['intervention_details'][:80]}...")

    print("[3/5] Testing Grounding Prompt Synthesis...")
    prompt = regrounding_engine.generate_grounding_prompt(
        goal_title="Test Goal",
        goal_intent="Build API",
        invariant_constraints=["Zero plain card numbers"],
        active_milestone={"title": "M1", "progress": 0.5},
        anti_goals=["No games"]
    )
    assert "NORTHSTAR PERSISTENT GOAL LAYER" in prompt, "Grounding header missing"
    print("       -> Grounding Prompt successfully synthesized")

    print("[4/5] Testing Goal Evolution vs Drift Classifier...")
    evo_class, evo_conf = evolution_service.classify_proposal(
        rfc_title="Migrate Stripe webhook to v2026 due to API deprecation",
        justification="Stripe has deprecated v1 endpoints; migration necessity for payment compliance",
        proposed_changes={},
        root_intent="Migrate e-commerce"
    )
    print(f"       -> Evolution RFC: {evo_class} (Confidence: {evo_conf})")
    assert evo_class == "EVOLUTION", f"Expected EVOLUTION, got {evo_class}"

    drift_class, drift_conf = evolution_service.classify_proposal(
        rfc_title="Add interactive 3D voxel game to checkout",
        justification="Thought it would be cool and fun to play games",
        proposed_changes={},
        root_intent="Migrate e-commerce"
    )
    print(f"       -> Distraction RFC: {drift_class} (Confidence: {drift_conf})")
    assert drift_class == "DRIFT", f"Expected DRIFT, got {drift_class}"

    print("[5/5] Testing Multi-Session Simulation Service...")
    scenarios = simulation_service.get_scenarios()
    assert len(scenarios) == 3, f"Expected 3 scenarios, got {len(scenarios)}"
    benchmark_res = simulation_service.run_benchmark("scenario_ecommerce")
    without_score = benchmark_res["summary_metrics"]["without_northstar"]["overall_alignment_score"]
    with_score = benchmark_res["summary_metrics"]["with_northstar"]["overall_alignment_score"]
    print(f"       -> Benchmark: Without Northstar = {without_score}%, With Northstar = {with_score}%")
    assert with_score > without_score, "Guarded agent should score higher than baseline"

    print("\nALL BACKEND UNIT & INTEGRATION TESTS PASSED PERFECTLY!")

if __name__ == "__main__":
    test_all()
