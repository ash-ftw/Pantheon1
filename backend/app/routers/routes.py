"""Route Broker API Router — PRD §7.5 / Module 11 (Phase 8).

Endpoints:
- POST /api/routes: Open an ephemeral, time-boxed route
- GET /api/routes: List routes for current organization
- GET /api/routes/{route_id}: Retrieve single route details
- DELETE /api/routes/{route_id}: Emergency Kill Switch (immediate synchronous revocation)
- DELETE /api/test-runs/{test_run_id}/route: Revoke route for test run
- POST /api/routes/sweep: Trigger expired route sweep
"""

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db_session
from app.models import User
from app.services.auth_service import get_current_user
from app.services.route_broker import route_broker_service

router = APIRouter(prefix="/api", tags=["route-broker"])


class OpenRouteRequest(BaseModel):
    """Payload to open an ephemeral attack route."""

    target_service: str = Field(
        min_length=1, max_length=255, description="Target service name within tenant namespace"
    )
    target_port: int = Field(ge=1, le=65535, description="Target service port (HTTP/HTTPS only)")
    ttl_seconds: int = Field(
        default=1800,
        ge=60,
        le=86400,
        description="Time-to-live in seconds before automatic revocation",
    )
    path_prefix: str = Field(
        default="/", max_length=255, description="Application route path prefix"
    )
    app_id: uuid.UUID | None = Field(default=None, description="Optional deployed app ID")
    test_run_id: uuid.UUID | None = Field(
        default=None, description="Optional associated test run ID"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "target_service": "web-frontend",
                "target_port": 8080,
                "ttl_seconds": 1800,
                "path_prefix": "/",
            }
        }
    )


class RevokeRouteRequest(BaseModel):
    """Optional payload for route revocation."""

    reason: str = Field(default="manual_kill_switch", max_length=255)


@router.post("/routes", status_code=status.HTTP_201_CREATED, response_model=dict[str, Any])
async def open_route(
    payload: OpenRouteRequest,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Open an ephemeral, application-layer route from range to tenant service."""
    if not current_user.org_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must belong to an organization to open routes.",
        )

    try:
        route = await route_broker_service.open_route(
            org_id=current_user.org_id,
            target_service=payload.target_service,
            target_port=payload.target_port,
            ttl_seconds=payload.ttl_seconds,
            path_prefix=payload.path_prefix,
            app_id=payload.app_id,
            test_run_id=payload.test_run_id,
            user_id=current_user.id,
            user_email=current_user.email,
            db=db,
        )
        return route
    except ValueError as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(err),
        )


@router.get("/routes", response_model=list[dict[str, Any]])
async def list_routes(
    status_filter: str | None = Query(
        None, alias="status", description="Filter by status (active, revoked, expired, all)"
    ),
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> list[dict[str, Any]]:
    """List routes for current organization with remaining TTL calculations."""
    if not current_user.org_id:
        return []

    return await route_broker_service.get_routes_for_org(
        org_id=current_user.org_id,
        status=status_filter,
        db=db,
    )


@router.get("/routes/{route_id}", response_model=dict[str, Any])
async def get_route(
    route_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Retrieve details of a specific route."""
    route = await route_broker_service.get_route(
        route_id=route_id,
        org_id=current_user.org_id,
        db=db,
    )
    if not route:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Route {route_id} not found",
        )
    return route


@router.delete("/routes/{route_id}", response_model=dict[str, Any])
async def kill_switch_revoke_route(
    route_id: uuid.UUID,
    reason: str = Query("manual_kill_switch", description="Reason for immediate revocation"),
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """EMERGENCY KILL SWITCH (PRD §7.5 / NFR-3.1): Revokes route synchronously in < 5 seconds."""
    try:
        revoked = await route_broker_service.revoke_route(
            route_id=route_id,
            reason=reason,
            org_id=current_user.org_id,
            user_id=current_user.id,
            user_email=current_user.email,
            db=db,
        )
        return revoked
    except KeyError as err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(err),
        )


@router.delete("/test-runs/{test_run_id}/route", response_model=list[dict[str, Any]])
async def revoke_test_run_route(
    test_run_id: uuid.UUID,
    reason: str = Query("test_run_stop", description="Reason for revocation"),
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> list[dict[str, Any]]:
    """Revoke routes associated with a test run — PRD §7.5."""
    return await route_broker_service.revoke_route_by_test_run(
        test_run_id=test_run_id,
        reason=reason,
        org_id=current_user.org_id,
        user_id=current_user.id,
        db=db,
    )


@router.post("/routes/sweep", response_model=list[dict[str, Any]])
async def sweep_routes(
    db: AsyncSession = Depends(get_db_session),
    _current_user: User = Depends(get_current_user),
) -> list[dict[str, Any]]:
    """Trigger an immediate TTL expiration sweep."""
    return await route_broker_service.sweep_expired_routes(db=db)
