"""Phase 8 Route Broker & Emergency Kill Switch Test Suite — PRD §7.5 / Module 11.

Tests:
1. Open route creates active record with Ingress and TTL annotations.
2. Emergency kill switch executes synchronously in under 5 seconds (NFR-3.1).
3. Periodic TTL sweep revokes expired routes (NFR-2.1).
4. Rejects disallowed non-application ports (L3/L4 prohibition FR-5.5).
5. Rejects out-of-scope targets (Simulation Guard integration FR-6.3).
6. Revoke routes by test run ID (PRD §7.5).
7. Audit log records all route lifecycle events (FR-11.1).
8. FastAPI route endpoints (POST, GET, DELETE kill switch, sweep).
"""

import time
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.database import async_session_factory
from app.main import app
from app.models import AuditLog, Org, Route, User
from app.services.auth_service import create_access_token
from app.services.route_broker import route_broker_service

DUMMY_HASH = "$2b$12$dummyhashedpasswordvaluefortestingpurpose"


@pytest.mark.asyncio
async def test_open_route_creates_active_record_and_ingress() -> None:
    """Verify route creation sets active status, valid URL, and calculated TTL."""
    org_id = uuid.uuid4()
    user_id = uuid.uuid4()

    async with async_session_factory() as session:
        org = Org(id=org_id, name="Route Test Org", slug=f"org-{uuid.uuid4().hex[:8]}")
        user = User(
            id=user_id,
            email=f"route-{uuid.uuid4().hex[:8]}@example.com",
            hashed_password=DUMMY_HASH,
            full_name="Route Tester",
            org_id=org_id,
        )
        session.add(org)
        session.add(user)
        await session.commit()

        route = await route_broker_service.open_route(
            org_id=org_id,
            target_service="payment-service",
            target_port=8080,
            ttl_seconds=1800,
            user_id=user_id,
            user_email=user.email,
            db=session,
        )

    assert route["status"] == "active"
    assert route["target_service"] == "payment-service"
    assert route["target_port"] == 8080
    assert route["ttl_seconds"] == 1800
    assert route["ttl_remaining_seconds"] > 1750
    assert route["route_url"].startswith("http://route-")
    assert "payment-service:8080" not in route["route_url"]  # Ephemeral Ingress, not direct target credential
    assert route["ingress_name"].startswith("route-")


@pytest.mark.asyncio
async def test_kill_switch_revokes_route_under_5_seconds() -> None:
    """Verify kill switch executes synchronously in under 5 seconds (NFR-3.1)."""
    org_id = uuid.uuid4()

    async with async_session_factory() as session:
        org = Org(id=org_id, name="KillSwitch Org", slug=f"org-{uuid.uuid4().hex[:8]}")
        session.add(org)
        await session.commit()

        route = await route_broker_service.open_route(
            org_id=org_id,
            target_service="web-service",
            target_port=80,
            ttl_seconds=3600,
            db=session,
        )

        route_id = uuid.UUID(route["id"])
        start = time.monotonic()
        revoked = await route_broker_service.revoke_route(
            route_id=route_id,
            reason="manual_kill_switch",
            org_id=org_id,
            db=session,
        )
        elapsed = time.monotonic() - start

    assert elapsed < 5.0, f"Kill switch exceeded 5 seconds: {elapsed:.2f}s"
    assert revoked["status"] == "revoked"
    assert revoked["revocation_reason"] == "manual_kill_switch"
    assert revoked["revoked_at"] is not None
    assert revoked["kill_switch_latency_seconds"] < 5.0


@pytest.mark.asyncio
async def test_sweep_expired_routes() -> None:
    """Verify TTL sweep revokes routes whose expires_at is in the past (NFR-2.1)."""
    org_id = uuid.uuid4()

    async with async_session_factory() as session:
        org = Org(id=org_id, name="Sweep Org", slug=f"org-{uuid.uuid4().hex[:8]}")
        session.add(org)
        await session.commit()

        # Create active route
        route = await route_broker_service.open_route(
            org_id=org_id,
            target_service="auth-service",
            target_port=443,
            ttl_seconds=300,
            db=session,
        )
        route_id = uuid.UUID(route["id"])

        # Manually backdate expires_at in DB
        past_time = datetime.now(UTC) - timedelta(seconds=60)
        route_db = (await session.execute(select(Route).where(Route.id == route_id))).scalar_one()
        route_db.expires_at = past_time
        await session.commit()

        # Execute sweep
        swept = await route_broker_service.sweep_expired_routes(db=session)

    swept_ids = [s["id"] for s in swept]
    assert str(route_id) in swept_ids

    # Verify route status is expired
    async with async_session_factory() as session:
        refreshed = (await session.execute(select(Route).where(Route.id == route_id))).scalar_one()
        assert refreshed.status == "expired"
        assert refreshed.revocation_reason == "ttl_expired"


@pytest.mark.asyncio
async def test_reject_l3_l4_disallowed_ports() -> None:
    """Verify non-application ports (SSH, SMB, etc.) are permanently disallowed (FR-5.5)."""
    org_id = uuid.uuid4()

    for disallowed_port in (22, 23, 445, 3389):
        with pytest.raises(ValueError, match="application-layer"):
            await route_broker_service.open_route(
                org_id=org_id,
                target_service="db-service",
                target_port=disallowed_port,
            )


@pytest.mark.asyncio
async def test_reject_out_of_scope_target() -> None:
    """Verify target outside customer tenant scope is blocked before opening route (FR-6.3)."""
    org_id = uuid.uuid4()

    # Cloud metadata
    with pytest.raises(ValueError, match="permitted tenant scope"):
        await route_broker_service.open_route(
            org_id=org_id,
            target_service="169.254.169.254",
            target_port=80,
        )

    # Public domain
    with pytest.raises(ValueError, match="permitted tenant scope"):
        await route_broker_service.open_route(
            org_id=org_id,
            target_service="target.external-domain.com",
            target_port=443,
        )


@pytest.mark.asyncio
async def test_revoke_route_by_test_run_id() -> None:
    """Verify all routes tied to a test_run_id are revoked together (PRD §7.5)."""
    org_id = uuid.uuid4()
    test_run_id = uuid.uuid4()

    async with async_session_factory() as session:
        org = Org(id=org_id, name="TestRun Org", slug=f"org-{uuid.uuid4().hex[:8]}")
        session.add(org)
        await session.commit()

        # Open two routes for same test run
        r1 = await route_broker_service.open_route(
            org_id=org_id,
            target_service="service-a",
            target_port=8001,
            test_run_id=test_run_id,
            db=session,
        )
        r2 = await route_broker_service.open_route(
            org_id=org_id,
            target_service="service-b",
            target_port=8002,
            test_run_id=test_run_id,
            db=session,
        )

        revoked_list = await route_broker_service.revoke_route_by_test_run(
            test_run_id=test_run_id,
            reason="test_run_stop",
            org_id=org_id,
            db=session,
        )

    assert len(revoked_list) == 2
    assert {r["id"] for r in revoked_list} == {r1["id"], r2["id"]}
    assert all(r["status"] == "revoked" for r in revoked_list)


@pytest.mark.asyncio
async def test_route_audit_log_entries() -> None:
    """Verify route creation and revocation record append-only audit entries (FR-11.1)."""
    org_id = uuid.uuid4()

    async with async_session_factory() as session:
        org = Org(id=org_id, name="Audit Org", slug=f"org-{uuid.uuid4().hex[:8]}")
        session.add(org)
        await session.commit()

        route = await route_broker_service.open_route(
            org_id=org_id,
            target_service="audit-svc",
            target_port=8080,
            db=session,
        )
        route_id = uuid.UUID(route["id"])

        await route_broker_service.revoke_route(
            route_id=route_id,
            reason="audit_test",
            org_id=org_id,
            db=session,
        )

        # Query audit log
        res = await session.execute(
            select(AuditLog).where(
                AuditLog.org_id == org_id,
                AuditLog.resource_id == str(route_id),
            )
        )
        logs = res.scalars().all()

    actions = [entry.action for entry in logs]
    assert "route.opened" in actions
    assert "route.revoked" in actions


@pytest.mark.asyncio
async def test_route_fastapi_endpoints() -> None:
    """Verify Route Broker REST API endpoints (open, list, kill switch, sweep)."""
    org_id = uuid.uuid4()
    user_id = uuid.uuid4()
    email = f"api-route-{uuid.uuid4().hex[:8]}@example.com"

    async with async_session_factory() as session:
        org = Org(id=org_id, name="API Test Org", slug=f"org-{uuid.uuid4().hex[:8]}")
        user = User(
            id=user_id,
            email=email,
            hashed_password=DUMMY_HASH,
            full_name="API Tester",
            org_id=org_id,
        )
        session.add(org)
        session.add(user)
        await session.commit()

    token = create_access_token(user_id=user_id, email=email, org_id=org_id, role="tester")
    headers = {"Authorization": f"Bearer {token}"}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Open Route
        open_res = await client.post(
            "/api/routes",
            headers=headers,
            json={
                "target_service": "frontend-service",
                "target_port": 3000,
                "ttl_seconds": 1200,
            },
        )
        assert open_res.status_code == 201
        data = open_res.json()
        route_id = data["id"]
        assert data["status"] == "active"
        assert data["target_service"] == "frontend-service"

        # 2. List Routes
        list_res = await client.get("/api/routes?status=active", headers=headers)
        assert list_res.status_code == 200
        routes = list_res.json()
        assert any(r["id"] == route_id for r in routes)

        # 3. Get Route Detail
        get_res = await client.get(f"/api/routes/{route_id}", headers=headers)
        assert get_res.status_code == 200
        assert get_res.json()["id"] == route_id

        # 4. Emergency Kill Switch
        del_res = await client.delete(
            f"/api/routes/{route_id}?reason=emergency_kill_switch_test",
            headers=headers,
        )
        assert del_res.status_code == 200
        revoked_data = del_res.json()
        assert revoked_data["status"] == "revoked"
        assert revoked_data["revocation_reason"] == "emergency_kill_switch_test"
        assert revoked_data["kill_switch_latency_seconds"] < 5.0

        # 5. Sweep Endpoint
        sweep_res = await client.post("/api/routes/sweep", headers=headers)
        assert sweep_res.status_code == 200
        assert isinstance(sweep_res.json(), list)
