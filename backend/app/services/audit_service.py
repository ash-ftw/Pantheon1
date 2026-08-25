import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AuditLog


async def log_audit_event(
    db: AsyncSession,
    org_id: uuid.UUID,
    action: str,
    resource_type: str,
    user_id: uuid.UUID | None = None,
    user_email: str | None = None,
    resource_id: str | None = None,
    details: dict[str, Any] | None = None,
    ip_address: str | None = None,
) -> AuditLog:
    """Helper to record an append-only audit event in the database — PRD §7.1."""
    entry = AuditLog(
        org_id=org_id,
        user_id=user_id,
        user_email=user_email,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        details=details or {},
        ip_address=ip_address,
    )
    db.add(entry)
    await db.flush()
    return entry
