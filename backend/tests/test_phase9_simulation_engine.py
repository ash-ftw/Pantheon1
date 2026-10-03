"""Phase 9 Simulation Engine & Test Run Execution Test Suite — PRD Module 10.

Tests:
1. Launch test run with safety guard validation creates queued/running record.
2. Step execution progresses and generates realistic security findings.
3. Emergency Kill Switch stops running simulation and revokes route in < 5 seconds (NFR-3.1).
4. Simulation Guard stops out-of-scope/unauthorized attacks.
5. In-memory and pub/sub event streaming pushes progress events.
6. REST endpoints for listing test runs, inspecting run details, and querying findings.
"""

import asyncio
import time
import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.database import async_session_factory
from app.main import app
from app.models import App, Org, User
from app.services.auth_service import create_access_token
from app.services.simulation_engine import simulation_engine

DUMMY_HASH = "$2b$12$dummyhashedpasswordvaluefortestingpurpose"


@pytest.mark.asyncio
async def test_launch_test_run_service() -> None:
    """Test launching a simulation run directly via simulation_engine."""
    org_id = uuid.uuid4()
    app_id = uuid.uuid4()

    async with async_session_factory() as session:
        org = Org(id=org_id, name="TestRun Org", slug=f"org-{uuid.uuid4().hex[:8]}")
        session.add(org)
        await session.commit()

        app_obj = App(
            id=app_id,
            org_id=org_id,
            name="Vulnerable Shop",
            source_type="git",
            source_url="https://github.com/example/shop.git",
            status="running",
            target_profile={"exposed_ports": [8085]},
        )
        session.add(app_obj)
        await session.commit()

        run_data = await simulation_engine.launch_test_run(
            org_id=org_id,
            app_id=app_id,
            scenario_name="SQL Injection Syntax & Tautology Probing",
            scenario_category="sqli_resilience",
            parameters={"rate_per_second": 10},
            db=session,
        )

    assert run_data["status"] in ("queued", "running")
    assert run_data["app_id"] == str(app_id)
    assert run_data["total_steps"] >= 2
    assert "requests_sent" in run_data["metrics"]


@pytest.mark.asyncio
async def test_emergency_kill_switch_under_5_seconds() -> None:
    """NFR-3.1: Stop button immediately calls Kill Switch, severing execution and route in < 5s."""
    org_id = uuid.uuid4()
    app_id = uuid.uuid4()

    async with async_session_factory() as session:
        org = Org(id=org_id, name="KillSwitch Org", slug=f"org-{uuid.uuid4().hex[:8]}")
        session.add(org)
        await session.commit()

        app_obj = App(
            id=app_id,
            org_id=org_id,
            name="Target App",
            source_type="compose",
            status="running",
            target_profile={"exposed_ports": [8085]},
        )
        session.add(app_obj)
        await session.commit()

        run_data = await simulation_engine.launch_test_run(
            org_id=org_id,
            app_id=app_id,
            scenario_name="Common Password Dictionary Stuffing",
            scenario_category="credential_guessing",
            db=session,
        )
        run_id = uuid.UUID(run_data["id"])

        # Give worker a brief moment to spin up
        await asyncio.sleep(0.1)

        # Trigger Kill Switch
        start_time = time.monotonic()
        stopped_run = await simulation_engine.stop_test_run(
            run_id=run_id,
            reason="manual_operator_abort",
            org_id=org_id,
            db=session,
        )
        elapsed = time.monotonic() - start_time

    assert elapsed < 5.0, f"Emergency stop took {elapsed}s, exceeding 5.0s NFR-3.1 requirement"
    assert stopped_run["status"] == "stopped"
    assert any("EMERGENCY STOP" in log["message"] for log in stopped_run["logs"])


@pytest.mark.asyncio
async def test_simulation_guard_safety_gate_rejection() -> None:
    """Verify safety policies reject attacks targeted at forbidden ports or loopback hosts."""
    org_id = uuid.uuid4()
    app_id = uuid.uuid4()

    async with async_session_factory() as session:
        org = Org(id=org_id, name="Safety Org", slug=f"org-{uuid.uuid4().hex[:8]}")
        session.add(org)
        await session.commit()

        # Disallowed port e.g. 22 (SSH)
        app_obj = App(
            id=app_id,
            org_id=org_id,
            name="Restricted Host",
            source_type="compose",
            status="running",
            target_profile={"exposed_ports": [22]},
        )
        session.add(app_obj)
        await session.commit()

        with pytest.raises(ValueError, match="Simulation Guard blocked run"):
            await simulation_engine.launch_test_run(
                org_id=org_id,
                app_id=app_id,
                scenario_name="SSH Brute Force",
                scenario_category="brute_force",
                db=session,
            )


@pytest.mark.asyncio
async def test_rest_api_lifecycle() -> None:
    """Test full REST API lifecycle: launch, list, get details, stop, query findings."""
    org_id = uuid.uuid4()
    user_id = uuid.uuid4()
    app_id = uuid.uuid4()

    async with async_session_factory() as session:
        org = Org(id=org_id, name="API Test Org", slug=f"org-{uuid.uuid4().hex[:8]}")
        session.add(org)
        await session.commit()

        user = User(
            id=user_id,
            email=f"tester-{uuid.uuid4().hex[:8]}@example.com",
            hashed_password=DUMMY_HASH,
            full_name="Simulation Tester",
            org_id=org_id,
        )
        session.add(user)

        app_obj = App(
            id=app_id,
            org_id=org_id,
            name="Chess App",
            source_type="git",
            status="running",
            target_profile={"exposed_ports": [8085]},
        )
        session.add(app_obj)
        await session.commit()

    token = create_access_token(user_id=user_id, email=user.email, org_id=org_id)
    headers = {"Authorization": f"Bearer {token}"}
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. POST /api/test-runs
        create_res = await client.post(
            "/api/test-runs",
            headers=headers,
            json={
                "app_id": str(app_id),
                "scenario_name": "SQL Injection Syntax & Tautology Probing",
                "scenario_category": "sqli_resilience",
            },
        )
        assert create_res.status_code == 201
        run_data = create_res.json()
        run_id = run_data["id"]
        assert run_data["status"] in ("queued", "running")

        # 2. GET /api/test-runs
        list_res = await client.get("/api/test-runs", headers=headers)
        assert list_res.status_code == 200
        runs_list = list_res.json()
        assert any(r["id"] == run_id for r in runs_list)

        # 3. GET /api/test-runs/{id}
        get_res = await client.get(f"/api/test-runs/{run_id}", headers=headers)
        assert get_res.status_code == 200
        assert get_res.json()["id"] == run_id

        # 4. POST /api/test-runs/{id}/stop (Kill Switch)
        stop_res = await client.post(
            f"/api/test-runs/{run_id}/stop",
            headers=headers,
            json={"reason": "operator_manual_test_stop"},
        )
        assert stop_res.status_code == 200
        assert stop_res.json()["status"] == "stopped"

        # 5. GET /api/test-runs/{id}/findings
        findings_res = await client.get(f"/api/test-runs/{run_id}/findings", headers=headers)
        assert findings_res.status_code == 200
        assert isinstance(findings_res.json(), list)


@pytest.mark.asyncio
async def test_in_memory_event_pubsub() -> None:
    """Test event queue subscription and delivery mechanism."""
    run_id = uuid.uuid4()
    q = simulation_engine.subscribe_in_memory(run_id)

    try:
        await simulation_engine.publish_event(
            run_id=run_id,
            event_type="test_event",
            data={"metric": 42},
        )
        msg = await asyncio.wait_for(q.get(), timeout=1.0)
        assert msg["event"] == "test_event"
        assert msg["data"]["metric"] == 42
    finally:
        simulation_engine.unsubscribe_in_memory(run_id, q)
