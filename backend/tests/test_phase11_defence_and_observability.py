"""Phase 11 Defence Engine & Observability Test Suite — PRD Modules 10, 11, 13, 14.

Tests:
1. DefenceRecommendation model persistence and deterministic rule catalog mapping.
2. 1-Click Infrastructure Mitigation application lifecycle (NetworkPolicy/Middleware deployment, finding state transition to 'mitigated', audit logging).
3. Mitigation rollback / revert lifecycle.
4. Defence REST API endpoints: GET /api/defence/recommendations, POST /api/defence/recommendations/{id}/apply, POST /api/defence/recommendations/{id}/revert.
5. Observability telemetry calculation: GET /api/observability/metrics/runs/{id} (probe latencies, status codes, resource utilization).
6. Observability event timeline: GET /api/observability/events/runs/{id}.
7. Platform metrics & Prometheus exposition endpoint: GET /api/observability/platform and GET /metrics.
"""

import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.database import async_session_factory
from app.main import app
from app.models import (
    App,
    Finding,
    Org,
    TestRun,
    User,
)
from app.services.auth_service import create_access_token
from app.services.defence_engine import defence_engine_service

DUMMY_HASH = "$2b$12$dummyhashedpasswordvaluefortestingpurpose"


@pytest.mark.asyncio
async def test_defence_models_and_catalog_generation() -> None:
    """Verify deterministic mitigation recommendation generation from a security finding."""
    org_id = uuid.uuid4()
    app_id = uuid.uuid4()
    run_id = uuid.uuid4()
    finding_id = uuid.uuid4()

    async with async_session_factory() as session:
        org = Org(id=org_id, name="Defence Org", slug=f"org-{uuid.uuid4().hex[:8]}")
        session.add(org)
        await session.commit()

        app_obj = App(
            id=app_id,
            org_id=org_id,
            name="Defence Target App",
            source_type="git",
            source_url="https://github.com/example/target.git",
            status="running",
            target_profile={"exposed_ports": [8085]},
        )
        session.add(app_obj)
        await session.commit()

        run = TestRun(
            id=run_id,
            org_id=org_id,
            app_id=app_id,
            scenario_name="SQL Injection Exploitation",
            scenario_category="sqli_resilience",
            status="completed",
            total_steps=3,
            current_step=3,
            metrics={},
            logs=[],
        )
        session.add(run)
        await session.commit()

        finding = Finding(
            id=finding_id,
            org_id=org_id,
            test_run_id=run_id,
            app_id=app_id,
            title="SQL Injection in /api/users Search Parameter",
            severity="critical",
            category="SQL Injection",
            cwe_id="CWE-89",
            owasp_category="A03:2021-Injection",
            description="Database query unsafely concatenates raw input.",
            evidence={"payload": "admin' OR 1=1--", "response_code": 200},
            remediation_guidance="Use parameterized queries.",
            status="open",
        )
        session.add(finding)
        await session.commit()

        # Generate recommendation
        rec = await defence_engine_service.generate_recommendation_for_finding(session, finding)
        await session.commit()

        assert rec.id is not None
        assert rec.finding_id == finding_id
        assert rec.status == "suggested"
        assert rec.mechanically_applicable is True
        assert rec.mitigation_type == "infrastructure"
        assert "NetworkPolicy" in str(rec.infra_manifest)
        assert "Parameterized SQL Queries" in rec.title
        assert rec.target_resource == "k8s:NetworkPolicy/isolate-database-access"


@pytest.mark.asyncio
async def test_defence_1click_apply_and_revert_lifecycle() -> None:
    """Verify 1-click infrastructure mitigation application and rollback with audit logging."""
    org_id = uuid.uuid4()
    app_id = uuid.uuid4()
    run_id = uuid.uuid4()
    finding_id = uuid.uuid4()

    async with async_session_factory() as session:
        org = Org(id=org_id, name="Lifecycle Org", slug=f"org-{uuid.uuid4().hex[:8]}")
        session.add(org)
        await session.commit()

        app_obj = App(
            id=app_id,
            org_id=org_id,
            name="Lifecycle App",
            source_type="git",
            source_url="https://github.com/example/app.git",
            status="running",
            target_profile={},
        )
        session.add(app_obj)
        await session.commit()

        run = TestRun(
            id=run_id,
            org_id=org_id,
            app_id=app_id,
            scenario_name="Auth Brute Force",
            scenario_category="brute_force",
            status="completed",
            total_steps=2,
            current_step=2,
            metrics={},
            logs=[],
        )
        session.add(run)
        await session.commit()

        finding = Finding(
            id=finding_id,
            org_id=org_id,
            test_run_id=run_id,
            app_id=app_id,
            title="Credential Guessing Weakness",
            severity="high",
            category="Authentication Abuse",
            description="No rate limit on login endpoint.",
            evidence={"attempts": 50},
            remediation_guidance="Enforce rate limiting.",
            status="open",
        )
        session.add(finding)
        await session.commit()

        rec = await defence_engine_service.generate_recommendation_for_finding(session, finding)
        await session.commit()

        # 1. Apply mitigation
        apply_res = await defence_engine_service.apply_mitigation(session, rec.id)
        assert apply_res.success is True
        assert apply_res.status == "applied"
        assert apply_res.applied_at is not None

        # Verify linked finding updated to mitigated
        f_after = await session.get(Finding, finding_id)
        assert f_after is not None
        assert f_after.status == "mitigated"

        # 2. Revert mitigation
        revert_res = await defence_engine_service.revert_mitigation(session, rec.id)
        assert revert_res.success is True
        assert revert_res.status == "reverted"
        assert revert_res.reverted_at is not None

        # Verify linked finding returned to open
        f_reverted = await session.get(Finding, finding_id)
        assert f_reverted is not None
        assert f_reverted.status == "open"


@pytest.mark.asyncio
async def test_defence_rest_endpoints() -> None:
    """Verify REST endpoints for recommendations and 1-click apply/revert actions."""
    org_id = uuid.uuid4()
    app_id = uuid.uuid4()
    run_id = uuid.uuid4()
    finding_id = uuid.uuid4()
    user_id = uuid.uuid4()

    async with async_session_factory() as session:
        org = Org(id=org_id, name="REST Org", slug=f"org-{uuid.uuid4().hex[:8]}")
        session.add(org)
        await session.commit()

        user = User(
            id=user_id,
            email=f"tester-{uuid.uuid4().hex[:6]}@example.com",
            hashed_password=DUMMY_HASH,
            full_name="Defence Tester",
            org_id=org_id,
            role="Admin",
            is_active=True,
        )
        session.add(user)
        await session.commit()

        app_obj = App(
            id=app_id,
            org_id=org_id,
            name="REST Target App",
            source_type="git",
            source_url="https://github.com/example/app.git",
            status="running",
            target_profile={},
        )
        session.add(app_obj)
        await session.commit()

        run = TestRun(
            id=run_id,
            org_id=org_id,
            app_id=app_id,
            scenario_name="SSRF Metadata Probe",
            scenario_category="ssrf",
            status="completed",
            total_steps=2,
            current_step=2,
            metrics={},
            logs=[],
        )
        session.add(run)
        await session.commit()

        finding = Finding(
            id=finding_id,
            org_id=org_id,
            test_run_id=run_id,
            app_id=app_id,
            title="SSRF to Cloud Metadata Service",
            severity="critical",
            category="SSRF",
            description="Outbound call to 169.254.169.254 succeeded.",
            evidence={"url": "http://169.254.169.254/latest/meta-data/"},
            remediation_guidance="Block outbound cloud metadata CIDRs.",
            status="open",
        )
        session.add(finding)
        await session.commit()

    token = create_access_token(user_id=user_id, email=user.email, org_id=org_id, role="Admin")
    headers = {"Authorization": f"Bearer {token}"}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. GET /api/defence/recommendations?test_run_id=...
        list_resp = await client.get(
            f"/api/defence/recommendations?test_run_id={run_id}", headers=headers
        )
        assert list_resp.status_code == 200
        recs = list_resp.json()
        assert len(recs) >= 1
        rec_id = recs[0]["id"]
        assert recs[0]["mechanically_applicable"] is True

        # 2. GET /api/defence/recommendations/{rec_id}
        get_resp = await client.get(f"/api/defence/recommendations/{rec_id}", headers=headers)
        assert get_resp.status_code == 200
        assert get_resp.json()["id"] == rec_id

        # 3. POST /api/defence/recommendations/{rec_id}/apply
        apply_resp = await client.post(
            f"/api/defence/recommendations/{rec_id}/apply", headers=headers
        )
        assert apply_resp.status_code == 200
        apply_data = apply_resp.json()
        assert apply_data["success"] is True
        assert apply_data["status"] == "applied"

        # 4. POST /api/defence/recommendations/{rec_id}/revert
        revert_resp = await client.post(
            f"/api/defence/recommendations/{rec_id}/revert", headers=headers
        )
        assert revert_resp.status_code == 200
        revert_data = revert_resp.json()
        assert revert_data["success"] is True
        assert revert_data["status"] == "reverted"


@pytest.mark.asyncio
async def test_observability_endpoints_and_prometheus() -> None:
    """Verify per-run telemetry analytics, event streams, and Prometheus /metrics."""
    org_id = uuid.uuid4()
    app_id = uuid.uuid4()
    run_id = uuid.uuid4()
    user_id = uuid.uuid4()

    async with async_session_factory() as session:
        org = Org(id=org_id, name="Obs Org", slug=f"org-{uuid.uuid4().hex[:8]}")
        session.add(org)
        await session.commit()

        user = User(
            id=user_id,
            email=f"obs-{uuid.uuid4().hex[:6]}@example.com",
            hashed_password=DUMMY_HASH,
            full_name="Obs Tester",
            org_id=org_id,
            role="Admin",
            is_active=True,
        )
        session.add(user)
        await session.commit()

        app_obj = App(
            id=app_id,
            org_id=org_id,
            name="Obs Target App",
            source_type="git",
            source_url="https://github.com/example/app.git",
            status="running",
            target_profile={},
        )
        session.add(app_obj)
        await session.commit()

        run = TestRun(
            id=run_id,
            org_id=org_id,
            app_id=app_id,
            scenario_name="Traffic Flood Resilience",
            scenario_category="traffic_flood",
            status="completed",
            total_steps=4,
            current_step=4,
            metrics={"peak_rps": 250},
            logs=[
                {
                    "step": 1,
                    "step_name": "Warmup Probe",
                    "status": "success",
                    "status_code": 200,
                    "latency_ms": 18.2,
                },
                {
                    "step": 2,
                    "step_name": "Baseline Burst",
                    "status": "success",
                    "status_code": 200,
                    "latency_ms": 28.5,
                },
                {
                    "step": 3,
                    "step_name": "Peak Load Test",
                    "status": "success",
                    "status_code": 200,
                    "latency_ms": 84.1,
                },
                {
                    "step": 4,
                    "step_name": "Saturated Overload",
                    "status": "compromised",
                    "status_code": 503,
                    "latency_ms": 142.6,
                },
            ],
        )
        session.add(run)
        await session.commit()

    token = create_access_token(user_id=user_id, email=user.email, org_id=org_id, role="Admin")
    headers = {"Authorization": f"Bearer {token}"}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Per-run metrics
        metrics_resp = await client.get(
            f"/api/observability/metrics/runs/{run_id}", headers=headers
        )
        assert metrics_resp.status_code == 200
        m_data = metrics_resp.json()
        assert m_data["test_run_id"] == str(run_id)
        assert m_data["avg_latency_ms"] > 0
        assert m_data["min_latency_ms"] > 0
        assert m_data["max_latency_ms"] >= m_data["min_latency_ms"]
        assert "200" in m_data["status_code_counts"]
        assert len(m_data["step_latencies"]) == 4

        # 2. Per-run event stream
        events_resp = await client.get(f"/api/observability/events/runs/{run_id}", headers=headers)
        assert events_resp.status_code == 200
        events = events_resp.json()
        assert len(events) >= 2
        components = {e["component"] for e in events}
        assert "runner" in components

        # 3. Platform metrics
        plat_resp = await client.get("/api/observability/platform", headers=headers)
        assert plat_resp.status_code == 200
        p_data = plat_resp.json()
        assert "cluster_health" in p_data
        assert p_data["cluster_health"] == "healthy"

        # 4. Prometheus metrics endpoint
        prom_resp = await client.get("/metrics")
        assert prom_resp.status_code == 200
        assert "pantheon_active_test_runs" in prom_resp.text
        assert "pantheon_total_findings" in prom_resp.text

        # 5. Grafana configuration endpoint
        grafana_resp = await client.get("/api/observability/grafana/config", headers=headers)
        assert grafana_resp.status_code == 200
        g_data = grafana_resp.json()
        assert "grafana_url" in g_data
        assert g_data["dashboard_uid"] == "pantheon-telemetry"
        assert g_data["status"] == "connected"

        # 6. Container real-time statistics endpoint
        container_resp = await client.get("/api/observability/container/stats", headers=headers)
        assert container_resp.status_code == 200
        c_data = container_resp.json()
        assert "cpu_utilization_pct" in c_data
        assert "memory_utilization_mb" in c_data
        assert "network_io_kbps" in c_data

        # 7. Loki log stream query endpoint
        loki_resp = await client.get(
            f"/api/observability/loki/logs?test_run_id={run_id}", headers=headers
        )
        assert loki_resp.status_code == 200
        assert isinstance(loki_resp.json(), list)
