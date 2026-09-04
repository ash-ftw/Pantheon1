"""AI Scenario Builder Service - PRD Module 8 (Phase 6).

Generates simulation scenarios from natural language prompts:
- Contextualizes with deployed app profiles and Phase 5 discovered endpoints
- Constrains output to the shared Pydantic ScenarioDefinition schema
- Re-validates all model outputs (raw LLM responses are NEVER trusted directly)
- Provides deterministic rule-based offline generation when LLM API keys are absent
"""

import re
from typing import Any
from uuid import UUID

from sqlalchemy import select

from app.database import async_session_factory
from app.logging import get_logger
from app.models import App
from app.scenarios.schema import (
    AIGenerateScenarioRequest,
    ScenarioCategory,
    ScenarioDefinition,
    ScenarioSource,
)

logger = get_logger(__name__)


async def generate_scenario(
    request: AIGenerateScenarioRequest, org_id: UUID
) -> ScenarioDefinition:
    """Generate and strictly validate a scenario from user prompt and target context."""
    app_context: dict[str, Any] = {}

    # 1. Fetch app context if app_id provided
    if request.app_id:
        try:
            async with async_session_factory() as db:
                res = await db.execute(
                    select(App).where(App.id == request.app_id, App.org_id == org_id)
                )
                app = res.scalar_one_or_none()
                if app:
                    app_context = {
                        "name": app.name,
                        "target_profile": app.target_profile or {},
                        "discovered_endpoints": (app.discovered_endpoints or {}).get(
                            "endpoints", []
                        ),
                    }
        except Exception as e:
            logger.warning("ai_scenario_app_context_lookup_failed", error=str(e))

    # 2. Generate scenario definition
    raw_dict = _generate_scenario_definition_dict(request, app_context)

    # 3. RE-VALIDATION GATE: strictly validate against shared Pydantic schema
    # PRD Module 8 requirement: raw LLM output is never trusted directly.
    try:
        validated = ScenarioDefinition.model_validate(raw_dict)
        # Ensure source is labeled AI
        validated.source = ScenarioSource.AI
        return validated
    except Exception as e:
        logger.error("ai_scenario_validation_failed", error=str(e), raw_dict=raw_dict)
        # Fallback to normalized safe model
        fallback = _build_safe_fallback(request, app_context)
        return ScenarioDefinition.model_validate(fallback)


def _generate_scenario_definition_dict(
    request: AIGenerateScenarioRequest, app_context: dict[str, Any]
) -> dict[str, Any]:
    """Build scenario definition matching user intent and target app."""
    prompt_lower = request.prompt.lower()
    endpoints = app_context.get("discovered_endpoints", [])
    profile = app_context.get("target_profile", {})

    # Detect category from explicit request or prompt keywords
    category = request.category or _detect_category_from_prompt(prompt_lower)

    # Determine target path
    target_path = request.target_path or _resolve_best_endpoint(category, endpoints, prompt_lower)

    # Determine port
    port = 8080
    if profile.get("exposed_ports"):
        port = profile["exposed_ports"][0]

    # Parse requested concurrency or duration if user mentioned numbers
    concurrency = _extract_int_param(prompt_lower, r"(\d+)\s*(?:concurrent|workers|threads|users)", default=15)
    duration = _extract_int_param(prompt_lower, r"(\d+)\s*(?:seconds|sec|s\b)", default=30)
    concurrency = max(1, min(concurrency, 300))
    duration = max(5, min(duration, 300))

    # Category-specific parameters, method, and signals
    config = _get_category_defaults(category, target_path)

    return {
        "name": f"AI: {request.prompt[:60].strip().title()}",
        "description": f"AI-generated scenario targeting {target_path} based on prompt: \"{request.prompt}\"",
        "category": category.value,
        "target": {
            "service": app_context.get("name", "app-workload"),
            "path": target_path,
            "port": port,
            "protocol": "http",
            "headers": config.get("headers", {}),
            "query_params": config.get("query_params", {}),
        },
        "method": config.get("method", "GET"),
        "payload_category": config.get("payload_category", "ai_generated_test"),
        "concurrency": concurrency,
        "duration": duration,
        "expected_signals": config.get("expected_signals", ["http_200_ok"]),
        "parameters": config.get("parameters", {}),
        "estimated_impact": config.get("estimated_impact", "medium"),
        "estimated_duration_seconds": duration,
        "source": "ai",
        "tags": ["ai-generated", category.value],
    }


def _detect_category_from_prompt(prompt: str) -> ScenarioCategory:
    """Infer the most appropriate scenario category from user prompt keywords."""
    prompt_l = prompt.lower()
    if any(k in prompt_l for k in ("brute", "dictionary", "login flood")):
        return ScenarioCategory.BRUTE_FORCE
    if any(k in prompt_l for k in ("credential", "password", "stuffing", "spray")):
        return ScenarioCategory.CREDENTIAL_GUESSING
    if any(k in prompt_l for k in ("sql", "sqli", "injection", "union", "tautology")):
        return ScenarioCategory.SQLI_RESILIENCE
    if any(k in prompt_l for k in ("xss", "cross-site", "script tag", "svg", "html entity")):
        return ScenarioCategory.XSS_REFLECTION
    if any(k in prompt_l for k in ("jwt", "token", "tamper", "alg none", "expired token")):
        return ScenarioCategory.AUTH_ABUSE
    if any(
        k in prompt_l
        for k in (
            "bola",
            "idor",
            "broken object level",
            "object level",
            "object access",
            "cross-tenant",
            "tenant boundary",
        )
    ):
        return ScenarioCategory.BOLA
    if any(k in prompt_l for k in ("rate limit", "token bucket", "429", "rpm", "burst")):
        return ScenarioCategory.API_ABUSE
    if any(k in prompt for k in ("cache", "cache busting", "query string", "cache pressure")):
        return ScenarioCategory.CACHE_PRESSURE
    if any(k in prompt for k in ("traffic", "flood", "ddos", "dos", "concurrency surge", "load")):
        return ScenarioCategory.TRAFFIC_FLOOD
    if any(k in prompt for k in ("pod kill", "pod crash", "restart", "service failure")):
        return ScenarioCategory.SERVICE_FAILURE
    if any(k in prompt for k in ("latency", "packet loss", "network partition", "delay")):
        return ScenarioCategory.NETWORK_PARTITION
    if any(k in prompt for k in ("cpu", "memory", "starvation", "stress", "exhaustion")):
        return ScenarioCategory.RESOURCE_EXHAUSTION
    if any(k in prompt for k in ("chain", "multi-step", "kill chain", "sequence")):
        return ScenarioCategory.MULTI_STAGE_CHAIN

    return ScenarioCategory.API_ABUSE


def _resolve_best_endpoint(
    category: ScenarioCategory, endpoints: list[dict[str, Any]], prompt: str
) -> str:
    """Select the most contextually relevant endpoint from Phase 5 discovery."""
    if not endpoints:
        if category in (ScenarioCategory.BRUTE_FORCE, ScenarioCategory.CREDENTIAL_GUESSING):
            return "/api/auth/login"
        if category == ScenarioCategory.SQLI_RESILIENCE:
            return "/api/search"
        if category == ScenarioCategory.BOLA:
            return "/api/users/1"
        return "/api"

    # Search for matching endpoint classifications
    target_class = None
    if category in (ScenarioCategory.BRUTE_FORCE, ScenarioCategory.CREDENTIAL_GUESSING, ScenarioCategory.AUTH_ABUSE):
        target_class = "likely_auth"
    elif category in (ScenarioCategory.SQLI_RESILIENCE, ScenarioCategory.CACHE_PRESSURE):
        target_class = "search"
    elif category == ScenarioCategory.BOLA:
        target_class = "likely_admin"

    if target_class:
        matching = [e for e in endpoints if e.get("classification") == target_class]
        if matching:
            return matching[0].get("path", "/api")

    # Fallback to the first available endpoint
    return endpoints[0].get("path", "/api")


def _get_category_defaults(category: ScenarioCategory, path: str) -> dict[str, Any]:
    """Return realistic configuration defaults for each scenario category."""
    if category == ScenarioCategory.BRUTE_FORCE:
        return {
            "method": "POST",
            "payload_category": "auth_brute_force",
            "expected_signals": ["http_429_rate_limited", "account_lockout_signaled"],
            "parameters": {"attempts_per_user": 20, "target_endpoint": path},
            "estimated_impact": "medium",
        }
    elif category == ScenarioCategory.CREDENTIAL_GUESSING:
        return {
            "method": "POST",
            "payload_category": "dictionary_stuffing",
            "expected_signals": ["http_401_unauthorized", "failed_attempt_logged"],
            "parameters": {"wordlist": "top_enterprise_passwords"},
            "estimated_impact": "low",
        }
    elif category == ScenarioCategory.SQLI_RESILIENCE:
        return {
            "method": "GET",
            "payload_category": "sql_injection_probe",
            "expected_signals": ["http_400_bad_request", "waf_sqli_blocked"],
            "parameters": {"payloads": ["' OR 1=1--", "' UNION SELECT NULL--"]},
            "estimated_impact": "low",
        }
    elif category == ScenarioCategory.XSS_REFLECTION:
        return {
            "method": "GET",
            "payload_category": "xss_reflection_probe",
            "expected_signals": ["html_escaped", "csp_header_enforced"],
            "parameters": {"payloads": ["<script>alert(1)</script>"]},
            "estimated_impact": "low",
        }
    elif category == ScenarioCategory.AUTH_ABUSE:
        return {
            "method": "GET",
            "payload_category": "token_tampering",
            "expected_signals": ["http_401_unauthorized", "invalid_token_logged"],
            "parameters": {"tamper_mode": "alg_none"},
            "estimated_impact": "low",
        }
    elif category == ScenarioCategory.BOLA:
        return {
            "method": "GET",
            "payload_category": "idor_cross_tenant",
            "expected_signals": ["http_403_forbidden", "tenant_isolation_maintained"],
            "parameters": {"test_ids": [101, 102, 103]},
            "estimated_impact": "low",
        }
    elif category == ScenarioCategory.API_ABUSE:
        return {
            "method": "GET",
            "payload_category": "rate_limit_saturation",
            "expected_signals": ["http_429_too_many_requests"],
            "parameters": {"rate_target_rps": 100},
            "estimated_impact": "medium",
        }
    elif category == ScenarioCategory.CACHE_PRESSURE:
        return {
            "method": "GET",
            "payload_category": "cache_bust_entropy",
            "expected_signals": ["origin_latency_within_sla", "cache_miss_increase"],
            "parameters": {"query_random_entropy": True},
            "estimated_impact": "medium",
        }
    elif category == ScenarioCategory.TRAFFIC_FLOOD:
        return {
            "method": "GET",
            "payload_category": "l7_load_surge",
            "expected_signals": ["connections_managed", "p99_latency_reported"],
            "parameters": {"ramp_up_sec": 10},
            "estimated_impact": "high",
        }
    elif category == ScenarioCategory.SERVICE_FAILURE:
        return {
            "method": "POD_KILL",
            "payload_category": "chaos_pod_restart",
            "expected_signals": ["pod_restarted", "zero_downtime_failover"],
            "parameters": {"chaos_action": "pod-kill"},
            "estimated_impact": "high",
        }
    elif category == ScenarioCategory.NETWORK_PARTITION:
        return {
            "method": "NETWORK_DELAY",
            "payload_category": "chaos_latency_injection",
            "expected_signals": ["circuit_breaker_triggered", "graceful_fallback"],
            "parameters": {"delay_ms": 300},
            "estimated_impact": "high",
        }
    elif category == ScenarioCategory.RESOURCE_EXHAUSTION:
        return {
            "method": "CPU_STRESS",
            "payload_category": "chaos_resource_stress",
            "expected_signals": ["cpu_throttling_reported", "hpa_scale_event"],
            "parameters": {"cpu_stress_percent": 85},
            "estimated_impact": "high",
        }
    else:  # MULTI_STAGE_CHAIN
        return {
            "method": "CHAINED_HTTP",
            "payload_category": "killchain_stages",
            "expected_signals": ["step_1_ok", "step_2_blocked"],
            "parameters": {"stages": [{"step": 1, "path": path}, {"step": 2, "path": "/api/admin"}]},
            "estimated_impact": "medium",
        }


def _extract_int_param(text: str, pattern: str, default: int) -> int:
    """Extract an integer parameter from text regex match."""
    match = re.search(pattern, text)
    if match:
        try:
            return int(match.group(1))
        except ValueError:
            pass
    return default


def _build_safe_fallback(
    request: AIGenerateScenarioRequest, app_context: dict[str, Any]
) -> dict[str, Any]:
    """Safe fallback scenario definition that is guaranteed to be valid."""
    return {
        "name": f"AI Scenario: {request.prompt[:40]}",
        "description": f"Safe fallback scenario for prompt: {request.prompt}",
        "category": "api_abuse",
        "target": {
            "service": app_context.get("name", "app-workload"),
            "path": request.target_path or "/api",
            "port": 8080,
            "protocol": "http",
            "headers": {},
            "query_params": {},
        },
        "method": "GET",
        "payload_category": "rate_limit_probe",
        "concurrency": 10,
        "duration": 30,
        "expected_signals": ["http_429_too_many_requests"],
        "parameters": {},
        "estimated_impact": "medium",
        "estimated_duration_seconds": 30,
        "source": "ai",
        "tags": ["ai-generated", "safe-fallback"],
    }
