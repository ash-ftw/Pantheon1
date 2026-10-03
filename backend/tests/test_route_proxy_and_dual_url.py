"""Pantheon Backend — Tests for Dual-URL Route Broker & Secure Reverse Proxy (PRD §7.5)."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.database import async_session_factory
from app.main import app
from app.models import Org, Route, User
from app.services.auth_service import create_access_token


@pytest.fixture
async def auth_client():
    async with async_session_factory() as session:
        # Create test org & user
        suffix = datetime.now().timestamp()
        org = Org(name="Proxy Test Org", slug=f"proxy-org-{suffix}")
        session.add(org)
        await session.flush()

        user = User(
            email=f"proxy_tester_{suffix}@pantheon.local",
            hashed_password="hashed_test_password",
            full_name="Proxy Tester",
            role="owner",
            org_id=org.id,
            is_active=True,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)

        token = create_access_token(
            user_id=user.id, email=user.email, org_id=org.id, role="owner"
        )

    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://test",
        headers={"Authorization": f"Bearer {token}"},
    ) as client:
        yield client, str(org.id)


@pytest.mark.asyncio
async def test_dual_url_returned_on_route_creation(auth_client):
    client, _org_id = auth_client

    with patch(
        "app.services.route_broker.k8s_tenant_service.create_ingress_route",
    ) as mock_k8s:
        mock_k8s.return_value = {"ingress_name": "route-testdual", "status": "created"}

        res = await client.post(
            "/api/routes",
            json={
                "target_service": "chess-service",
                "target_port": 8080,
                "ttl_seconds": 1800,
                "path_prefix": "/",
            },
        )
        assert res.status_code == 201
        data = res.json()

        assert "internal_url" in data
        assert "public_url" in data
        assert "svc.cluster.local:8080" in data["internal_url"]
        assert "/r/" in data["public_url"]
        assert data["status"] == "active"


@pytest.mark.asyncio
async def test_proxy_404_on_unknown_route():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/r/nonexistent123")
        assert res.status_code == 404
        assert "not found in registry" in res.json()["detail"]


@pytest.mark.asyncio
async def test_proxy_403_on_revoked_route():
    async with async_session_factory() as session:
        org = Org(name="Revoked Test Org", slug=f"revoked-org-{datetime.now().timestamp()}")
        session.add(org)
        await session.flush()

        route = Route(
            org_id=org.id,
            target_service="chess",
            target_port=8080,
            path_prefix="/",
            route_url="http://route-revoked.local:8080",
            status="revoked",
            ttl_seconds=1800,
            expires_at=datetime.now(UTC) + timedelta(minutes=20),
            revoked_at=datetime.now(UTC),
            revocation_reason="manual_kill_switch",
            ingress_name="route-revoked12",
            namespace=f"pantheon-tenant-{str(org.id)[:12]}",
        )
        session.add(route)
        await session.commit()
        await session.refresh(route)
        route_id = str(route.id)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get(f"/r/{route_id[:8]}")
        assert res.status_code == 403
        assert "revoked" in res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_proxy_410_on_expired_route():
    async with async_session_factory() as session:
        org = Org(name="Expired Test Org", slug=f"expired-org-{datetime.now().timestamp()}")
        session.add(org)
        await session.flush()

        route = Route(
            org_id=org.id,
            target_service="chess",
            target_port=8080,
            path_prefix="/",
            route_url="http://route-expired.local:8080",
            status="active",
            ttl_seconds=1800,
            expires_at=datetime.now(UTC) - timedelta(minutes=5),  # in past
            ingress_name="route-expired12",
            namespace=f"pantheon-tenant-{str(org.id)[:12]}",
        )
        session.add(route)
        await session.commit()
        await session.refresh(route)
        route_id = str(route.id)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get(f"/r/{route_id[:8]}")
        assert res.status_code == 410
        assert "expired" in res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_proxy_forwards_to_target_and_strips_frame_headers():
    async with async_session_factory() as session:
        org = Org(name="Forward Test Org", slug=f"fwd-org-{datetime.now().timestamp()}")
        session.add(org)
        await session.flush()

        route = Route(
            org_id=org.id,
            target_service="chess",
            target_port=8080,
            path_prefix="/",
            route_url="http://route-forward.local:8080",
            status="active",
            ttl_seconds=1800,
            expires_at=datetime.now(UTC) + timedelta(minutes=25),
            ingress_name="route-forward12",
            namespace=f"pantheon-tenant-{str(org.id)[:12]}",
        )
        session.add(route)
        await session.commit()
        await session.refresh(route)
        route_id = str(route.id)

    # Mock the internal proxy HTTP request specifically in route_proxy
    class MockProxyResponse:
        def __init__(self):
            self.status_code = 200
            self.content = b"<html><body>Chess Board Application Ready</body></html>"
            self.headers = {
                "content-type": "text/html",
                "x-frame-options": "DENY",
                "content-security-policy": "frame-ancestors 'none'",
            }

    with patch("app.routers.route_proxy.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.request.return_value = MockProxyResponse()
        mock_client_cls.return_value = mock_client

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            res = await client.get(f"/r/{route_id[:8]}/play")
            assert res.status_code == 200
            assert b"Chess Board Application Ready" in res.content
            # Verify restrictive frame headers were stripped for UI embedding
            assert "x-frame-options" not in res.headers
            assert "content-security-policy" not in res.headers
            assert "x-pantheon-route-id" in res.headers
