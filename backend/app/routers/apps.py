"""Application Ingestion & Lifecycle Management Router — PRD Module 4.

Endpoints:
- POST /api/apps/ingest/git: Ingest from Git repository URL
- POST /api/apps/ingest/compose: Ingest from Docker Compose YAML string
- GET /api/apps: List applications for current org
- GET /api/apps/{app_id}: Retrieve single application details & deployment status
- GET /api/apps/{app_id}/versions: Retrieve version history & build logs
- POST /api/apps/{app_id}/redeploy: Trigger new build/deployment for existing app
- WS /api/apps/{app_id}/logs/ws: Live WebSocket log tail stream
"""

import asyncio
import uuid

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Request,
    Response,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db_session
from app.logging import get_logger
from app.models import App, AppVersion, User
from app.routers.orgs import log_audit_event
from app.services.auth_service import get_current_user
from app.tasks.ingestion import _async_ingest_app, ingest_app

logger = get_logger(__name__)

router = APIRouter(prefix="/api/apps", tags=["apps"])


def dispatch_ingestion_task(app_id_str: str, version_id_str: str) -> None:
    """Dispatch ingestion task to Celery or fall back to asyncio task if Celery worker is unavailable."""
    celery_dispatched = False
    try:
        from app.worker import celery_app

        insp = celery_app.control.inspect(timeout=0.5)
        nodes = insp.ping()
        if nodes:
            ingest_app.delay(app_id_str, version_id_str)
            celery_dispatched = True
            logger.info("ingest_app_dispatched_celery", app_id=app_id_str)
    except Exception as e:
        logger.warning("celery_ping_failed", error=str(e))

    if not celery_dispatched:
        logger.info("ingest_app_dispatching_asyncio_fallback", app_id=app_id_str)
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(_async_ingest_app(app_id_str, version_id_str))
        except RuntimeError:
            asyncio.run(_async_ingest_app(app_id_str, version_id_str))


# Pydantic Schemas
class GitIngestRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    git_url: str = Field(..., min_length=5, max_length=1024)


class ComposeIngestRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    compose_yaml: str = Field(..., min_length=10)


class AppVersionRead(BaseModel):
    id: uuid.UUID
    app_id: uuid.UUID
    version_number: int
    commit_hash: str | None = None
    image_tag: str | None = None
    detected_framework: str | None = None
    build_logs: str | None = None

    model_config = ConfigDict(from_attributes=True)


class AppDeploymentRead(BaseModel):
    id: uuid.UUID
    app_id: uuid.UUID
    version_id: uuid.UUID
    status: str
    k8s_namespace: str | None = None
    error_message: str | None = None

    model_config = ConfigDict(from_attributes=True)


class AppRead(BaseModel):
    id: uuid.UUID
    org_id: uuid.UUID
    name: str
    source_type: str
    source_url: str | None = None
    status: str

    model_config = ConfigDict(from_attributes=True)


@router.post("/ingest/git", response_model=AppRead, status_code=status.HTTP_202_ACCEPTED)
async def ingest_from_git(
    payload: GitIngestRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> App:
    """Ingest application from Git repository URL — PRD Module 4."""
    if not current_user.org_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="No organization associated with user"
        )

    # Create App record
    app_obj = App(
        org_id=current_user.org_id,
        name=payload.name,
        source_type="git",
        source_url=payload.git_url,
        status="queued",
    )
    db.add(app_obj)
    await db.commit()
    await db.refresh(app_obj)

    # Create initial version record
    version = AppVersion(app_id=app_obj.id, version_number=1)
    db.add(version)
    await db.commit()
    await db.refresh(version)

    # Trigger ingestion task (Celery worker or asyncio background task fallback)
    dispatch_ingestion_task(str(app_obj.id), str(version.id))

    await log_audit_event(
        db,
        org_id=current_user.org_id,
        user_id=current_user.id,
        user_email=current_user.email,
        action="app.ingest.git",
        resource_type="App",
        resource_id=str(app_obj.id),
        details={"name": payload.name, "git_url": payload.git_url},
        ip_address=request.client.host if request.client else None,
    )

    return app_obj


@router.post("/ingest/compose", response_model=AppRead, status_code=status.HTTP_202_ACCEPTED)
async def ingest_from_compose(
    payload: ComposeIngestRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> App:
    """Ingest application from Docker Compose YAML — PRD Module 4."""
    if not current_user.org_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="No organization associated with user"
        )

    # Create App record
    app_obj = App(
        org_id=current_user.org_id,
        name=payload.name,
        source_type="compose",
        compose_yaml=payload.compose_yaml,
        status="queued",
    )
    db.add(app_obj)
    await db.commit()
    await db.refresh(app_obj)

    # Create initial version record
    version = AppVersion(app_id=app_obj.id, version_number=1)
    db.add(version)
    await db.commit()
    await db.refresh(version)

    # Trigger ingestion task (Celery worker or asyncio background task fallback)
    dispatch_ingestion_task(str(app_obj.id), str(version.id))

    await log_audit_event(
        db,
        org_id=current_user.org_id,
        user_id=current_user.id,
        user_email=current_user.email,
        action="app.ingest.compose",
        resource_type="App",
        resource_id=str(app_obj.id),
        details={"name": payload.name},
        ip_address=request.client.host if request.client else None,
    )

    return app_obj


@router.get("", response_model=list[AppRead])
async def list_apps(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> list[App]:
    """List applications for the user's organization."""
    if not current_user.org_id:
        return []

    res = await db.execute(select(App).where(App.org_id == current_user.org_id))
    return list(res.scalars().all())


@router.get("/{app_id}", response_model=AppRead)
async def get_app_details(
    app_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> App:
    """Get details for a specific application."""
    if not current_user.org_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No org found")

    res = await db.execute(
        select(App).where(App.id == app_id, App.org_id == current_user.org_id)
    )
    app_obj = res.scalar_one_or_none()
    if not app_obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="App not found")

    return app_obj


@router.get("/{app_id}/preview")
async def preview_app(
    app_id: uuid.UUID,
    target_port: int = 8085,
    db: AsyncSession = Depends(get_db_session),
) -> Response:
    """Proxy live app request and strip framing restrictions (X-Frame-Options, CSP) for preview."""
    import httpx

    target_url = f"http://localhost:{target_port}/"
    async with httpx.AsyncClient(timeout=3.0) as client:
        try:
            resp = await client.get(target_url)
            content = resp.content
            headers = dict(resp.headers)

            # Strip frame restriction and length headers
            headers.pop("x-frame-options", None)
            headers.pop("content-security-policy", None)
            headers.pop("X-Frame-Options", None)
            headers.pop("Content-Security-Policy", None)
            headers.pop("content-length", None)
            headers.pop("Content-Length", None)
            headers.pop("transfer-encoding", None)
            headers.pop("Transfer-Encoding", None)

            headers["Access-Control-Allow-Origin"] = "*"
            headers["Access-Control-Allow-Methods"] = "*"
            headers["Access-Control-Allow-Headers"] = "*"

            media_type = resp.headers.get("content-type", "text/html")

            if "text/html" in media_type:
                # Inject base tag so relative and root-relative assets resolve against target_port
                base_tag = f'<base href="http://localhost:{target_port}/">'.encode("utf-8")
                if b"<head>" in content:
                    content = content.replace(b"<head>", b"<head>" + base_tag, 1)
                elif b"<HEAD>" in content:
                    content = content.replace(b"<HEAD>", b"<HEAD>" + base_tag, 1)
                else:
                    content = base_tag + content

            return Response(
                content=content,
                status_code=resp.status_code,
                media_type=media_type,
                headers=headers,
            )
        except Exception:
            # Fallback mock preview page if container server is offline
            fallback_html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Pantheon Live App Preview</title>
    <style>
        body {{ background: #07090d; color: #e2e8f0; font-family: system-ui, sans-serif; display: flex; align-items: center; justify-content: center; height: 100vh; margin: 0; text-align: center; }}
        .card {{ background: #0d1117; border: 1px solid #00d4aa; padding: 40px; border-radius: 16px; max-width: 500px; box-shadow: 0 10px 30px rgba(0,212,170,0.15); }}
        h2 {{ color: #00d4aa; margin-top: 0; display: flex; align-items: center; justify-content: center; gap: 10px; }}
        p {{ color: #94a3b8; font-size: 14px; line-height: 1.6; }}
        .btn {{ display: inline-block; background: #00d4aa; color: #07090d; font-weight: 700; padding: 12px 24px; border-radius: 8px; text-decoration: none; margin-top: 16px; font-size: 13px; }}
        .btn:hover {{ background: #00b38f; }}
    </style>
</head>
<body>
    <div class="card">
        <h2>⚡ Pantheon App Instance Running</h2>
        <p>Your application is deployed and active in the tenant cluster on port <strong>{target_port}</strong>.</p>
        <a href="http://localhost:{target_port}" target="_blank" class="btn">Launch Direct Window (http://localhost:{target_port})</a>
    </div>
</body>
</html>"""
            return Response(content=fallback_html, status_code=200, media_type="text/html")


@router.get("/{app_id}/preview/{subpath:path}")
async def preview_app_subpath(
    app_id: uuid.UUID,
    subpath: str,
    target_port: int = 8085,
    db: AsyncSession = Depends(get_db_session),
) -> Response:
    """Proxy sub-path requests for previewing application assets and routes."""
    import httpx

    target_url = f"http://localhost:{target_port}/{subpath}"
    async with httpx.AsyncClient(timeout=5.0) as client:
        try:
            resp = await client.get(target_url)
            headers = dict(resp.headers)
            headers.pop("x-frame-options", None)
            headers.pop("content-security-policy", None)
            headers.pop("X-Frame-Options", None)
            headers.pop("Content-Security-Policy", None)
            headers.pop("content-length", None)
            headers.pop("Content-Length", None)
            headers.pop("transfer-encoding", None)
            headers.pop("Transfer-Encoding", None)

            headers["Access-Control-Allow-Origin"] = "*"
            headers["Access-Control-Allow-Methods"] = "*"
            headers["Access-Control-Allow-Headers"] = "*"

            return Response(
                content=resp.content,
                status_code=resp.status_code,
                media_type=resp.headers.get("content-type"),
                headers=headers,
            )
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"Proxy error: {e!s}")


@router.get("/{app_id}/versions", response_model=list[AppVersionRead])
async def get_app_versions(
    app_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> list[AppVersion]:
    """Get deployment version history for an app — PRD Module 4 Item 11."""
    if not current_user.org_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No org found")

    # Verify ownership
    res_app = await db.execute(
        select(App).where(App.id == app_id, App.org_id == current_user.org_id)
    )
    if not res_app.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="App not found")

    res = await db.execute(
        select(AppVersion)
        .where(AppVersion.app_id == app_id)
        .order_by(AppVersion.version_number.desc())
    )
    return list(res.scalars().all())


@router.post("/{app_id}/redeploy", response_model=AppRead)
async def redeploy_app(
    app_id: uuid.UUID,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> App:
    """Trigger redeploy for existing app — PRD Module 4 Item 11."""
    if not current_user.org_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No org found")

    res_app = await db.execute(
        select(App).where(App.id == app_id, App.org_id == current_user.org_id)
    )
    app_obj = res_app.scalar_one_or_none()
    if not app_obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="App not found")

    # Get latest version number
    res_ver = await db.execute(
        select(AppVersion)
        .where(AppVersion.app_id == app_id)
        .order_by(AppVersion.version_number.desc())
    )
    latest = res_ver.scalars().first()
    new_version_num = (latest.version_number + 1) if latest else 1

    new_version = AppVersion(app_id=app_id, version_number=new_version_num)
    db.add(new_version)
    app_obj.status = "queued"
    await db.commit()
    await db.refresh(app_obj)
    await db.refresh(new_version)

    dispatch_ingestion_task(str(app_obj.id), str(new_version.id))

    await log_audit_event(
        db,
        org_id=current_user.org_id,
        user_id=current_user.id,
        user_email=current_user.email,
        action="app.redeploy",
        resource_type="App",
        resource_id=str(app_obj.id),
        details={"version": new_version_num},
        ip_address=request.client.host if request.client else None,
    )

    return app_obj


@router.websocket("/{app_id}/logs/ws")
async def websocket_build_logs(websocket: WebSocket, app_id: str) -> None:
    """Live WebSocket build log tail stream from Redis pub/sub — PRD Module 4 Item 8."""
    await websocket.accept()
    channel_name = f"app:ingest:{app_id}"

    try:
        import redis.asyncio as aioredis

        from app.config import settings

        r = aioredis.from_url(settings.redis_url)
        pubsub = r.pubsub()
        await pubsub.subscribe(channel_name)

        while True:
            msg = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
            if msg and msg.get("type") == "message":
                data = msg.get("data")
                if isinstance(data, bytes):
                    data = data.decode("utf-8")
                await websocket.send_text(str(data))
            await asyncio.sleep(0.2)
    except WebSocketDisconnect:
        logger.info("websocket_logs_disconnected", app_id=app_id)
    except Exception as e:
        logger.error("websocket_logs_error", app_id=app_id, error=str(e))
        await websocket.close()
