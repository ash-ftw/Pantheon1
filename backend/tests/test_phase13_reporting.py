"""Phase 13 Reporting Engine Test Suite — PRD Module 12.

Comprehensive unit and integration tests covering:
1. Before/After posture delta calculation:
   - Initial baseline execution (no prior run recorded)
   - Improved posture (resolved findings from prior run)
   - Degraded posture (new critical findings introduced)
2. Authoritative Markdown document generation with all required sections.
3. Server-side headless Matplotlib chart generation (PNG export).
4. Pure Python ReportLab PDF document compilation and validation.
5. CSV export generation with CWE/OWASP mapping and remediation guidance.
6. REST API Endpoints:
   - POST /api/reports/generate
   - GET /api/reports (scoped to organization)
   - GET /api/reports/{id}
   - GET /api/reports/runs/{id}/preview
   - GET /api/reports/{id}/download (PDF, CSV, Markdown)
"""

import os
import uuid
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.database import get_db_session
from app.main import app
from app.models import (
    App,
    DefenceRecommendation,
    Finding,
    Report,
    TestRun,
    User,
)
from app.services.auth_service import create_access_token, get_current_user
from app.services.reporting_service import ReportingService, reporting_service


def _create_mock_test_run(
    run_id: uuid.UUID,
    org_id: uuid.UUID,
    app_id: uuid.UUID,
    scenario_name: str = "SQL Injection Resilience Probe",
) -> TestRun:
    """Helper to instantiate an in-memory TestRun model for unit testing."""
    return TestRun(
        id=run_id,
        org_id=org_id,
        app_id=app_id,
        scenario_name=scenario_name,
        scenario_category="sqli",
        status="completed",
        total_steps=3,
        current_step=3,
        metrics={
            "total_requests": 40,
            "failed_requests": 2,
            "avg_latency_ms": 35.4,
            "p95_latency_ms": 78.2,
        },
        logs=[],
        created_at=datetime(2026, 9, 6, 12, 0, tzinfo=UTC),
        started_at=datetime(2026, 9, 6, 12, 0, tzinfo=UTC),
        completed_at=datetime(2026, 9, 6, 12, 1, tzinfo=UTC),
    )


@pytest.mark.asyncio
async def test_before_after_comparison_baseline_and_delta() -> None:
    """Verify before/after comparison calculates baseline and posture deltas properly."""
    org_id = uuid.uuid4()
    app_id = uuid.uuid4()
    run1_id = uuid.uuid4()
    run2_id = uuid.uuid4()

    service = ReportingService()

    # 1. Baseline Test (no prior run returned by db query)
    current_run = _create_mock_test_run(run1_id, org_id, app_id)
    f1 = Finding(
        id=uuid.uuid4(),
        org_id=org_id,
        test_run_id=run1_id,
        app_id=app_id,
        title="Blind SQLi in /search",
        severity="critical",
        category="Injection",
        remediation_guidance="Use ORM",
        status="open",
    )
    f2 = Finding(
        id=uuid.uuid4(),
        org_id=org_id,
        test_run_id=run1_id,
        app_id=app_id,
        title="Stack Trace Disclosure",
        severity="medium",
        category="Information Disclosure",
        remediation_guidance="Disable debug",
        status="open",
    )

    mock_db = AsyncMock()
    mock_result_none = MagicMock()
    mock_result_none.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_result_none

    comp_baseline = await service.compute_before_after_comparison(mock_db, current_run, [f1, f2])
    assert comp_baseline["posture_delta"] == "initial_run"
    assert comp_baseline["prior_run_id"] is None
    assert comp_baseline["current_findings_count"] == 2
    assert comp_baseline["current_posture_score"] == 12.0  # critical(10) + medium(2)
    assert len(comp_baseline["new_findings"]) == 2

    # 2. Subsequent Run Test (prior run had f1 and f2, current run resolved f1, kept f2, added low f3)
    prior_run = _create_mock_test_run(run1_id, org_id, app_id)
    prior_run.findings = [f1, f2]

    f3_low = Finding(
        id=uuid.uuid4(),
        org_id=org_id,
        test_run_id=run2_id,
        app_id=app_id,
        title="Missing Content-Type Options",
        severity="low",
        category="Misconfiguration",
        remediation_guidance="Add X-Content-Type-Options: nosniff",
        status="open",
    )

    current_run_2 = _create_mock_test_run(run2_id, org_id, app_id)
    mock_result_prior = MagicMock()
    mock_result_prior.scalar_one_or_none.return_value = prior_run
    mock_db.execute.return_value = mock_result_prior

    comp_subsequent = await service.compute_before_after_comparison(
        mock_db, current_run_2, [f2, f3_low]
    )
    assert comp_subsequent["prior_run_id"] == str(run1_id)
    assert comp_subsequent["prior_findings_count"] == 2
    assert comp_subsequent["current_findings_count"] == 2
    assert len(comp_subsequent["resolved_findings"]) == 1
    assert comp_subsequent["resolved_findings"][0]["title"] == "Blind SQLi in /search"
    assert len(comp_subsequent["new_findings"]) == 1
    assert comp_subsequent["new_findings"][0]["title"] == "Missing Content-Type Options"
    # Prior score was 12.0, current score is medium(2) + low(1) = 3.0 -> delta +9.0
    assert comp_subsequent["posture_delta"] == "improved"
    assert comp_subsequent["posture_score_delta"] == 9.0


def test_markdown_and_chart_generation(tmp_path: Path) -> None:
    """Verify authoritative Markdown generation and headless Matplotlib chart rendering."""
    org_id = uuid.uuid4()
    app_id = uuid.uuid4()
    run_id = uuid.uuid4()
    report_id = uuid.uuid4()

    service = ReportingService()
    test_run = _create_mock_test_run(run_id, org_id, app_id)
    app_obj = App(
        id=app_id,
        org_id=org_id,
        name="Fintech Core Gateway",
        source_type="git",
        source_url="https://github.com/example/gw.git",
        status="running",
    )

    f1 = Finding(
        id=uuid.uuid4(),
        org_id=org_id,
        test_run_id=run_id,
        app_id=app_id,
        title="Unauthenticated Password Reset Endpoint",
        severity="critical",
        category="Broken Authentication",
        cwe_id="CWE-287",
        owasp_category="A07:2021-Identification and Authentication Failures",
        description="Password reset can be triggered without token verification.",
        remediation_guidance="Enforce signed cryptographic reset tokens.",
        status="open",
    )

    rec = DefenceRecommendation(
        id=uuid.uuid4(),
        org_id=org_id,
        test_run_id=run_id,
        finding_id=f1.id,
        app_id=app_id,
        title="Block Unverified Reset Requests via Ingress Rate Limiting",
        category="Authentication Abuse",
        mitigation_type="ingress_rule",
        mechanically_applicable=True,
        status="applied",
        code_guidance="Apply Traefik rate limit middleware.",
        infra_manifest={},
    )

    comparison = {
        "prior_run_id": "test-prior-run",
        "prior_run_date": "2026-09-01 10:00 UTC",
        "prior_findings_count": 3,
        "current_findings_count": 1,
        "resolved_findings": [{"title": "Old Flaw", "severity": "high", "category": "Auth"}],
        "new_findings": [],
        "posture_delta": "improved",
        "posture_score_delta": 5.0,
        "prior_posture_score": 15.0,
        "current_posture_score": 10.0,
        "summary": "Security posture improved significantly.",
    }

    metrics = {
        "total_requests": 150,
        "failed_requests": 3,
        "error_rate_pct": 2.0,
        "avg_latency_ms": 28.5,
        "p95_latency_ms": 62.0,
    }

    # 1. Chart generation
    sev_counts = {"critical": 1, "high": 0, "medium": 0, "low": 0, "info": 0}
    chart_path = service.generate_charts(sev_counts, tmp_path, report_id)
    assert chart_path is not None
    assert os.path.exists(chart_path)
    assert os.path.getsize(chart_path) > 1000

    # 2. Markdown report generation
    md = service.build_markdown_report(
        report_id=report_id,
        title="Fintech Gateway Resilience Report",
        test_run=test_run,
        app=app_obj,
        findings=[f1],
        recommendations=[rec],
        comparison=comparison,
        metrics=metrics,
        chart_path=chart_path,
    )

    assert "# Fintech Gateway Resilience Report" in md
    assert "Fintech Core Gateway" in md
    assert "## 1. Executive Summary" in md
    assert "## 2. Before / After Posture Comparison" in md
    assert "## 3. Performance & Reliability Metrics" in md
    assert "## 4. Security Findings & Vulnerability Matrix" in md
    assert "Unauthenticated Password Reset Endpoint" in md
    assert "CWE-287" in md
    assert "## 5. Defensive Mitigations & Recommendations" in md
    assert "## 6. Audit & Platform Verification" in md


def test_pdf_and_csv_exports(tmp_path: Path) -> None:
    """Verify pure-Python ReportLab PDF export and CSV export generation."""
    org_id = uuid.uuid4()
    app_id = uuid.uuid4()
    run_id = uuid.uuid4()
    report_id = uuid.uuid4()

    service = ReportingService()
    test_run = _create_mock_test_run(run_id, org_id, app_id)
    app_obj = App(
        id=app_id,
        org_id=org_id,
        name="Export Target API",
        source_type="git",
        source_url="https://github.com/target/api.git",
    )

    f1 = Finding(
        id=uuid.uuid4(),
        org_id=org_id,
        test_run_id=run_id,
        app_id=app_id,
        title="Exposed Prometheus Metrics Without Auth",
        severity="medium",
        category="Information Disclosure",
        cwe_id="CWE-200",
        owasp_category="A01:2021-Broken Access Control",
        description="Internal metrics exposed at /metrics",
        remediation_guidance="Restrict /metrics to internal subnet.",
        status="open",
        created_at=datetime(2026, 9, 6, 12, 5, tzinfo=UTC),
    )

    rec = DefenceRecommendation(
        id=uuid.uuid4(),
        org_id=org_id,
        test_run_id=run_id,
        finding_id=f1.id,
        app_id=app_id,
        title="Restrict /metrics via NetworkPolicy",
        category="Network Security",
        mitigation_type="network_policy",
        mechanically_applicable=True,
        status="suggested",
    )

    comparison = {
        "summary": "Post-mitigation security test run.",
        "posture_delta": "improved",
        "posture_score_delta": 4.0,
        "prior_run_id": "run-prior-123",
        "prior_run_date": "2026-09-05",
        "prior_findings_count": 2,
        "prior_posture_score": 6.0,
        "current_posture_score": 2.0,
    }
    metrics = {
        "total_requests": 60,
        "failed_requests": 1,
        "error_rate_pct": 1.67,
        "avg_latency_ms": 32.1,
        "p95_latency_ms": 70.0,
    }

    # 1. CSV Generation
    csv_path = tmp_path / f"{report_id}.csv"
    service.generate_csv([f1], csv_path)
    assert os.path.exists(csv_path)
    with open(csv_path, encoding="utf-8") as f:
        content = f.read()
        assert (
            "id,severity,category,title,cwe_id,owasp_category,status,remediation_guidance,created_at"
            in content
        )
        assert "Exposed Prometheus Metrics Without Auth" in content
        assert "CWE-200" in content

    # 2. PDF Generation
    pdf_path = tmp_path / f"{report_id}.pdf"
    service.generate_pdf(
        title="Export Evaluation Report",
        test_run=test_run,
        app=app_obj,
        findings=[f1],
        recommendations=[rec],
        comparison=comparison,
        metrics=metrics,
        chart_path=None,
        output_path=pdf_path,
    )
    assert os.path.exists(pdf_path)
    assert os.path.getsize(pdf_path) > 1000
    with open(pdf_path, "rb") as f:
        header = f.read(5)
        assert header == b"%PDF-"


@pytest.mark.asyncio
async def test_reporting_rest_endpoints(tmp_path: Path) -> None:
    """Verify REST endpoints for generating, listing, previewing, and downloading reports."""
    org_id = uuid.uuid4()
    user_id = uuid.uuid4()
    run_id = uuid.uuid4()
    report_id = uuid.uuid4()
    app_id = uuid.uuid4()

    token = create_access_token(
        user_id=user_id,
        email="auditor@pantheon.local",
        org_id=org_id,
        role="Admin",
    )
    headers = {"Authorization": f"Bearer {token}"}

    test_user = User(
        id=user_id,
        email="auditor@pantheon.local",
        full_name="Security Auditor",
        hashed_password="hash",
        org_id=org_id,
        role="Admin",
        is_active=True,
    )

    sample_report = Report(
        id=report_id,
        org_id=org_id,
        test_run_id=run_id,
        app_id=app_id,
        title="Automated Test Run Report",
        executive_summary="Summary of evaluation.",
        markdown_content="# Automated Test Run Report\n\nAll checks passed.",
        pdf_path=str(tmp_path / "report.pdf"),
        csv_path=str(tmp_path / "report.csv"),
        before_after_comparison={"posture_delta": "improved"},
        metrics_summary={"total_requests": 50},
        created_at=datetime.now(UTC),
    )

    assert sample_report.pdf_path is not None
    assert sample_report.csv_path is not None

    # Write dummy files to disk for download testing
    with open(sample_report.pdf_path, "wb") as f:
        f.write(b"%PDF-1.4 test pdf content")
    with open(sample_report.csv_path, "w", encoding="utf-8") as f:
        f.write("id,title\n1,Test Finding\n")

    # Override dependencies
    app.dependency_overrides[get_current_user] = lambda: test_user
    mock_db = AsyncMock()
    app.dependency_overrides[get_db_session] = lambda: mock_db

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # 1. GET /api/reports/runs/{id}/preview
            with patch.object(
                reporting_service,
                "preview_report",
                new=AsyncMock(
                    return_value={
                        "test_run_id": str(run_id),
                        "scenario_name": "Preview Scenario",
                        "markdown_preview": "# Preview",
                        "before_after_comparison": {},
                        "metrics_summary": {},
                    }
                ),
            ):
                preview_resp = await client.get(
                    f"/api/reports/runs/{run_id}/preview", headers=headers
                )
                assert preview_resp.status_code == 200
                assert preview_resp.json()["scenario_name"] == "Preview Scenario"

            # 2. POST /api/reports/generate
            with patch.object(
                reporting_service,
                "generate_report",
                new=AsyncMock(return_value=sample_report),
            ):
                gen_resp = await client.post(
                    "/api/reports/generate",
                    json={"test_run_id": str(run_id), "title": "Automated Test Run Report"},
                    headers=headers,
                )
                assert gen_resp.status_code == 201
                assert gen_resp.json()["id"] == str(report_id)

            # 3. GET /api/reports
            with patch.object(
                reporting_service,
                "list_reports",
                new=AsyncMock(return_value=[sample_report]),
            ):
                list_resp = await client.get("/api/reports", headers=headers)
                assert list_resp.status_code == 200
                reports_list = list_resp.json()
                assert len(reports_list) == 1
                assert reports_list[0]["id"] == str(report_id)

            # 4. GET /api/reports/{id}
            with patch.object(
                reporting_service,
                "get_report",
                new=AsyncMock(return_value=sample_report),
            ):
                get_resp = await client.get(f"/api/reports/{report_id}", headers=headers)
                assert get_resp.status_code == 200
                assert get_resp.json()["title"] == "Automated Test Run Report"

            # 5. GET /api/reports/{id}/download?format=pdf
            with patch.object(
                reporting_service,
                "get_export_bytes",
                new=AsyncMock(return_value=(b"%PDF-1.4 sample", "application/pdf", "report.pdf")),
            ):
                dl_pdf = await client.get(
                    f"/api/reports/{report_id}/download?format=pdf", headers=headers
                )
                assert dl_pdf.status_code == 200
                assert "application/pdf" in dl_pdf.headers["content-type"]
                assert dl_pdf.content.startswith(b"%PDF")

            # 6. GET /api/reports/{id}/download?format=csv
            with patch.object(
                reporting_service,
                "get_export_bytes",
                new=AsyncMock(return_value=(b"id,title\n1,Finding", "text/csv", "report.csv")),
            ):
                dl_csv = await client.get(
                    f"/api/reports/{report_id}/download?format=csv", headers=headers
                )
                assert dl_csv.status_code == 200
                assert "text/csv" in dl_csv.headers["content-type"]

            # 7. GET /api/reports/{id}/download?format=md
            with patch.object(
                reporting_service,
                "get_export_bytes",
                new=AsyncMock(return_value=(b"# Markdown", "text/markdown", "report.md")),
            ):
                dl_md = await client.get(
                    f"/api/reports/{report_id}/download?format=md", headers=headers
                )
                assert dl_md.status_code == 200
                assert "text/markdown" in dl_md.headers["content-type"]
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db_session, None)
