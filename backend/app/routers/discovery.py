"""Discovery Router - PRD Modules 5-6 (Phase 5).

Endpoints:
- POST /api/discovery/target-analysis: Run/re-run target analysis on a deployed app
- POST /api/discovery/endpoints: Run/re-run endpoint discovery on a deployed app
- GET  /api/discovery/{app_id}/profile: Get persisted target profile
- GET  /api/discovery/{app_id}/endpoints: Get persisted endpoint discovery results
- GET  /api/discovery/{app_id}/summary: Get compact discovery summary for app list views
"""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db_session
from app.models import App, User
from app.schemas import (
    AppDiscoverySummary,
    DiscoveryEndpointsRequest,
    DiscoveryEndpointsResponse,
    DiscoveryTargetAnalysisRequest,
    DiscoveryTargetAnalysisResponse,
)
from app.services.auth_service import get_current_user
from app.services.discovery_service import discover_endpoints, run_target_analysis

router = APIRouter(prefix="/api/discovery", tags=["discovery"])


async def _get_org_app(
    app_id: str,
    current_user: User,
    db: AsyncSession,
) -> App:
    """Verify app belongs to current user's org and return it."""
    if not current_user.org_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User has no associated org"
        )
    import uuid as _uuid

    result = await db.execute(
        select(App).where(App.id == _uuid.UUID(app_id), App.org_id == current_user.org_id)
    )
    app = result.scalar_one_or_none()
    if not app:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="App not found in org")
    return app


# ---------------------------------------------------------------------------
# POST — Run/re-run analysis
# ---------------------------------------------------------------------------


@router.post(
    "/target-analysis",
    response_model=DiscoveryTargetAnalysisResponse,
    status_code=status.HTTP_200_OK,
)
async def api_target_analysis(
    request: Request,
    payload: DiscoveryTargetAnalysisRequest,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> DiscoveryTargetAnalysisResponse:
    """Run target analysis on a deployed app.

    Scopes all discovery to the org/tenant (org_id from auth).
    Persists results to the App record.
    """
    app = await _get_org_app(str(payload.app_id), current_user, db)

    # Run analysis
    app.discovery_status = "running"
    await db.commit()

    profile = await run_target_analysis(payload.app_id, current_user.org_id)  # type: ignore[arg-type]

    # Persist
    app.target_profile = profile
    app.discovery_status = profile.get("discovery_status", "completed")
    await db.commit()

    return DiscoveryTargetAnalysisResponse(**profile)


@router.post(
    "/endpoints",
    response_model=DiscoveryEndpointsResponse,
    status_code=status.HTTP_200_OK,
)
async def api_discover_endpoints(
    request: Request,
    payload: DiscoveryEndpointsRequest,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> DiscoveryEndpointsResponse:
    """Discover OpenAPI/Swagger endpoints for a deployed app.

    Scopes all discovery to the org/tenant (org_id from auth).
    Persists results to the App record.
    """
    app = await _get_org_app(str(payload.app_id), current_user, db)

    result = await discover_endpoints(payload.app_id, current_user.org_id)  # type: ignore[arg-type]

    # Persist
    app.discovered_endpoints = result
    await db.commit()

    return DiscoveryEndpointsResponse(**result)


# ---------------------------------------------------------------------------
# GET — Return persisted results (no re-run)
# ---------------------------------------------------------------------------


@router.get(
    "/{app_id}/profile",
    response_model=DiscoveryTargetAnalysisResponse,
)
async def get_target_profile(
    app_id: str,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> DiscoveryTargetAnalysisResponse:
    """Get persisted target analysis profile for an app."""
    app = await _get_org_app(app_id, current_user, db)

    if app.target_profile:
        return DiscoveryTargetAnalysisResponse(**app.target_profile)

    # No persisted profile — return empty with pending status
    from app.services.k8s_service import k8s_tenant_service

    namespace = k8s_tenant_service.get_namespace_name(app.org_id)
    return DiscoveryTargetAnalysisResponse(
        app_id=str(app.id),
        org_id=str(app.org_id),
        namespace=namespace,
        discovery_status=app.discovery_status,
    )


@router.get(
    "/{app_id}/endpoints",
    response_model=DiscoveryEndpointsResponse,
)
async def get_discovered_endpoints(
    app_id: str,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> DiscoveryEndpointsResponse:
    """Get persisted endpoint discovery results for an app."""
    app = await _get_org_app(app_id, current_user, db)

    if app.discovered_endpoints:
        return DiscoveryEndpointsResponse(**app.discovered_endpoints)

    from app.services.k8s_service import k8s_tenant_service

    namespace = k8s_tenant_service.get_namespace_name(app.org_id)
    return DiscoveryEndpointsResponse(
        app_id=str(app.id),
        org_id=str(app.org_id),
        namespace=namespace,
        discovery_status=app.discovery_status,
    )


@router.get(
    "/{app_id}/summary",
    response_model=AppDiscoverySummary,
)
async def get_discovery_summary(
    app_id: str,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> AppDiscoverySummary:
    """Get compact discovery summary for app list/detail views."""
    app = await _get_org_app(app_id, current_user, db)

    profile = app.target_profile or {}
    endpoints_data = app.discovered_endpoints or {}
    endpoints_list = endpoints_data.get("endpoints", [])
    classification = endpoints_data.get("classification", {})

    return AppDiscoverySummary(
        discovery_status=app.discovery_status,
        language=profile.get("language"),
        framework=profile.get("framework"),
        exposed_ports=profile.get("exposed_ports", []),
        detected_db=profile.get("detected_db"),
        endpoint_count=len(endpoints_list),
        classification_counts={k: len(v) for k, v in classification.items() if v},
    )
