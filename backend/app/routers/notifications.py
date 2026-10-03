"""Notifications Router — PRD Module 1 (Phase 14).

REST endpoints for reading and managing organization alerts and notifications.
"""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db_session
from app.models import Notification, User
from app.schemas import NotificationCreate, NotificationRead
from app.services.auth_service import get_current_user
from app.services.notification_service import notification_service

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


@router.get("", response_model=list[NotificationRead])
async def list_notifications(
    unread_only: bool = Query(False, description="Filter for unread notifications only"),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> list[Notification]:
    """Retrieve notifications scoped to current organization and user."""
    if not current_user.org_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No organization associated with user",
        )

    return await notification_service.list_notifications(
        session=db,
        org_id=current_user.org_id,
        user_id=current_user.id,
        unread_only=unread_only,
        limit=limit,
    )


@router.get("/unread-count")
async def get_unread_count(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, int]:
    """Return count of unread notifications for quick UI badge rendering."""
    if not current_user.org_id:
        return {"unread_count": 0}

    count = await notification_service.get_unread_count(
        session=db, org_id=current_user.org_id, user_id=current_user.id
    )
    return {"unread_count": count}


@router.post("/{notification_id}/read")
async def mark_notification_as_read(
    notification_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, bool]:
    """Mark a specific notification as read."""
    if not current_user.org_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No organization associated with user",
        )

    success = await notification_service.mark_as_read(
        session=db, notification_id=notification_id, org_id=current_user.org_id
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found",
        )
    await db.commit()
    return {"success": True}


@router.post("/read-all")
async def mark_all_as_read(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Mark all unread notifications in current organization as read."""
    if not current_user.org_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No organization associated with user",
        )

    count = await notification_service.mark_all_as_read(
        session=db, org_id=current_user.org_id, user_id=current_user.id
    )
    await db.commit()
    return {"success": True, "marked_count": count}


@router.post("", response_model=NotificationRead)
async def create_custom_notification(
    payload: NotificationCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> Notification:
    """Create a manual notification (e.g. for administrative or testing purposes)."""
    if not current_user.org_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No organization associated with user",
        )

    notif = await notification_service.create_notification(
        session=db,
        org_id=current_user.org_id,
        user_id=current_user.id,
        title=payload.title,
        message=payload.message,
        type=payload.type,
        category=payload.category,
        link=payload.link,
    )
    await db.commit()
    return notif
