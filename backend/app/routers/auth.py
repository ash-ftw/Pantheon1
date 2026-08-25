import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db_session
from app.logging import get_logger
from app.models import Org, OrgMember, User
from app.schemas import TokenResponse, UserLogin, UserRead, UserRegister
from app.services.audit_service import log_audit_event
from app.services.auth_service import (
    create_access_token,
    get_current_user,
    hash_password,
    verify_password,
)
from app.tasks.provisioning import provision_tenant_cluster

logger = get_logger(__name__)
limiter = Limiter(key_func=get_remote_address)
router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minute")
async def register(
    request: Request,
    payload: UserRegister,
    db: AsyncSession = Depends(get_db_session),
) -> TokenResponse:
    """User registration flow — PRD §7.1.

    1. Checks for duplicate email.
    2. Creates Org (slug auto-generated).
    3. Creates User with 'admin' role linked to Org.
    4. Triggers background tenant cluster provisioning.
    5. Returns JWT access token.
    """
    # Check duplicate email
    existing = await db.execute(select(User).where(User.email == payload.email))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already exists",
        )

    # Generate org slug
    slug_base = payload.org_name.lower().replace(" ", "-")
    slug = f"{slug_base}-{uuid.uuid4().hex[:6]}"

    # Create Org
    org = Org(name=payload.org_name, slug=slug, cluster_status="provisioning")
    db.add(org)
    await db.flush()

    # Create User
    hashed_pwd = hash_password(payload.password)
    user = User(
        email=payload.email,
        hashed_password=hashed_pwd,
        full_name=payload.full_name,
        org_id=org.id,
        role="admin",
    )
    db.add(user)
    await db.flush()

    # Create OrgMember junction entry
    member = OrgMember(org_id=org.id, user_id=user.id, role="admin")
    db.add(member)

    # Audit log
    await log_audit_event(
        db,
        org_id=org.id,
        user_id=user.id,
        user_email=user.email,
        action="user.register",
        resource_type="User",
        resource_id=str(user.id),
        details={"org_name": org.name, "role": "admin"},
        ip_address=request.client.host if request.client else None,
    )
    await db.commit()

    # Trigger background K8s namespace provisioning task (Phase 3)
    try:
        provision_tenant_cluster.delay(str(org.id))
    except Exception as e:
        logger.warning("provision_task_dispatch_failed", error=str(e))

    # Issue JWT token
    token = create_access_token(user_id=user.id, email=user.email, org_id=org.id, role="admin")
    return TokenResponse(
        access_token=token,
        expires_in_seconds=settings.jwt_access_token_expire_minutes * 60,
    )


@router.post("/login", response_model=TokenResponse)
@limiter.limit("20/minute")
async def login(
    request: Request,
    payload: UserLogin,
    db: AsyncSession = Depends(get_db_session),
) -> TokenResponse:
    """User authentication login endpoint."""
    result = await db.execute(select(User).where(User.email == payload.email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled",
        )

    # Audit log
    if user.org_id:
        await log_audit_event(
            db,
            org_id=user.org_id,
            user_id=user.id,
            user_email=user.email,
            action="user.login",
            resource_type="User",
            resource_id=str(user.id),
            ip_address=request.client.host if request.client else None,
        )
        await db.commit()

    token = create_access_token(
        user_id=user.id, email=user.email, org_id=user.org_id, role=user.role
    )
    return TokenResponse(
        access_token=token,
        expires_in_seconds=settings.jwt_access_token_expire_minutes * 60,
    )


@router.get("/me", response_model=UserRead)
async def get_me(current_user: User = Depends(get_current_user)) -> User:
    """Get current authenticated user profile."""
    return current_user
