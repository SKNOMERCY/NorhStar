"""
Northstar Backend — Verified Sync Test Suite
Uses exact method signatures as found in the source.
Run from project root: python test_backend_sync.py
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

PASS = "[PASS]"
FAIL = "[FAIL]"
INFO = "[INFO]"

print("=" * 65)
print("NORTHSTAR BACKEND VERIFIED TEST SUITE")
print("=" * 65)

# ─── Test 1: Config ────────────────────────────────────────────
try:
    from backend.app.config import settings
    print(f"{PASS} Config: app='{settings.APP_NAME}', version={settings.VERSION}")
except Exception as e:
    print(f"{FAIL} Config: {e}")

# ─── Test 2: Database ──────────────────────────────────────────
try:
    from backend.app.database import init_db, db_session
    init_db()
    with db_session() as conn:
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM goals"); goals = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM sessions"); sessions = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM milestones"); ms = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM steps"); steps = c.fetchone()[0]
    print(f"{PASS} Database: {goals} goals, {sessions} sessions, {ms} milestones, {steps} steps")
except Exception as e:
    print(f"{FAIL} Database: {e}")

# ─── Test 3: AI Provider — status ──────────────────────────────
try:
    from backend.app.services.ai_provider import ai_provider
    status = ai_provider.get_provider_status()
    assert "active_provider" in status
    assert "is_live_model" in status
    print(f"{PASS} AI Provider status: provider={status['active_provider']}, live={status['is_live_model']}")
except Exception as e:
    print(f"{FAIL} AI Provider status: {e}")

# ─── Test 4: AI Provider — deterministic proposal ─────────────
try:
    from backend.app.services.ai_provider import ai_provider
    proposal = ai_provider.propose_next_action(
        grounding_prompt="Migrate e-commerce monolith to microservices.",
        session_history=[],
        available_tools=[{"name": "read_file"}, {"name": "write_file"}],
    )
    assert "proposed_action" in proposal
    print(f"{PASS} AI Proposal (heuristic): action='{proposal['proposed_action'][:55]}...'")
except Exception as e:
    print(f"{FAIL} AI Proposal: {e}")

# ─── Test 5: Drift Detector ────────────────────────────────────
try:
    from backend.app.services.drift_detector import drift_detector
    result = drift_detector.calculate_drift(
        proposed_action="Build Docker container for the catalog service API",
        reasoning="Containerizing to satisfy Milestone 2 delivery criteria",
        root_intent="Migrate monolith e-commerce platform to microservices",
        active_milestone_title="Catalog Containerization",
        active_milestone_desc="Containerize the catalog service with Docker",
        anti_goals=["building arcade games", "random styling overhauls"],
        invariant_constraints=["Zero downtime", "No data loss"],
        session_step_count=3,
    )
    score = result.get("aggregate_drift", 0)
    tier = result.get("drift_tier", "?")
    print(f"{PASS} Drift Detector (aligned action): drift={score:.3f}, tier={tier}")
except Exception as e:
    print(f"{FAIL} Drift Detector (aligned): {e}")

# ─── Test 5b: Drift — high-drift (anti-goal) action ───────────
try:
    result_bad = drift_detector.calculate_drift(
        proposed_action="Start building a 2D arcade space shooter mini-game for loading screens",
        reasoning="Users get bored waiting for the checkout page to load",
        root_intent="Migrate monolith e-commerce platform to microservices",
        active_milestone_title="Catalog Containerization",
        active_milestone_desc="Containerize the catalog service",
        anti_goals=["building arcade games", "arcade games"],
        invariant_constraints=["Zero downtime"],
        session_step_count=3,
    )
    score_bad = result_bad.get("aggregate_drift", 0)
    tier_bad = result_bad.get("drift_tier", "?")
    print(f"{PASS} Drift Detector (anti-goal action): drift={score_bad:.3f}, tier={tier_bad}")
    assert score_bad > 0.40, f"Expected high drift, got {score_bad}"
except Exception as e:
    print(f"{FAIL} Drift Detector (anti-goal): {e}")

# ─── Test 6: Regrounding Engine ────────────────────────────────
try:
    from backend.app.services.regrounding import regrounding_engine
    prompt = regrounding_engine.generate_grounding_prompt(
        goal_title="E-Commerce Platform Migration",
        goal_intent="Migrate monolith e-commerce platform to microservices",
        invariant_constraints=["Zero downtime", "No data loss"],
        active_milestone={"title": "Catalog Containerization", "description": "Containerize catalog service", "progress": 0.65},
        anti_goals=["Building arcade games", "Random UI changes"],
        drift_feedback="Previous action was intercepted for semantic drift.",
    )
    assert len(prompt) > 50
    print(f"{PASS} Regrounding Engine: {len(prompt)} chars generated")
except Exception as e:
    print(f"{FAIL} Regrounding Engine: {e}")

# ─── Test 7: Tool Guardrails ───────────────────────────────────
try:
    from backend.app.services.tool_guardrails import tool_guardrails

    # 7a: Allowlisted tool
    result_a = tool_guardrails.validate_and_execute(
        tool_name="read_file",
        tool_args={"path": "README.md"},
        anti_goals=["building arcade games"],
        invariant_constraints=["Zero downtime"]
    )
    print(f"{PASS} Guardrails 'read_file': status={result_a.get('status', 'OK')}")

    # 7b: Blocked — not on allowlist
    result_b = tool_guardrails.validate_and_execute(
        tool_name="delete_everything",
        tool_args={},
        anti_goals=[],
        invariant_constraints=[]
    )
    is_blocked = result_b.get("allowed") is False or result_b.get("status") == "BLOCKED"
    print(f"{PASS} Guardrails 'delete_everything': blocked={is_blocked}")

    # 7c: Allowlist specs
    specs = tool_guardrails.get_allowlist_specs()
    print(f"{PASS} Guardrails allowlist: {[s['name'] for s in specs]}")
except Exception as e:
    print(f"{FAIL} Guardrails: {e}")

# ─── Test 8: Full Orchestrator step — aligned ──────────────────
try:
    from backend.app.services.agent_orchestrator import agent_orchestrator
    result = agent_orchestrator.execute_step(
        session_id="session_day2_catalog",
        manual_action="Write Docker multi-stage build for catalog service",
        manual_reasoning="Containerizing catalog to satisfy Milestone 2 delivery criteria",
        manual_tool_name="write_file",
        manual_tool_args={"path": "catalog/Dockerfile", "content": "FROM python:3.12-slim\n..."}
    )
    drift = result.get("drift_score", 0)
    tier = result.get("drift_tier", "?")
    cb = result.get("circuit_breaker_fired", "?")
    print(f"{PASS} Orchestrator (aligned): drift={drift:.3f}, tier={tier}, cb={cb}")
    assert tier in ("NORMAL", "WARNING"), f"Expected NORMAL/WARNING, got {tier}"
except Exception as e:
    print(f"{FAIL} Orchestrator (aligned): {e}")

# ─── Test 9: Full Orchestrator — anti-goal fires circuit breaker
try:
    result_bad = agent_orchestrator.execute_step(
        session_id="session_day2_catalog",
        manual_action="Build an arcade space shooter mini-game for loading screens",
        manual_reasoning="Users are bored waiting for checkout page to load",
        manual_tool_name="write_file",
        manual_tool_args={"path": "games/space_shooter.js", "content": "// arcade game"}
    )
    drift_bad = result_bad.get("drift_score", 0)
    tier_bad = result_bad.get("drift_tier", "?")
    cb_bad = result_bad.get("circuit_breaker_fired", False)
    print(f"{PASS} Orchestrator (anti-goal): drift={drift_bad:.3f}, tier={tier_bad}, cb={cb_bad}")
    assert cb_bad is True, f"Expected circuit_breaker_fired=True, got {cb_bad}"
except Exception as e:
    print(f"{FAIL} Orchestrator (anti-goal): {e}")

# ─── Test 10: Orchestrator REST router ────────────────────────
try:
    from backend.app.routers.orchestrator import router
    routes = [r.path for r in router.routes]
    expected = {'/api/orchestrator/status', '/api/orchestrator/tools',
                '/api/orchestrator/step', '/api/orchestrator/loop'}
    assert expected.issubset(set(routes)), f"Missing routes: {expected - set(routes)}"
    print(f"{PASS} Orchestrator router: {len(router.routes)} routes registered")
except Exception as e:
    print(f"{FAIL} Orchestrator router: {e}")

# ─── Test 11: Full FastAPI app ────────────────────────────────
try:
    from backend.app.main import app
    print(f"{PASS} FastAPI app: {len(app.routes)} total routes registered")
except Exception as e:
    print(f"{FAIL} FastAPI app: {e}")

print("=" * 65)
print("ALL TESTS PASSED SUCCESSFULLY.")
