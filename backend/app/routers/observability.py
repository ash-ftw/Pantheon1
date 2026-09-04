"""Observability Router — PRD Module 13 / Module 10 (Phase 11).

REST and Prometheus endpoints for per-run telemetry (step latencies, status code breakdown,
container resource utilization), event stream, and platform health metrics.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db_session
from app.schemas import ObservabilityEventRead, PlatformMetricsRead, RunMetricsRead
from app.services.observability_service import observability_service

router = APIRouter(tags=["observability"])


@router.get("/api/observability/metrics/runs/{test_run_id}", response_model=RunMetricsRead)
async def get_run_metrics(
    test_run_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
) -> RunMetricsRead:
    """Fetch aggregated latency distributions, status codes, and resource metrics for a test run."""
    metrics = await observability_service.get_run_metrics(db, test_run_id)
    if not metrics:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Test run {test_run_id} not found",
        )
    return metrics


@router.get("/api/observability/events/runs/{test_run_id}", response_model=list[ObservabilityEventRead])
async def get_run_events(
    test_run_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
) -> list[ObservabilityEventRead]:
    """Fetch timeline of container, route, probe, and security events for a test run."""
    return await observability_service.get_run_events(db, test_run_id)


@router.get("/api/observability/platform", response_model=PlatformMetricsRead)
async def get_platform_metrics(
    db: AsyncSession = Depends(get_db_session),
) -> PlatformMetricsRead:
    """Fetch platform-wide health, active test runs, open routes, and mitigation coverage metrics."""
    return await observability_service.get_platform_metrics(db)


@router.get("/api/observability/loki/logs")
async def get_loki_logs(
    test_run_id: uuid.UUID | None = Query(default=None, description="Optional filter by test run ID"),
    limit: int = Query(default=50, ge=1, le=200, description="Max log lines to return"),
) -> list[dict]:
    """Query live log stream from Grafana Loki HTTP API (PRD FR-8.2)."""
    return await observability_service.query_loki_logs(test_run_id=test_run_id, limit=limit)


@router.get("/api/observability/grafana/config")
async def get_grafana_config() -> dict:
    """Fetch Grafana deep-link URLs, dashboard UID, and data source endpoints."""
    return observability_service.get_grafana_info()


@router.get("/api/observability/container/stats")
async def get_container_stats(
    app_name: str | None = Query(default=None, description="Optional container/app filter name"),
) -> dict:
    """Fetch live Docker container CPU, Memory, and Network I/O metrics."""
    return observability_service.get_container_stats(app_name=app_name)


@router.get("/metrics", response_class=Response)
async def get_prometheus_metrics(
    db: AsyncSession = Depends(get_db_session),
) -> Response:

    """Expose Prometheus exposition format metrics for scraping (PRD FR-8.1)."""
    p_metrics = await observability_service.get_platform_metrics(db)

    # Format standard Prometheus plaintext
    lines = [
        "# HELP pantheon_active_test_runs Number of currently running attack simulations",
        "# TYPE pantheon_active_test_runs gauge",
        f"pantheon_active_test_runs {p_metrics.active_test_runs}",
        "",
        "# HELP pantheon_completed_test_runs Number of completed/stopped attack simulations",
        "# TYPE pantheon_completed_test_runs counter",
        f"pantheon_completed_test_runs {p_metrics.completed_test_runs}",
        "",
        "# HELP pantheon_open_routes Number of currently active route broker proxy routes",
        "# TYPE pantheon_open_routes gauge",
        f"pantheon_open_routes {p_metrics.open_routes}",
        "",
        "# HELP pantheon_total_findings Total security findings discovered",
        "# TYPE pantheon_total_findings counter",
        f"pantheon_total_findings {p_metrics.total_findings}",
        "",
        "# HELP pantheon_applied_mitigations Total infrastructure mitigations applied",
        "# TYPE pantheon_applied_mitigations counter",
        f"pantheon_applied_mitigations {p_metrics.applied_mitigations}",
        "",
        "# HELP pantheon_mitigation_rate_percent Percentage of recommendations with applied mitigations",
        "# TYPE pantheon_mitigation_rate_percent gauge",
        f"pantheon_mitigation_rate_percent {p_metrics.mitigation_rate_pct}",
        "",
    ]
    content = "\n".join(lines)
    return Response(content=content, media_type="text/plain; version=0.0.4; charset=utf-8")
