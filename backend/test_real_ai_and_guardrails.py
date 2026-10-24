import sys
import os
import asyncio
sys.path.insert(0, os.path.abspath("."))

from backend.app.database import init_db, db_session
from backend.app.services.ai_provider import ai_provider
from backend.app.services.tool_guardrails import tool_guardrails
from backend.app.services.agent_orchestrator import agent_orchestrator

async def run_tests():
    print("[1/4] Testing AI Provider Adapter...")
    init_db()
    status = await ai_provider.get_provider_status()
    print(f"      -> Provider: {status['active_provider']}, Model: {status['model_name']}, Live: {status['is_live_model']}")
    assert "active_provider" in status

    print("[2/4] Testing Pre-Execution Guardrail Security Enforcement...")
    # Safe tool
    safe_res = tool_guardrails.validate_and_execute(
        tool_name="list_files",
        tool_args={"directory": "backend"},
        anti_goals=["Building arcade games"],
        invariant_constraints=["PCI-DSS"]
    )
    print(f"      -> Safe tool call: {safe_res['status']} (Allowed: {safe_res['allowed']})")
    assert safe_res["allowed"] is True

    # Unauthorized tool call
    unauth_res = tool_guardrails.validate_and_execute(
        tool_name="download_remote_malware_binary",
        tool_args={"url": "http://evil.com"},
        anti_goals=[],
        invariant_constraints=[]
    )
    print(f"      -> Unauthorized tool call: {unauth_res['status']} (Allowed: {unauth_res['allowed']})")
    assert unauth_res["allowed"] is False
    assert unauth_res["status"] == "BLOCKED_UNAUTHORIZED_TOOL"

    # Workspace containment breach (Path traversal)
    traversal_res = tool_guardrails.validate_and_execute(
        tool_name="read_file",
        tool_args={"path": "../../../Windows/System32/drivers/etc/hosts"},
        anti_goals=[],
        invariant_constraints=[]
    )
    print(f"      -> Path traversal attempt: {traversal_res['status']} (Allowed: {traversal_res['allowed']})")
    assert traversal_res["allowed"] is False
    assert traversal_res["status"] == "BLOCKED_PATH_TRAVERSAL"

    # Anti-Goal breach (Attempting to write an arcade mini-game)
    antigoal_res = tool_guardrails.validate_and_execute(
        tool_name="write_file",
        tool_args={"path": "arcade_game.ts", "content": "const arcade_shooter = new Game();"},
        anti_goals=["Building custom GUI arcade games or unrelated utilities"],
        invariant_constraints=[]
    )
    print(f"      -> Anti-Goal breach attempt: {antigoal_res['status']} (Allowed: {antigoal_res['allowed']})")
    assert antigoal_res["allowed"] is False
    assert antigoal_res["status"] == "BLOCKED_ANTI_GOAL_BREACH"

    print("[3/4] Testing Agent Orchestrator Controlled Execution Loop...")
    step_res = await agent_orchestrator.execute_step(
        session_id="session_day2_catalog",
        manual_action="Verify Redis cache connection pool to maintain p99 < 200ms latency",
        manual_reasoning="Milestone 2 deliverable requirement",
        manual_tool_name="validate_test",
        manual_tool_args={"test_name": "test_redis_cache"}
    )
    print(f"      -> In-scope step executed: Drift {step_res['drift_score']} (Tier: {step_res['drift_tier']})")
    print(f"         Circuit Breaker: {step_res['circuit_breaker_fired']}, Output: {step_res['execution_result'][:60]}...")
    assert step_res["circuit_breaker_fired"] is False

    # Test an out-of-scope tangent step
    tangent_res = await agent_orchestrator.execute_step(
        session_id="session_day2_catalog",
        manual_action="Code a retro arcade mini-game for user loading animations",
        manual_reasoning="Thought users might get bored waiting",
        manual_tool_name="write_file",
        manual_tool_args={"path": "frontend/arcade.ts", "content": "class ArcadeGame {}"}
    )
    print(f"      -> Tangent step executed: Drift {tangent_res['drift_score']} (Tier: {tangent_res['drift_tier']})")
    print(f"         Circuit Breaker Fired: {tangent_res['circuit_breaker_fired']}")
    print(f"         Intervention: {tangent_res['intervention_details'][:80]}...")
    assert tangent_res["circuit_breaker_fired"] is True

    print("[4/4] Verifying Persistence in SQLite across execution...")
    with db_session() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM steps WHERE session_id = 'session_day2_catalog'")
        total_steps = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM drift_audits WHERE session_id = 'session_day2_catalog'")
        total_audits = cursor.fetchone()[0]
        print(f"      -> Total persisted steps: {total_steps}, Audits: {total_audits}")
        assert total_steps >= 6
        assert total_audits >= 6

    print("\n>>> ALL REAL AI INTEGRATION & PRE-EXECUTION GUARDRAIL TESTS PASSED 100% <<<")

if __name__ == "__main__":
    asyncio.run(run_tests())
