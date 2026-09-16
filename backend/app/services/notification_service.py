"""Notification Service — PRD Module 1 (Phase 14).

Manages user/org notifications for ingestion build events, test run completions,
safety violation warnings, and team collaboration events.
"""

from __future__ import annotations

import uuid

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.logging import get_logger
from app.models import Notification, utcnow

logger = get_logger(__name__)


class NotificationService:
    """Service managing system notifications and user alert preferences."""

    async def create_notification(
        self,
        session: AsyncSession,
        org_id: uuid.UUID,
        title: str,
        message: str,
        type: str = "info",  # noqa: A002
        category: str = "general",
        user_id: uuid.UUID | None = None,
        link: str | None = None,
    ) -> Notification:
        """Create and persist a new notification."""
        notif = Notification(
            id=uuid.uuid4(),
            org_id=org_id,
            user_id=user_id,
            title=title,
            message=message,
            type=type,
            category=category,
            read=False,
            link=link,
            created_at=utcnow(),
        )
        session.add(notif)
        await session.flush()
        logger.info(
            "notification_created",
            notification_id=str(notif.id),
            org_id=str(org_id),
            category=category,
            title=title,
        )
        return notif

    async def list_notifications(
        self,
        session: AsyncSession,
        org_id: uuid.UUID,
        user_id: uuid.UUID | None = None,
        unread_only: bool = False,
        limit: int = 50,
    ) -> list[Notification]:
        """Fetch notifications scoped to an org and optional user."""
        query = select(Notification).where(Notification.org_id == org_id)
        if unread_only:
            query = query.where(Notification.read.is_(False))
        if user_id:
            query = query.where(
                (Notification.user_id == user_id) | (Notification.user_id.is_(None))
            )

        query = query.order_by(Notification.created_at.desc()).limit(limit)
        result = await session.execute(query)
        return list(result.scalars().all())

    async def mark_as_read(
        self, session: AsyncSession, notification_id: uuid.UUID, org_id: uuid.UUID
    ) -> bool:
        """Mark a single notification as read."""
        res = await session.execute(
            select(Notification).where(
                Notification.id == notification_id, Notification.org_id == org_id
            )
        )
        notif = res.scalar_one_or_none()
        if not notif:
            return False
        notif.read = True
        await session.flush()
        return True

    async def mark_all_as_read(
        self, session: AsyncSession, org_id: uuid.UUID, user_id: uuid.UUID | None = None
    ) -> int:
        """Mark all unread notifications in an org as read."""
        stmt = (
            update(Notification)
            .where(Notification.org_id == org_id, Notification.read.is_(False))
            .values(read=True)
        )
        if user_id:
            stmt = stmt.where((Notification.user_id == user_id) | (Notification.user_id.is_(None)))

        result = await session.execute(stmt)
        await session.flush()
        return int(getattr(result, "rowcount", 0) or 0)

    async def get_unread_count(
        self, session: AsyncSession, org_id: uuid.UUID, user_id: uuid.UUID | None = None
    ) -> int:
        """Count unread notifications for quick UI badge rendering."""
        query = select(func.count(Notification.id)).where(
            Notification.org_id == org_id, Notification.read.is_(False)
        )
        if user_id:
            query = query.where(
                (Notification.user_id == user_id) | (Notification.user_id.is_(None))
            )
        result = await session.execute(query)
        return result.scalar() or 0


notification_service = NotificationService()
