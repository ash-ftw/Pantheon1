from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db_session
from app.models import App, User
from app.schemas import (
    DiscoveryEndpointsRequest,
    DiscoveryEndpointsResponse,
    DiscoveryTargetAnalysisRequest,
    DiscoveryTargetAnalysisResponse,
)
from app.services.auth_service import get_current_user
from app.services.discovery_service import discover_endpoints, run_target_analysis

router = APIRouter(prefix="/api/discovery", tags=["discovery"])


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
    """
    if not current_user.org_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User has no associated org"
        )

    # Verify app belongs to org
    result = await db.execute(
        select(App).where(App.id == payload.app_id, App.org_id == current_user.org_id)
    )
    app = result.scalar_one_or_none()
    if not app:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="App not found in org")

    profile = await run_target_analysis(payload.app_id, current_user.org_id)
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
    """
    if not current_user.org_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User has no associated org"
        )

    # Verify app belongs to org
    result = await db.execute(
        select(App).where(App.id == payload.app_id, App.org_id == current_user.org_id)
    )
    app = result.scalar_one_or_none()
    if not app:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="App not found in org")

    profile = await discover_endpoints(payload.app_id, current_user.org_id)
    return DiscoveryEndpointsResponse(**profile)
