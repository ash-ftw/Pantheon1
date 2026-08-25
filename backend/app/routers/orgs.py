import secrets
import uuid
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db_session
from app.models import AuditLog, Invitation, Org, OrgMember, User
from app.schemas import (
    AuditLogRead,
    InvitationAccept,
    InvitationCreate,
    InvitationRead,
    OrgMemberRead,
    OrgMemberUpdate,
    OrgRead,
    TokenResponse,
)
from app.services.audit_service import log_audit_event
from app.services.auth_service import create_access_token, get_current_user, hash_password

router = APIRouter(prefix="/api/orgs", tags=["orgs"])


@router.get("/current", response_model=OrgRead)
async def get_current_org(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> Org:
    """Get active organization for current user."""
    if not current_user.org_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User has no associated org"
        )

    result = await db.execute(select(Org).where(Org.id == current_user.org_id))
    org = result.scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")

    return org


@router.get("/members", response_model=list[OrgMemberRead])
async def list_org_members(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> list[OrgMemberRead]:
    """List all team members for current org — PRD §7.1."""
    if not current_user.org_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No org found")

    result = await db.execute(
        select(OrgMember, User)
        .join(User, OrgMember.user_id == User.id)
        .where(OrgMember.org_id == current_user.org_id)
    )
    rows = result.all()

    members = []
    for member, user in rows:
        m_read = OrgMemberRead(
            id=member.id,
            org_id=member.org_id,
            user_id=member.user_id,
            role=member.role,
            joined_at=member.joined_at,
            user_email=user.email,
            user_name=user.full_name,
        )
        members.append(m_read)

    return members


@router.patch("/members/{member_id}", response_model=OrgMemberRead)
async def update_member_role(
    member_id: uuid.UUID,
    payload: OrgMemberUpdate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> OrgMemberRead:
    """Update team member role (Admin role required)."""
    if current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin role required")

    if not current_user.org_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No org found")

    result = await db.execute(
        select(OrgMember, User)
        .join(User, OrgMember.user_id == User.id)
        .where(OrgMember.id == member_id, OrgMember.org_id == current_user.org_id)
    )
    row = result.first()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found")

    member, user = row
    member.role = payload.role
    user.role = payload.role

    await log_audit_event(
        db,
        org_id=current_user.org_id,
        user_id=current_user.id,
        user_email=current_user.email,
        action="org.member.update_role",
        resource_type="OrgMember",
        resource_id=str(member.id),
        details={"new_role": payload.role, "target_user": user.email},
        ip_address=request.client.host if request.client else None,
    )
    await db.commit()

    return OrgMemberRead(
        id=member.id,
        org_id=member.org_id,
        user_id=member.user_id,
        role=member.role,
        joined_at=member.joined_at,
        user_email=user.email,
        user_name=user.full_name,
    )


@router.delete("/members/{member_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_member(
    member_id: uuid.UUID,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> None:
    """Remove member from org (Admin role required)."""
    if current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin role required")
    if not current_user.org_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No org found")

    result = await db.execute(
        select(OrgMember).where(OrgMember.id == member_id, OrgMember.org_id == current_user.org_id)
    )
    member = result.scalar_one_or_none()
    if not member:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found")

    if member.user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot remove yourself"
        )

    await db.delete(member)
    await log_audit_event(
        db,
        org_id=current_user.org_id,
        user_id=current_user.id,
        user_email=current_user.email,
        action="org.member.remove",
        resource_type="OrgMember",
        resource_id=str(member_id),
        ip_address=request.client.host if request.client else None,
    )
    await db.commit()


@router.post("/invitations", response_model=InvitationRead, status_code=status.HTTP_201_CREATED)
async def invite_member(
    payload: InvitationCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> Invitation:
    """Invite teammate by email — PRD §7.1."""
    if current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin role required")
    if not current_user.org_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No org found")

    # Generate secure token
    token = secrets.token_urlsafe(32)
    expires_at = datetime.now(UTC) + timedelta(days=7)

    invitation = Invitation(
        org_id=current_user.org_id,
        email=payload.email,
        role=payload.role,
        token=token,
        expires_at=expires_at,
        created_by_id=current_user.id,
    )
    db.add(invitation)

    await log_audit_event(
        db,
        org_id=current_user.org_id,
        user_id=current_user.id,
        user_email=current_user.email,
        action="org.invite",
        resource_type="Invitation",
        resource_id=payload.email,
        details={"role": payload.role},
        ip_address=request.client.host if request.client else None,
    )
    await db.commit()

    return invitation


@router.get("/invitations", response_model=list[InvitationRead])
async def list_invitations(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> list[Invitation]:
    """List pending invitations for current org."""
    if not current_user.org_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No org found")

    result = await db.execute(
        select(Invitation).where(
            Invitation.org_id == current_user.org_id,
            Invitation.accepted_at.is_(None),
        )
    )
    return list(result.scalars().all())


@router.post("/invitations/accept", response_model=TokenResponse)
async def accept_invitation(
    payload: InvitationAccept,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
) -> TokenResponse:
    """Accept team invitation token & create user password."""
    result = await db.execute(select(Invitation).where(Invitation.token == payload.token))
    inv = result.scalar_one_or_none()

    if not inv or inv.accepted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or used invitation token"
        )

    if datetime.now(UTC) > inv.expires_at.replace(tzinfo=UTC):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invitation token has expired"
        )

    # Check if user email already exists
    user_res = await db.execute(select(User).where(User.email == inv.email))
    user = user_res.scalar_one_or_none()

    hashed_pwd = hash_password(payload.password)

    if not user:
        user = User(
            email=inv.email,
            hashed_password=hashed_pwd,
            full_name=payload.full_name,
            org_id=inv.org_id,
            role=inv.role,
        )
        db.add(user)
        await db.flush()

    member = OrgMember(org_id=inv.org_id, user_id=user.id, role=inv.role)
    db.add(member)
    inv.accepted_at = datetime.now(UTC)

    await log_audit_event(
        db,
        org_id=inv.org_id,
        user_id=user.id,
        user_email=user.email,
        action="org.invite.accept",
        resource_type="Invitation",
        resource_id=str(inv.id),
        ip_address=request.client.host if request.client else None,
    )
    await db.commit()

    token = create_access_token(user_id=user.id, email=user.email, org_id=inv.org_id, role=inv.role)
    return TokenResponse(access_token=token, expires_in_seconds=1440 * 60)


@router.get("/audit-log", response_model=list[AuditLogRead])
async def get_audit_log(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> list[AuditLog]:
    """Get append-only security audit log entries for current org — PRD §7.1."""
    if not current_user.org_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No org found")

    result = await db.execute(
        select(AuditLog)
        .where(AuditLog.org_id == current_user.org_id)
        .order_by(AuditLog.created_at.desc())
        .limit(100)
    )
    return list(result.scalars().all())
