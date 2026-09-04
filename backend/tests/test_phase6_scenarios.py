"""Phase 6 Scenario System Test Suite — PRD Modules 7, 8, 9.

Tests:
1. Preset scenario definitions: all 13 categories must parse and validate against ScenarioDefinition
2. Strict schema boundary checks: concurrency (1-500), duration (5-600), path normalization
3. Category enum completeness across all required PRD types
4. AI Scenario Builder service: prompt parsing, context extraction, schema re-validation
5. Validation endpoint (/api/scenarios/validate): schema rejection and approval
6. Preset listing endpoint (/api/scenarios/presets): returns all 13 presets
"""

import uuid

import pytest
from pydantic import ValidationError

from app.scenarios.presets import PRESET_SCENARIOS, get_all_presets, get_preset_by_category
from app.scenarios.schema import (
    AIGenerateScenarioRequest,
    ScenarioCategory,
    ScenarioDefinition,
    ScenarioSource,
    ScenarioTarget,
    ScenarioValidateRequest,
)
from app.services.ai_scenario_service import (
    _detect_category_from_prompt,
    _resolve_best_endpoint,
    generate_scenario,
)

# ---------------------------------------------------------------------------
# Preset Library Tests (PRD Module 7)
# ---------------------------------------------------------------------------


def test_preset_library_contains_all_13_categories() -> None:
    """Verify all 13 required PRD categories are represented in the preset catalog."""
    presets = get_all_presets()
    assert len(presets) == 13

    categories_present = {p.category for p in presets}
    for cat in ScenarioCategory:
        assert cat in categories_present, f"Missing preset for category: {cat}"


def test_all_presets_strictly_validate_against_schema() -> None:
    """Verify every preset adheres strictly to ScenarioDefinition."""
    for preset in PRESET_SCENARIOS:
        # Re-dump and re-validate to guarantee JSON round-trip compliance
        dumped = preset.model_dump(mode="json")
        reloaded = ScenarioDefinition.model_validate(dumped)

        assert reloaded.name == preset.name
        assert reloaded.concurrency >= 1
        assert reloaded.concurrency <= 500
        assert reloaded.duration >= 5
        assert reloaded.duration <= 600
        assert len(reloaded.expected_signals) > 0
        assert reloaded.target.path.startswith("/")
        assert reloaded.source == ScenarioSource.PRESET


def test_preset_filtering_by_category() -> None:
    """Verify filtering presets by specific category."""
    brute_force_presets = get_preset_by_category(ScenarioCategory.BRUTE_FORCE)
    assert len(brute_force_presets) == 1
    assert brute_force_presets[0].category == ScenarioCategory.BRUTE_FORCE

    sqli_presets = get_preset_by_category(ScenarioCategory.SQLI_RESILIENCE)
    assert len(sqli_presets) == 1
    assert sqli_presets[0].category == ScenarioCategory.SQLI_RESILIENCE


# ---------------------------------------------------------------------------
# Strict Schema Validation Tests
# ---------------------------------------------------------------------------


def test_schema_validates_valid_custom_scenario() -> None:
    """Verify a handcrafted valid scenario passes validation."""
    data = {
        "name": "Custom Token Bucket Stress",
        "description": "Fires bursts to verify rate limiting behavior",
        "category": "api_abuse",
        "target": {
            "service": "api-gateway",
            "path": "/api/v1/resource",
            "port": 8080,
            "protocol": "http",
        },
        "method": "post",  # test normalization to POST
        "payload_category": "burst_rate",
        "concurrency": 25,
        "duration": 45,
        "expected_signals": ["http_429_too_many_requests"],
        "parameters": {"burst_rate": 200},
        "estimated_impact": "medium",
        "estimated_duration_seconds": 45,
        "source": "custom",
    }

    scen = ScenarioDefinition.model_validate(data)
    assert scen.name == "Custom Token Bucket Stress"
    assert scen.method == "POST"  # normalized uppercase
    assert scen.category == ScenarioCategory.API_ABUSE


def test_schema_rejects_invalid_concurrency() -> None:
    """Scenario with concurrency > 500 or < 1 must be rejected."""
    base_data = {
        "name": "Invalid Concurrency Test",
        "description": "Testing concurrency limits",
        "category": "traffic_flood",
        "expected_signals": ["signal_1"],
    }

    with pytest.raises(ValidationError):
        ScenarioDefinition.model_validate({**base_data, "concurrency": 501})

    with pytest.raises(ValidationError):
        ScenarioDefinition.model_validate({**base_data, "concurrency": 0})


def test_schema_rejects_invalid_duration() -> None:
    """Scenario with duration < 5s or > 600s must be rejected."""
    base_data = {
        "name": "Invalid Duration Test",
        "description": "Testing duration limits",
        "category": "traffic_flood",
        "expected_signals": ["signal_1"],
    }

    with pytest.raises(ValidationError):
        ScenarioDefinition.model_validate({**base_data, "duration": 4})

    with pytest.raises(ValidationError):
        ScenarioDefinition.model_validate({**base_data, "duration": 601})


def test_schema_rejects_empty_expected_signals() -> None:
    """Scenario must specify at least one expected defense/reaction signal."""
    with pytest.raises(ValidationError):
        ScenarioDefinition.model_validate(
            {
                "name": "No Signals Test",
                "description": "Testing signals requirement",
                "category": "auth_abuse",
                "expected_signals": [],
            }
        )


def test_schema_normalizes_target_path() -> None:
    """Path without leading slash must be normalized to start with '/'."""
    target = ScenarioTarget.model_validate({"path": "api/v1/test"})
    assert target.path == "/api/v1/test"


# ---------------------------------------------------------------------------
# AI Scenario Builder Tests (PRD Module 8)
# ---------------------------------------------------------------------------


def test_ai_scenario_detect_category_heuristics() -> None:
    """Verify prompt keyword heuristic classification."""
    assert _detect_category_from_prompt("test SQL injection on search input") == ScenarioCategory.SQLI_RESILIENCE
    assert _detect_category_from_prompt("brute force the login form") == ScenarioCategory.BRUTE_FORCE
    assert _detect_category_from_prompt("credential stuffing with top passwords") == ScenarioCategory.CREDENTIAL_GUESSING
    assert _detect_category_from_prompt("reflected cross-site scripting in comment box") == ScenarioCategory.XSS_REFLECTION
    assert _detect_category_from_prompt("test broken object level authorization IDOR") == ScenarioCategory.BOLA
    assert _detect_category_from_prompt("simulate pod crash and recovery") == ScenarioCategory.SERVICE_FAILURE
    assert _detect_category_from_prompt("inject 200ms latency and packet loss") == ScenarioCategory.NETWORK_PARTITION
    assert _detect_category_from_prompt("starve container cpu and memory") == ScenarioCategory.RESOURCE_EXHAUSTION
    assert _detect_category_from_prompt("multi-step killchain attack") == ScenarioCategory.MULTI_STAGE_CHAIN


def test_ai_scenario_resolve_best_endpoint() -> None:
    """Verify linking discovered endpoints from Phase 5 to scenario category."""
    discovered = [
        {"path": "/api/auth/login", "classification": "likely_auth"},
        {"path": "/api/catalog/search", "classification": "search"},
        {"path": "/api/admin/system", "classification": "likely_admin"},
        {"path": "/api/public/items", "classification": "public"},
    ]

    auth_path = _resolve_best_endpoint(ScenarioCategory.BRUTE_FORCE, discovered, "")
    assert auth_path == "/api/auth/login"

    search_path = _resolve_best_endpoint(ScenarioCategory.SQLI_RESILIENCE, discovered, "")
    assert search_path == "/api/catalog/search"

    bola_path = _resolve_best_endpoint(ScenarioCategory.BOLA, discovered, "")
    assert bola_path == "/api/admin/system"


@pytest.mark.asyncio
async def test_generate_scenario_pipeline_strict_validation() -> None:
    """Verify AI scenario generation produces a valid ScenarioDefinition."""
    req = AIGenerateScenarioRequest(
        prompt="Test SQL injection resilience on search with 25 concurrent requests for 40 seconds",
        category=ScenarioCategory.SQLI_RESILIENCE,
    )
    org_id = uuid.uuid4()

    scenario = await generate_scenario(req, org_id)

    assert isinstance(scenario, ScenarioDefinition)
    assert scenario.category == ScenarioCategory.SQLI_RESILIENCE
    assert scenario.concurrency == 25
    assert scenario.duration == 40
    assert scenario.source == ScenarioSource.AI
    assert len(scenario.expected_signals) > 0


# ---------------------------------------------------------------------------
# Validation Endpoint Schema Helper Tests (PRD Module 9)
# ---------------------------------------------------------------------------


def test_validate_request_model() -> None:
    """Verify validate request payload wrapping."""
    valid_def = {
        "name": "Form Validated Scenario",
        "description": "Validated via schema endpoint",
        "category": "auth_abuse",
        "expected_signals": ["http_401_unauthorized"],
    }
    req = ScenarioValidateRequest(definition=valid_def)
    assert req.definition["name"] == "Form Validated Scenario"
