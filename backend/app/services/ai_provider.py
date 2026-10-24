import json
import logging
import os
import urllib.request
import urllib.error
from typing import Dict, Any, Optional, List
from backend.app.config import settings

logger = logging.getLogger("northstar.ai_provider")

class AIProviderAdapter:
    def __init__(self):
        self.openai_key = settings.OPENAI_API_KEY
        self.openai_url = settings.OPENAI_BASE_URL
        self.openai_model = settings.OPENAI_MODEL
        self.ollama_url = settings.OLLAMA_BASE_URL
        self.ollama_model = settings.OLLAMA_MODEL
        self.ollama_enabled = os.getenv("OLLAMA_ENABLED", "false").lower() in ("true", "1", "yes")

    def get_provider_status(self) -> Dict[str, Any]:
        """
        Detects available AI providers and returns operational readiness.
        """
        status = {
            "openai": {"configured": bool(self.openai_key), "model": self.openai_model},
            "ollama": {"configured": self.ollama_enabled, "model": self.ollama_model, "endpoint": self.ollama_url},
            "active_provider": "DETERMINISTIC_HEURISTIC_MODEL",
            "model_name": "Northstar-Heuristic-V2",
            "is_live_model": False,
            "message": "Running on Northstar Heuristic Model. Set OPENAI_API_KEY or OLLAMA_ENABLED=true for live LLM inference."
        }

        # Check OpenAI key
        if self.openai_key:
            status["active_provider"] = "LIVE_OPENAI"
            status["model_name"] = self.openai_model
            status["is_live_model"] = True
            status["message"] = f"Connected to OpenAI ({self.openai_model})"
            return status

        # Check Ollama flag
        if self.ollama_enabled:
            status["active_provider"] = "LIVE_OLLAMA"
            status["model_name"] = self.ollama_model
            status["is_live_model"] = True
            status["message"] = f"Connected to Local Ollama ({self.ollama_model})"
            return status

        return status

    def propose_next_action(
        self,
        grounding_prompt: str,
        session_history: List[Dict[str, Any]],
        available_tools: List[Dict[str, Any]],
        injected_steering: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Queries the active AI provider to propose the next action and tool call.
        """
        provider_info = self.get_provider_status()

        # Try Live OpenAI
        if provider_info["active_provider"] == "LIVE_OPENAI":
            try:
                return self._call_openai(grounding_prompt, session_history, available_tools, injected_steering)
            except Exception as e:
                logger.warning(f"OpenAI call failed ({e}); falling back to deterministic model.")

        # Try Live Ollama
        if provider_info["active_provider"] == "LIVE_OLLAMA":
            try:
                return self._call_ollama(grounding_prompt, session_history, available_tools, injected_steering)
            except Exception as e:
                logger.warning(f"Ollama call failed ({e}); falling back to deterministic model.")

        # Fallback Deterministic Engine
        return self._deterministic_proposal(session_history, injected_steering)

    def _call_openai(
        self,
        grounding_prompt: str,
        session_history: List[Dict[str, Any]],
        available_tools: List[Dict[str, Any]],
        injected_steering: Optional[str]
    ) -> Dict[str, Any]:
        system_content = (
            f"{grounding_prompt}\n\n"
            "You are an autonomous execution agent supervised by the Northstar Long-Horizon Goal Layer.\n"
            "Respond strictly in JSON format with keys:\n"
            "{\n"
            '  "thought": "Your internal strategic reasoning referencing the active milestone and invariants",\n'
            '  "proposed_action": "Clear description of the next action",\n'
            '  "tool_name": "Name of tool to invoke from allowlist",\n'
            '  "tool_args": { "argument_name": "value" },\n'
            '  "confidence": 0.95\n'
            "}"
        )

        user_content = f"Recent steps executed: {len(session_history)}.\n"
        if injected_steering:
            user_content += f"NORTHSTAR DIRECTIVE: {injected_steering}\n"
        user_content += "Propose your next logical step to advance the active milestone."

        payload = {
            "model": self.openai_model,
            "messages": [
                {"role": "system", "content": system_content},
                {"role": "user", "content": user_content}
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.2
        }

        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            f"{self.openai_url}/chat/completions",
            data=data,
            headers={
                "Authorization": f"Bearer {self.openai_key}",
                "Content-Type": "application/json"
            }
        )

        with urllib.request.urlopen(req, timeout=10.0) as response:
            res_data = json.loads(response.read().decode("utf-8"))
            content = res_data["choices"][0]["message"]["content"]
            parsed = json.loads(content)
            parsed["provider"] = "LIVE_OPENAI"
            parsed["model"] = self.openai_model
            return parsed

    def _call_ollama(
        self,
        grounding_prompt: str,
        session_history: List[Dict[str, Any]],
        available_tools: List[Dict[str, Any]],
        injected_steering: Optional[str]
    ) -> Dict[str, Any]:
        prompt = (
            f"[SYSTEM]\n{grounding_prompt}\n"
            "Return JSON only with thought, proposed_action, tool_name, tool_args, confidence.\n"
            f"[USER]\nSteps executed: {len(session_history)}. "
        )
        if injected_steering:
            prompt += f"DIRECTIVE: {injected_steering}. "
        prompt += "Propose next action."

        payload = {
            "model": self.ollama_model,
            "prompt": prompt,
            "format": "json",
            "stream": False
        }

        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            f"{self.ollama_url}/api/generate",
            data=data,
            headers={"Content-Type": "application/json"}
        )

        with urllib.request.urlopen(req, timeout=10.0) as response:
            res_data = json.loads(response.read().decode("utf-8"))
            parsed = json.loads(res_data["response"])
            parsed["provider"] = "LIVE_OLLAMA"
            parsed["model"] = self.ollama_model
            return parsed

    def _deterministic_proposal(
        self,
        session_history: List[Dict[str, Any]],
        injected_steering: Optional[str]
    ) -> Dict[str, Any]:
        """
        Deterministic state-machine agent simulating authentic agent execution cycles.
        If a steering intervention was injected, follows the corrective directive.
        """
        step_idx = len(session_history) + 1

        if injected_steering:
            return {
                "thought": "Received Northstar corrective directive. Halting tangential action and re-grounding to active Milestone 2 deliverables.",
                "proposed_action": "Execute cache validation suite to verify Redis expiry rules and p99 latency",
                "tool_name": "validate_test",
                "tool_args": {"test_name": "test_redis_cache_invalidation"},
                "confidence": 0.94,
                "provider": "DETERMINISTIC_HEURISTIC_MODEL",
                "model": "Northstar-Heuristic-V2"
            }

        # Sequence of realistic steps for Milestone 2
        sequence = [
            {
                "thought": "Catalog microservice requires Docker containerization to decouple from legacy monolith.",
                "proposed_action": "Write Dockerfile with multi-stage build for catalog service",
                "tool_name": "write_file",
                "tool_args": {"path": "backend/Dockerfile.catalog", "content": "# Multi-stage Dockerfile\nFROM python:3.12-slim\nWORKDIR /app\n"},
                "confidence": 0.96
            },
            {
                "thought": "Need Redis cache client to satisfy the mandatory p99 < 200ms latency invariant constraint.",
                "proposed_action": "Configure Redis connection pool with exponential backoff",
                "tool_name": "write_file",
                "tool_args": {"path": "backend/cache_pool.py", "content": "# Redis connection pool\n"},
                "confidence": 0.92
            },
            {
                "thought": "Users may experience wait times during checkout; building an arcade space shooter mini-game for loading screens.",
                "proposed_action": "Start coding an arcade space shooter mini-game for user loading screens",
                "tool_name": "write_file",
                "tool_args": {"path": "frontend/src/game/arcade.ts", "content": "// 2D arcade shooter canvas engine\n"},
                "confidence": 0.88
            },
            {
                "thought": "Re-grounded by Northstar. Resuming Redis unit testing to ensure data consistency.",
                "proposed_action": "Run unit test suite for catalog cache invalidation",
                "tool_name": "validate_test",
                "tool_args": {"test_name": "tests/test_cache.py"},
                "confidence": 0.95
            }
        ]

        item = sequence[(step_idx - 1) % len(sequence)]
        item["provider"] = "DETERMINISTIC_HEURISTIC_MODEL"
        item["model"] = "Northstar-Heuristic-V2"
        return item

ai_provider = AIProviderAdapter()
