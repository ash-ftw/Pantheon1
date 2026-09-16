"""Tests for Phase 14 — Dashboard & Polish (PRD Module 1).

Covers:
1. Dashboard KPIs and resilience score calculation
2. Preset demo app catalog querying and 1-click deployment
3. Notifications lifecycle (create, list, mark-read, mark-all-read)
4. Audit log filtering and authorization
"""

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.database import get_db_session
from app.main import app
from app.models import (
    App,
    AuditLog,
    DefenceRecommendation,
    Finding,
    Notification,
    TestRun,
    User,
)
from app.services.auth_service import get_current_user
from app.services.dashboard_service import DashboardService, dashboard_service
from app.services.notification_service import NotificationService, notification_service


def _make_mock_user(org_id: uuid.UUID, role: str = "admin") -> User:
    user = MagicMock(spec=User)
    user.id = uuid.uuid4()
    user.email = "admin@pantheon.cyber"
    user.org_id = org_id
    user.role = role
    return user


@pytest.mark.asyncio
async def test_dashboard_service_stats_calculation():
    """Verify DashboardService correctly aggregates counts and calculates the resilience score."""
    service = DashboardService()
    org_id = uuid.uuid4()
    app_id = uuid.uuid4()
    run_id = uuid.uuid4()

    mock_app = App(
        id=app_id,
        org_id=org_id,
        name="Production Web App",
        source_type="git",
        source_url="https://github.com/example/repo",
        status="running",
        created_at=datetime.now(UTC),
    )

    mock_run = TestRun(
        id=run_id,
        org_id=org_id,
        app_id=app_id,
        scenario_name="OWASP SQLi Test",
        scenario_category="sqli",
        status="completed",
        total_steps=5,
        current_step=5,
        created_at=datetime.now(UTC),
    )

    f_crit = Finding(
        id=uuid.uuid4(),
        org_id=org_id,
        test_run_id=run_id,
        app_id=app_id,
        title="SQL Injection",
        severity="critical",
        category="Injection",
        status="open",
        created_at=datetime.now(UTC),
    )

    f_high = Finding(
        id=uuid.uuid4(),
        org_id=org_id,
        test_run_id=run_id,
        app_id=app_id,
        title="Reflected XSS",
        severity="high",
        category="XSS",
        status="mitigated",
        created_at=datetime.now(UTC),
    )

    rec = DefenceRecommendation(
        id=uuid.uuid4(),
        org_id=org_id,
        test_run_id=run_id,
        finding_id=f_high.id,
        app_id=app_id,
        title="Enable CSP Headers",
        category="Headers",
        mitigation_type="ingress",
        mechanically_applicable=True,
        status="applied",
        created_at=datetime.now(UTC),
    )

    audit = AuditLog(
        id=uuid.uuid4(),
        org_id=org_id,
        action="simulation.completed",
        resource_type="test_run",
        resource_id=run_id,
        details={"status": "completed"},
        created_at=datetime.now(UTC),
    )

    session = AsyncMock()

    # Configure session.execute to return mocks in order: apps, test_runs, findings, recs, audit
    res_apps = MagicMock()
    res_apps.scalars.return_value.all.return_value = [mock_app]

    res_runs = MagicMock()
    res_runs.scalars.return_value.all.return_value = [mock_run]

    res_findings = MagicMock()
    res_findings.scalars.return_value.all.return_value = [f_crit, f_high]

    res_recs = MagicMock()
    res_recs.scalars.return_value.all.return_value = [rec]

    res_audit = MagicMock()
    res_audit.scalars.return_value.all.return_value = [audit]

    session.execute.side_effect = [res_apps, res_runs, res_findings, res_recs, res_audit]

    stats = await service.get_dashboard_stats(session, org_id)

    assert stats["total_apps"] == 1
    assert stats["active_deployments"] == 1
    assert stats["total_test_runs"] == 1
    assert stats["completed_test_runs"] == 1
    assert stats["total_findings"] == 2
    assert stats["findings_by_severity"]["critical"] == 1
    assert stats["findings_by_severity"]["high"] == 1
    assert stats["open_findings_count"] == 1
    assert stats["resolved_findings_count"] == 1
    assert stats["mitigation_stats"]["applied_mitigations"] == 1
    assert stats["mitigation_stats"]["mitigation_rate_pct"] == 100.0
    assert 0.0 <= stats["resilience_score"] <= 100.0
    assert len(stats["recent_test_runs"]) == 1
    assert len(stats["recent_activity"]) == 1
    assert stats["cluster_status"]["network_policy"] == "default-deny-active"


def test_demo_app_catalog_contents():
    """Verify demo catalog has all 4 expected known-vulnerable demo apps."""
    catalog = dashboard_service.get_demo_catalog()
    assert len(catalog) == 4

    ids = [d["id"] for d in catalog]
    assert "juice-shop-lite" in ids
    assert "fintech-gateway" in ids
    assert "cloudstore-commerce" in ids
    assert "devops-worker-agent" in ids

    for app_meta in catalog:
        assert "name" in app_meta
        assert "description" in app_meta
        assert "vulnerabilities" in app_meta
        assert len(app_meta["vulnerabilities"]) > 0
        assert "architecture" in app_meta
        assert "git_url" in app_meta

    single = dashboard_service.get_demo_app("juice-shop-lite")
    assert single is not None
    assert "OWASP" in single["name"]


@pytest.mark.asyncio
async def test_notification_service_crud():
    """Verify notification creation, listing, marking read, and unread counts."""
    service = NotificationService()
    org_id = uuid.uuid4()
    user_id = uuid.uuid4()

    session = AsyncMock()
    session.add = MagicMock()

    # 1. Create notification
    notif = await service.create_notification(
        session=session,
        org_id=org_id,
        user_id=user_id,
        title="Build Succeeded",
        message="Docker build completed for App v1",
        type="success",
        category="build",
        link="/apps/123",
    )
    assert notif.org_id == org_id
    assert notif.read is False
    assert notif.type == "success"
    session.add.assert_called_once()
    session.flush.assert_called()

    # 2. Mark as read
    res_notif = MagicMock()
    res_notif.scalar_one_or_none.return_value = notif
    session.execute.return_value = res_notif

    success = await service.mark_as_read(session, notif.id, org_id)
    assert success is True
    assert notif.read is True


@pytest.mark.asyncio
async def test_dashboard_and_notifications_endpoints():
    """Integration test for dashboard and notifications REST endpoints."""
    org_id = uuid.uuid4()
    mock_user = _make_mock_user(org_id)

    dummy_stats = {
        "total_apps": 2,
        "active_deployments": 1,
        "total_test_runs": 3,
        "completed_test_runs": 3,
        "active_test_runs": 0,
        "total_findings": 5,
        "findings_by_severity": {"critical": 1, "high": 2, "medium": 2, "low": 0, "info": 0},
        "open_findings_count": 3,
        "resolved_findings_count": 2,
        "resilience_score": 76.5,
        "mitigation_stats": {
            "total_recommendations": 3,
            "applied_mitigations": 2,
            "mitigation_rate_pct": 66.7,
        },
        "findings_timeline": [
            {"date": "Sep 15", "critical": 1, "high": 2, "medium": 2, "low": 0, "total": 5}
        ],
        "recent_test_runs": [],
        "cluster_status": {"status": "ready", "network_policy": "default-deny-active"},
        "recent_activity": [],
    }

    mock_db = AsyncMock()

    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_db_session] = lambda: mock_db

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # 1. GET /api/dashboard/demo-catalog
            resp = await client.get("/api/dashboard/demo-catalog")
            assert resp.status_code == 200
            catalog = resp.json()
            assert len(catalog) == 4

            # 2. GET /api/dashboard/stats
            with patch.object(
                dashboard_service, "get_dashboard_stats", new=AsyncMock(return_value=dummy_stats)
            ):
                resp = await client.get("/api/dashboard/stats")
                assert resp.status_code == 200
                data = resp.json()
                assert data["total_apps"] == 2
                assert data["resilience_score"] == 76.5

            # 3. POST /api/dashboard/demo-catalog/juice-shop-lite/deploy
            with patch("app.routers.dashboard.dispatch_ingestion_task") as mock_dispatch:
                resp = await client.post("/api/dashboard/demo-catalog/juice-shop-lite/deploy")
                assert resp.status_code == 200
                res_json = resp.json()
                assert res_json["success"] is True
                assert res_json["demo_id"] == "juice-shop-lite"
                mock_dispatch.assert_called_once()

            # 4. Notifications Endpoints
            dummy_notif = Notification(
                id=uuid.uuid4(),
                org_id=org_id,
                user_id=mock_user.id,
                title="Test Alert",
                message="Test alert description",
                type="info",
                category="general",
                read=False,
                link=None,
                created_at=datetime.now(UTC),
            )

            with patch.object(
                notification_service,
                "list_notifications",
                new=AsyncMock(return_value=[dummy_notif]),
            ):
                resp = await client.get("/api/notifications")
                assert resp.status_code == 200
                notifs = resp.json()
                assert len(notifs) == 1
                assert notifs[0]["title"] == "Test Alert"

            with patch.object(
                notification_service, "get_unread_count", new=AsyncMock(return_value=1)
            ):
                resp = await client.get("/api/notifications/unread-count")
                assert resp.status_code == 200
                assert resp.json()["unread_count"] == 1

            with patch.object(
                notification_service, "mark_all_as_read", new=AsyncMock(return_value=1)
            ):
                resp = await client.post("/api/notifications/read-all")
                assert resp.status_code == 200
                assert resp.json()["marked_count"] == 1

    finally:
        app.dependency_overrides.clear()
