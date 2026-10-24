import sys
import os
sys.path.insert(0, os.path.abspath("."))

from backend.app.main import app
from backend.app.database import init_db

init_db()

# Test each router function directly (no network/port needed)
from backend.app.routers.goals import list_goals, get_grounding_prompt
from backend.app.routers.drift import get_drift_stats
from backend.app.routers.simulations import list_scenarios, run_simulation
from backend.app.routers.sessions import list_sessions

print("[1] Testing list_goals...")
goals = list_goals()
print(f"    -> Retrieved {len(goals)} goal(s). First goal: {goals[0].title}")
assert len(goals) >= 1

print("[2] Testing get_grounding_prompt...")
prompt_data = get_grounding_prompt(goals[0].id)
prompt = prompt_data["grounding_prompt"]
print(f"    -> Grounding prompt generated ({len(prompt)} chars)")
assert "NORTHSTAR PERSISTENT GOAL LAYER" in prompt

print("[3] Testing get_drift_stats...")
stats = get_drift_stats()
print(f"    -> Alignment Health: {stats['alignment_health_percentage']}%, Avg Drift: {stats['average_drift_score']}")
assert stats["alignment_health_percentage"] > 0

print("[4] Testing list_scenarios & run_simulation...")
scenarios = list_scenarios()
print(f"    -> Found {len(scenarios)} benchmark scenarios")
res = run_simulation("scenario_ecommerce")
print(f"    -> With Northstar: {res['summary_metrics']['with_northstar']['overall_alignment_score']}%")
print(f"    -> Without Northstar: {res['summary_metrics']['without_northstar']['overall_alignment_score']}%")
assert res["summary_metrics"]["with_northstar"]["overall_alignment_score"] > res["summary_metrics"]["without_northstar"]["overall_alignment_score"]

print("[5] Testing list_sessions...")
sessions = list_sessions(goals[0].id)
print(f"    -> Found {len(sessions)} session(s)")
assert len(sessions) >= 1

print("\n>>> ALL API ROUTERS TESTED DIRECTLY & VERIFIED 100% SUCCESSFUL <<<")
