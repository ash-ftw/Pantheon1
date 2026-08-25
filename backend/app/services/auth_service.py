import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import bcrypt
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db_session
from app.models import Org, User

# OAuth2 scheme (auto_error=False allows optional auth token check for dev fallback)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


def hash_password(password: str) -> str:
    """Hash password using bcrypt."""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against bcrypt hash."""
    return bcrypt.checkpw(
        plain_password.encode("utf-8"), hashed_password.encode("utf-8")
    )


def create_access_token(
    user_id: uuid.UUID,
    email: str,
    org_id: uuid.UUID | None = None,
    role: str = "tester",
    expires_delta: timedelta | None = None,
) -> str:
    """Generate JWT token with org_id and role scope."""
    now = datetime.now(UTC)
    expire = now + (expires_delta or timedelta(minutes=settings.jwt_access_token_expire_minutes))

    payload: dict[str, Any] = {
        "sub": str(user_id),
        "email": email,
        "org_id": str(org_id) if org_id else None,
        "role": role,
        "iat": now,
        "exp": expire,
    }

    # Encode with JWT secret / RS256
    token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    return token


def decode_access_token(token: str) -> dict[str, Any]:
    """Decode and validate JWT access token."""
    try:
        payload = jwt.decode(
            token, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
        )
        return payload
    except jwt.ExpiredSignatureError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e
    except jwt.InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e


async def _get_or_create_dev_user(db: AsyncSession) -> User:
    """Auto-provision a default dev user and organization for local dev environment."""
    result = await db.execute(select(User).where(User.email == "dev@pantheon.local"))
    user = result.scalar_one_or_none()
    if user:
        return user

    # Ensure dev org exists
    org_res = await db.execute(select(Org).where(Org.name == "Default Dev Org"))
    org = org_res.scalar_one_or_none()
    if not org:
        org = Org(name="Default Dev Org", slug="default-dev-org", cluster_status="ready")
        db.add(org)
        await db.flush()

    user = User(
        email="dev@pantheon.local",
        hashed_password=hash_password("devpassword123"),
        full_name="Dev User",
        org_id=org.id,
        role="admin",
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def get_current_user(
    token: str | None = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db_session),
) -> User:
    """Dependency to resolve and authenticate current user from JWT token.

    In development mode, if no token is provided or invalid token is supplied,
    automatically falls back to default dev user.
    """
    if token:
        try:
            payload = decode_access_token(token)
            user_id_str = payload.get("sub")
            if user_id_str:
                user_id = uuid.UUID(user_id_str)
                result = await db.execute(select(User).where(User.id == user_id))
                user = result.scalar_one_or_none()
                if user and user.is_active:
                    return user
        except HTTPException:
            pass
        except Exception:
            pass

    # Fallback for dev / debug mode
    if settings.app_debug or settings.app_env.value == "development":
        return await _get_or_create_dev_user(db)

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )

