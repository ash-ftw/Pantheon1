"""Tests for Network Readiness & Dynamic Host Resolution.

Verifies:
1. CORS configuration and origin regex matches LAN / private network clients.
2. Discovery service respects PANTHEON_TARGET_HOST and app probe_host configurations.
3. Preview endpoints dynamically adapt to external client host headers.
"""

import os
import re
import uuid
from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.config import Settings
from app.main import app
from app.services.discovery_service import discover_endpoints


def test_cors_settings_and_origin_regex() -> None:
    """Verify default CORS settings allow localhost and private LAN origins."""
    settings = Settings()
    assert "http://localhost:5173" in settings.cors_origins
    assert "http://127.0.0.1:5173" in settings.cors_origins
    assert settings.cors_origin_regex is not None

    pattern = re.compile(settings.cors_origin_regex)

    # Allowed network origins
    assert pattern.match("http://localhost:5173")
    assert pattern.match("http://127.0.0.1:3000")
    assert pattern.match("http://192.168.1.50:5173")
    assert pattern.match("http://10.0.0.15:8080")
    assert pattern.match("http://172.20.0.5:5173")
    assert pattern.match("http://dev-box.local:5173")
    assert pattern.match("https://pantheon.internal")


@pytest.mark.asyncio
async def test_discovery_probes_configured_target_host() -> None:
    """Verify discover_endpoints honors PANTHEON_TARGET_HOST."""
    custom_host = "test-target-service.tenant-ns.svc.cluster.local"
    probed_urls = []

    import httpx

    async def mock_get(url, *args, **kwargs):
        probed_urls.append(str(url))
        return httpx.Response(status_code=404)

    with patch.dict(os.environ, {"PANTHEON_TARGET_HOST": custom_host}):
        with patch("httpx.AsyncClient.get", side_effect=mock_get):
            with patch("app.services.discovery_service.async_session_factory"):
                profile = await discover_endpoints(uuid.uuid4(), uuid.uuid4())

    assert len(probed_urls) > 0
    for url in probed_urls:
        assert custom_host in url
    assert profile["specs_found"] == []


@pytest.mark.asyncio
async def test_preview_endpoint_adapts_to_request_host() -> None:
    """Verify preview endpoint uses client host header for base tags and direct links."""
    app_id = uuid.uuid4()
    client_host = "192.168.1.105:5173"

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # When target container is offline, fallback page is returned with client host
        response = await client.get(
            f"/api/apps/{app_id}/preview",
            headers={"x-forwarded-host": client_host},
            params={"target_port": 8085},
        )
        assert response.status_code == 200
        html = response.text
        # Fallback HTML should include the external client host rather than hardcoded localhost
        assert "192.168.1.105:8085" in html
        assert "http://localhost:8085" not in html
