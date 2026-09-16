"""Dashboard & Demo Catalog Router — PRD Module 1 (Phase 14).

Provides aggregated platform KPIs, security posture analytics, and preset demo application deployment.
"""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db_session
from app.logging import get_logger
from app.models import App, AppVersion, User, utcnow
from app.routers.apps import dispatch_ingestion_task
from app.routers.orgs import log_audit_event
from app.schemas import DashboardStatsRead, DemoAppRead
from app.services.auth_service import get_current_user
from app.services.dashboard_service import dashboard_service
from app.services.notification_service import notification_service

logger = get_logger(__name__)

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/stats", response_model=DashboardStatsRead)
async def get_dashboard_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Retrieve org-level dashboard metrics, resilience trends, and cluster status."""
    if not current_user.org_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No organization associated with user",
        )

    stats = await dashboard_service.get_dashboard_stats(db, current_user.org_id)
    return stats


@router.get("/demo-catalog", response_model=list[DemoAppRead])
async def get_demo_catalog(
    current_user: User = Depends(get_current_user),
) -> list[dict[str, Any]]:
    """Retrieve catalog of known-vulnerable preset demo applications (PRD §6.1)."""
    return dashboard_service.get_demo_catalog()


@router.post("/demo-catalog/{demo_id}/deploy")
async def deploy_demo_app(
    demo_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """1-Click Ingest & Deploy a Preset Demo Application.

    Allows exploring attack simulations immediately while custom tenant workloads provision.
    """
    if not current_user.org_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No organization associated with user",
        )

    demo = dashboard_service.get_demo_app(demo_id)
    if not demo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Demo app with ID '{demo_id}' not found in catalog",
        )

    # 1. Create App record
    new_app = App(
        id=uuid.uuid4(),
        org_id=current_user.org_id,
        name=demo["name"],
        source_type="git",
        source_url=demo["git_url"],
        status="building",
        created_at=utcnow(),
        updated_at=utcnow(),
    )
    db.add(new_app)

    # 2. Create initial AppVersion
    new_version = AppVersion(
        id=uuid.uuid4(),
        app_id=new_app.id,
        version_number=1,
        commit_hash=f"demo-{demo_id[:6]}",
        detected_framework=demo["architecture"],
        created_at=utcnow(),
    )
    db.add(new_version)
    await db.commit()

    # 3. Log audit event
    await log_audit_event(
        db=db,
        org_id=current_user.org_id,
        user_id=current_user.id,
        user_email=current_user.email,
        action="app.demo_deployed",
        resource_type="app",
        resource_id=str(new_app.id),
        details={"demo_id": demo_id, "name": demo["name"], "git_url": demo["git_url"]},
    )

    # 4. Notify user
    await notification_service.create_notification(
        session=db,
        org_id=current_user.org_id,
        user_id=current_user.id,
        title="Demo Application Ingestion Started",
        message=f"Deploying {demo['name']} ({demo['category']}). Ingestion and endpoint discovery are running.",
        type="info",
        category="build",
        link=f"/apps?app_id={new_app.id}",
    )
    await db.commit()

    # 5. Dispatch async ingestion worker
    dispatch_ingestion_task(str(new_app.id), str(new_version.id))

    return {
        "success": True,
        "app_id": str(new_app.id),
        "app_name": new_app.name,
        "demo_id": demo_id,
        "status": "building",
        "message": f"Successfully launched {demo['name']}. Building and deploying to tenant namespace.",
    }
