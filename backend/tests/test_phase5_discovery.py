"""Phase 5 AI Target Analysis & Endpoint Discovery Test Suite — PRD Modules 5 & 6.

Tests:
1. Language & framework detection heuristics (_detect_language_framework)
2. Endpoint classification heuristics (_classify_endpoint)
3. Classification confidence scoring (_compute_classification_confidence)
4. OpenAPI/Swagger endpoint extraction and categorization (_extract_endpoints_from_spec)
5. Exposed port lookup helper (_get_app_exposed_port)
6. Offline / simulated target analysis fallback (run_target_analysis)
7. HTTP probing endpoint discovery with mock OpenAPI spec (discover_endpoints)
8. Pydantic schema validation for target analysis and endpoint responses
"""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.schemas import (
    DiscoveryEndpointItem,
    DiscoveryEndpointsResponse,
    DiscoveryTargetAnalysisResponse,
)
from app.services.discovery_service import (
    _classify_endpoint,
    _compute_classification_confidence,
    _detect_language_framework,
    _extract_endpoints_from_spec,
    _get_app_exposed_port,
    discover_endpoints,
    run_target_analysis,
)

# ---------------------------------------------------------------------------
# Heuristic & Classification Unit Tests
# ---------------------------------------------------------------------------


def test_detect_language_framework_heuristics() -> None:
    """Verify Docker image name heuristics correctly detect languages and frameworks."""
    cases = [
        ("python:3.11-fastapi", "python", "fastapi"),
        ("my-django-app:v1", "python", "django"),
        ("flask-service:latest", "python", "flask"),
        ("node:18-alpine", "javascript", "unknown"),
        ("node-express-api:2.0", "javascript", "express"),
        ("openjdk:17-spring", "java", "spring boot"),
        ("ruby:3.2", "ruby", "ror"),
        ("golang:1.21", "go", "unknown"),
        ("php:8.2-laravel", "php", "laravel"),
        ("php:8.1-symfony", "php", "symfony"),
    ]

    for image, expected_lang, expected_fw in cases:
        profile = {"language": None, "framework": None}
        res = _detect_language_framework(image, profile)
        assert res["language"] == expected_lang, f"Failed language for {image}"
        assert res["framework"] == expected_fw, f"Failed framework for {image}"


def test_classify_endpoint_heuristics() -> None:
    """Verify endpoint path & description patterns map to correct classification buckets."""
    assert _classify_endpoint("/api/v1/auth/login", "post", {}) == "likely_auth"
    assert _classify_endpoint("/oauth/token", "post", {}) == "likely_auth"
    assert _classify_endpoint("/user/register", "post", {}) == "likely_auth"

    assert _classify_endpoint("/admin/users", "get", {}) == "likely_admin"
    assert _classify_endpoint("/manage/system-settings", "get", {}) == "likely_admin"

    assert _classify_endpoint("/api/v1/upload", "post", {}) == "upload"
    assert _classify_endpoint("/profiles/avatar", "put", {}) == "upload"

    assert _classify_endpoint("/api/search", "get", {}) == "search"
    assert _classify_endpoint("/items/filter", "get", {}) == "search"

    assert _classify_endpoint("/healthz", "get", {}) == "public"
    assert _classify_endpoint("/products", "get", {}) == "public"


def test_classification_confidence_scoring() -> None:
    """Verify confidence level and basis explanation computation."""
    # High confidence: multiple signals (path + summary + security)
    conf_high, basis_high = _compute_classification_confidence(
        "/api/auth/login",
        "post",
        {"summary": "User login", "security": [{"OAuth2": []}]},
        "likely_auth",
    )
    assert conf_high == "high"
    assert "path contains" in basis_high
    assert "summary metadata present" in basis_high

    # Medium confidence: single signal
    conf_med, basis_med = _compute_classification_confidence(
        "/api/v1/upload",
        "post",
        {},
        "upload",
    )
    assert conf_med == "medium"
    assert "path contains 'upload'" in basis_med

    # Low confidence: default public
    conf_low, basis_low = _compute_classification_confidence(
        "/info",
        "get",
        {},
        "public",
    )
    assert conf_low == "low"
    assert "default classification" in basis_low


def test_get_app_exposed_port() -> None:
    """Verify exposed port resolution from target profile with default fallback."""
    assert _get_app_exposed_port(None) == 8085
    assert _get_app_exposed_port({}) == 8085
    assert _get_app_exposed_port({"exposed_ports": []}) == 8085
    assert _get_app_exposed_port({"exposed_ports": [3000, 8080]}) == 3000


def test_extract_endpoints_from_spec() -> None:
    """Verify OpenAPI spec extraction, normalization, and classification grouping."""
    sample_spec = {
        "openapi": "3.0.0",
        "info": {"title": "Sample API", "version": "1.0.0"},
        "paths": {
            "/api/auth/token": {
                "post": {
                    "summary": "Obtain JWT token",
                    "parameters": [{"name": "grant_type", "in": "query"}],
                }
            },
            "/api/admin/dashboard": {
                "get": {
                    "summary": "Admin dashboard overview",
                    "security": [{"BearerAuth": []}],
                }
            },
            "/api/files/upload": {
                "post": {
                    "summary": "Upload file asset",
                }
            },
            "/api/items/search": {
                "get": {
                    "summary": "Search catalog items",
                }
            },
            "/api/health": {
                "get": {
                    "summary": "Health check",
                }
            },
        },
    }

    profile: dict = {
        "endpoints": [],
        "classification": {
            "public": [],
            "likely_admin": [],
            "likely_auth": [],
            "upload": [],
            "search": [],
        },
    }

    _extract_endpoints_from_spec(sample_spec, profile)

    assert len(profile["endpoints"]) == 5
    assert len(profile["classification"]["likely_auth"]) == 1
    assert profile["classification"]["likely_auth"][0]["path"] == "/api/auth/token"
    assert profile["classification"]["likely_auth"][0]["method"] == "POST"

    assert len(profile["classification"]["likely_admin"]) == 1
    assert profile["classification"]["likely_admin"][0]["path"] == "/api/admin/dashboard"

    assert len(profile["classification"]["upload"]) == 1
    assert profile["classification"]["upload"][0]["path"] == "/api/files/upload"

    assert len(profile["classification"]["search"]) == 1
    assert profile["classification"]["search"][0]["path"] == "/api/items/search"

    assert len(profile["classification"]["public"]) == 1
    assert profile["classification"]["public"][0]["path"] == "/api/health"


# ---------------------------------------------------------------------------
# Target Analysis & Discovery Execution Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_run_target_analysis_simulated_mode() -> None:
    """When no K8s cluster client is active, returns simulated fallback profile with low confidence."""
    app_id = uuid.uuid4()
    org_id = uuid.uuid4()

    # Mock DB call in step 1 to raise or return None
    with patch(
        "app.services.discovery_service.async_session_factory"
    ) as mock_session_factory, patch(
        "app.services.discovery_service.k8s_tenant_service._get_client",
        return_value=None,
    ):
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = None
        mock_session.execute.return_value = mock_result
        mock_session_factory.return_value.__aenter__.return_value = mock_session

        profile = await run_target_analysis(app_id, org_id)

        assert profile["app_id"] == str(app_id)
        assert profile["org_id"] == str(org_id)
        assert profile["discovery_status"] == "completed"
        assert profile["language"] == "python"
        assert profile["framework"] == "fastapi"
        assert 8080 in profile["exposed_ports"]
        assert profile["detected_db"] == "postgresql"
        assert "DB_HOST" in profile["db_environment_variables"]
        assert "JWT_SECRET" in profile["auth_env_variables"]
        assert profile["confidence"] == "low"
        assert "Simulated mode" in profile["confidence_basis"]


@pytest.mark.asyncio
async def test_discover_endpoints_mocked_http() -> None:
    """Verify endpoint discovery probes OpenAPI endpoint and returns structured response."""
    app_id = uuid.uuid4()
    org_id = uuid.uuid4()

    sample_openapi = {
        "openapi": "3.0.1",
        "paths": {
            "/login": {
                "post": {
                    "summary": "Login user",
                }
            },
            "/ping": {
                "get": {
                    "summary": "Ping service",
                }
            },
        },
    }

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.headers = {"content-type": "application/json"}
    mock_resp.json.return_value = sample_openapi

    with patch(
        "app.services.discovery_service.async_session_factory"
    ) as mock_session_factory, patch(
        "httpx.AsyncClient.get",
        new=AsyncMock(return_value=mock_resp),
    ):
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result
        mock_session_factory.return_value.__aenter__.return_value = mock_session

        result = await discover_endpoints(app_id, org_id)

        assert len(result["specs_found"]) == 1
        assert result["specs_found"][0] == "/openapi.json"
        assert len(result["endpoints"]) == 2
        paths = [ep["path"] for ep in result["endpoints"]]
        assert "/login" in paths
        assert "/ping" in paths
        assert len(result["classification"]["likely_auth"]) == 1
        assert len(result["classification"]["public"]) == 1


def test_discovery_pydantic_schemas() -> None:
    """Verify Pydantic response models deserialize properly."""
    target_data = {
        "app_id": str(uuid.uuid4()),
        "org_id": str(uuid.uuid4()),
        "namespace": "tenant-test",
        "discovery_status": "completed",
        "language": "python",
        "framework": "fastapi",
        "exposed_ports": [8000],
        "detected_db": "postgresql",
        "db_environment_variables": ["DATABASE_URL"],
        "auth_mechanisms": ["jwt"],
        "auth_env_variables": ["JWT_SECRET"],
        "confidence": "high",
        "confidence_basis": "ingestion-detected-framework, k8s-port-discovery",
    }
    target_model = DiscoveryTargetAnalysisResponse(**target_data)
    assert target_model.language == "python"
    assert target_model.confidence == "high"

    endpoint_item = DiscoveryEndpointItem(
        path="/users",
        method="GET",
        summary="List users",
        description="Retrieve user list",
        classification="public",
        confidence="medium",
        confidence_basis="path contains 'users'",
        parameters=[],
    )
    endpoints_data = {
        "app_id": str(uuid.uuid4()),
        "org_id": str(uuid.uuid4()),
        "namespace": "tenant-test",
        "discovery_status": "completed",
        "specs_found": ["/openapi.json"],
        "endpoints": [endpoint_item],
        "classification": {"public": [endpoint_item]},
    }
    endpoints_model = DiscoveryEndpointsResponse(**endpoints_data)
    assert len(endpoints_model.endpoints) == 1
    assert endpoints_model.endpoints[0].classification == "public"
