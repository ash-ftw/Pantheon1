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
import mimetypes
import os
import uuid
from typing import Any

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
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
from app.services.app_runtime_service import app_runtime_service
from app.services.docker_builder import docker_builder, sanitize_docker_name
from app.services.minio_service import minio_service
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
            _bg_task = loop.create_task(_async_ingest_app(app_id_str, version_id_str))
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
    discovery_status: str = "pending"
    target_profile: dict[str, Any] | None = None

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
    """List applications for the user's organization with live container status synchronization."""
    if not current_user.org_id:
        return []

    res = await db.execute(
        select(App).where(App.org_id == current_user.org_id).order_by(App.created_at.desc())
    )
    apps = list(res.scalars().all())

    # Sync runtime status for built apps (e.g. if container was stopped or exited on restart)
    status_changed = False
    for app in apps:
        if await app_runtime_service.sync_app_status(app, db):
            status_changed = True
    if status_changed:
        await db.commit()

    return apps


@router.get("/storage/registry", status_code=status.HTTP_200_OK)
async def list_registry_storage(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """List all image repositories stored in MinIO pantheon-registry bucket with active/orphaned status."""
    active_names: set[str] = set()
    if current_user.org_id:
        active_apps_res = await db.execute(select(App.name).where(App.org_id == current_user.org_id))
        active_names = {sanitize_docker_name(name) for name in active_apps_res.scalars().all()}

    repos = await minio_service.list_repositories(active_app_names=active_names)
    return {
        "bucket": minio_service.registry_bucket,
        "total_repositories": len(repos),
        "orphaned_count": sum(1 for r in repos if r.get("is_orphaned")),
        "repositories": repos,
    }


@router.delete("/storage/registry/{repo_path:path}", status_code=status.HTTP_200_OK)
async def delete_registry_storage(
    repo_path: str,
    purge_docker: bool = Query(default=True, description="Also remove local Docker image cache and container"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Remove an image repository and all its blobs from MinIO storage and local Docker image cache."""
    result = await minio_service.delete_repository(repo_path, purge_local_docker=purge_docker)
    return result


@router.post("/storage/registry/purge-orphans", status_code=status.HTTP_200_OK)
async def purge_orphaned_registry_storage(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Purge all orphaned images from MinIO bucket that are not associated with any active application."""
    active_names: set[str] = set()
    if current_user.org_id:
        active_apps_res = await db.execute(select(App.name).where(App.org_id == current_user.org_id))
        active_names = {sanitize_docker_name(name) for name in active_apps_res.scalars().all()}

    repos = await minio_service.list_repositories(active_app_names=active_names)
    orphans = [r for r in repos if r.get("is_orphaned")]

    purged = []
    for o in orphans:
        res = await minio_service.delete_repository(o["repository"], purge_local_docker=True)
        purged.append({"repository": o["repository"], "result": res})

    return {
        "status": "success",
        "purged_count": len(purged),
        "purged": purged,
    }


@router.get("/{app_id}", response_model=AppRead)
async def get_app_details(
    app_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> App:
    """Get details for a specific application with live container status synchronization."""
    if not current_user.org_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No org found")

    res = await db.execute(select(App).where(App.id == app_id, App.org_id == current_user.org_id))
    app_obj = res.scalar_one_or_none()
    if not app_obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="App not found")

    if await app_runtime_service.sync_app_status(app_obj, db):
        await db.commit()

    return app_obj


@router.post("/{app_id}/start", response_model=AppRead)
async def start_app_instance(
    app_id: uuid.UUID,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> App:
    """Start application container instance if stopped or reopening system."""
    if not current_user.org_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No org found")

    res = await db.execute(select(App).where(App.id == app_id, App.org_id == current_user.org_id))
    app_obj = res.scalar_one_or_none()
    if not app_obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="App not found")

    try:
        await app_runtime_service.start_app(app_obj, db)
    except ValueError as err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(err))
    except Exception as err:
        logger.error("start_app_error", app_id=str(app_id), error=str(err))
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to start container: {err!s}",
        )

    await log_audit_event(
        db,
        org_id=current_user.org_id,
        user_id=current_user.id,
        user_email=current_user.email,
        action="app.start",
        resource_type="App",
        resource_id=str(app_obj.id),
        details={"name": app_obj.name},
        ip_address=request.client.host if request.client else None,
    )

    return app_obj


@router.post("/{app_id}/stop", response_model=AppRead)
async def stop_app_instance(
    app_id: uuid.UUID,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> App:
    """Stop application container instance."""
    if not current_user.org_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No org found")

    res = await db.execute(select(App).where(App.id == app_id, App.org_id == current_user.org_id))
    app_obj = res.scalar_one_or_none()
    if not app_obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="App not found")

    await app_runtime_service.stop_app(app_obj, db)

    await log_audit_event(
        db,
        org_id=current_user.org_id,
        user_id=current_user.id,
        user_email=current_user.email,
        action="app.stop",
        resource_type="App",
        resource_id=str(app_obj.id),
        details={"name": app_obj.name},
        ip_address=request.client.host if request.client else None,
    )

    return app_obj


@router.delete("/{app_id}", status_code=status.HTTP_200_OK)
async def delete_app_instance(
    app_id: uuid.UUID,
    request: Request,
    purge_minio: bool = Query(
        default=True,
        description="Also remove image repository, layer blobs, and artifacts from MinIO storage and local Docker image cache",
    ),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Delete an application and all its versions, deployments, and container resources."""
    if not current_user.org_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No org found")

    res = await db.execute(select(App).where(App.id == app_id, App.org_id == current_user.org_id))
    app_obj = res.scalar_one_or_none()
    if not app_obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="App not found")

    app_name = app_obj.name
    # Clean up Docker resources
    await app_runtime_service.delete_app_resources(app_name)

    # Clean up MinIO bucket and Docker image cache if purge_minio is True
    minio_purged = False
    if purge_minio:
        try:
            await minio_service.delete_app_storage(
                app_name=app_name,
                org_id=str(current_user.org_id),
                purge_local_docker=True,
            )
            minio_purged = True
        except Exception as e:
            logger.warning("minio_purge_failed_on_delete", error=str(e), app_name=app_name)

    # Delete app from database (cascades to versions, deployments, routes)
    await db.delete(app_obj)
    await db.commit()

    await log_audit_event(
        db,
        org_id=current_user.org_id,
        user_id=current_user.id,
        user_email=current_user.email,
        action="app.delete",
        resource_type="App",
        resource_id=str(app_id),
        details={"name": app_name, "minio_purged": minio_purged},
        ip_address=request.client.host if request.client else None,
    )

    return {"status": "deleted", "id": str(app_id), "name": app_name, "minio_purged": minio_purged}


@router.get("/{app_id}/preview")
async def preview_app(
    app_id: uuid.UUID,
    request: Request,
    target_port: int | None = None,
    db: AsyncSession = Depends(get_db_session),
) -> Response:
    """Proxy live app request and strip framing restrictions (X-Frame-Options, CSP) for preview."""
    import httpx

    # Resolve target application
    res = await db.execute(select(App).where(App.id == app_id))
    app_obj = res.scalar_one_or_none()

    effective_port = target_port
    if app_obj:
        # Check container state and dynamically locate host port
        client = docker_builder._get_client()
        if client:
            container_name = app_runtime_service.get_container_name(app_obj.name)
            try:
                c = await asyncio.to_thread(client.containers.get, container_name)
                # Auto-start container if stopped
                if c.status != "running":
                    await app_runtime_service.start_app(app_obj, db)
                    c = await asyncio.to_thread(client.containers.get, container_name)

                # Inspect actual host port binding
                if c.status == "running" and c.ports:
                    for _, bindings in c.ports.items():
                        if bindings and len(bindings) > 0:
                            h_port = bindings[0].get("HostPort")
                            if h_port and (effective_port is None or effective_port == 8085):
                                effective_port = int(h_port)
                                break
            except Exception:
                # If container does not exist yet, attempt starting it from latest image
                try:
                    start_res = await app_runtime_service.start_app(app_obj, db)
                    if "host_port" in start_res:
                        effective_port = int(start_res["host_port"])
                except Exception:
                    pass

        if effective_port is None:
            if app_obj.target_profile and "host_port" in app_obj.target_profile:
                effective_port = int(app_obj.target_profile["host_port"])

    if effective_port is None:
        effective_port = 8085

    target_host = os.getenv("PANTHEON_TARGET_HOST", "localhost")
    target_url = f"http://{target_host}:{effective_port}/"

    # Derive the external host the client used to reach Pantheon (for direct links and base tags)
    client_host = request.headers.get("x-forwarded-host") or request.url.hostname or "localhost"
    client_hostname = client_host.split(":")[0]

    async with httpx.AsyncClient(timeout=3.0) as client:
        try:
            resp = await client.get(target_url, headers={"accept-encoding": "identity"})
            content = resp.content
            headers = dict(resp.headers)

            # Strip frame restriction, encoding, and length headers
            headers.pop("x-frame-options", None)
            headers.pop("content-security-policy", None)
            headers.pop("X-Frame-Options", None)
            headers.pop("Content-Security-Policy", None)
            headers.pop("content-length", None)
            headers.pop("Content-Length", None)
            headers.pop("transfer-encoding", None)
            headers.pop("Transfer-Encoding", None)
            headers.pop("content-encoding", None)
            headers.pop("Content-Encoding", None)

            headers["Access-Control-Allow-Origin"] = "*"
            headers["Access-Control-Allow-Methods"] = "*"
            headers["Access-Control-Allow-Headers"] = "*"

            media_type = resp.headers.get("content-type", "text/html")

            if "text/html" in media_type:
                preview_base = f"/api/apps/{app_id}/preview"
                import re

                try:
                    html_str = content.decode("utf-8", errors="replace")
                    # Rewrite root-relative URLs (href="/...", src="/...") so they route through the preview proxy
                    # Avoids all CORS and cross-origin restrictions in the preview iframe
                    html_str = re.sub(
                        r'((?:href|src|action)\s*=\s*["\'])/(?!/|#)([^"\']*)',
                        lambda m: f"{m.group(1)}{preview_base}/{m.group(2)}",
                        html_str,
                        flags=re.IGNORECASE,
                    )
                    # Inject base tag pointing to the preview proxy
                    base_tag = f'<base href="{preview_base}/">'
                    if "<head>" in html_str:
                        html_str = html_str.replace("<head>", f"<head>{base_tag}", 1)
                    elif "<HEAD>" in html_str:
                        html_str = html_str.replace("<HEAD>", f"<HEAD>{base_tag}", 1)
                    else:
                        html_str = f"{base_tag}{html_str}"
                    content = html_str.encode("utf-8")
                except Exception:
                    pass

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
        <p>Your application is deployed and active in the tenant cluster on port <strong>{effective_port}</strong>.</p>
        <a href="http://{client_hostname}:{effective_port}" target="_blank" class="btn">Launch Direct Window (http://{client_hostname}:{effective_port})</a>
    </div>
</body>
</html>"""
            return Response(content=fallback_html, status_code=200, media_type="text/html")


@router.api_route("/{app_id}/preview/{subpath:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"])
async def preview_app_subpath(
    app_id: uuid.UUID,
    subpath: str,
    request: Request,
    target_port: int | None = None,
    db: AsyncSession = Depends(get_db_session),
) -> Response:
    """Proxy sub-path requests for previewing application assets, routes, and APIs."""
    import httpx

    effective_port = target_port
    if effective_port is None or effective_port == 8085:
        # Resolve target application host_port
        res = await db.execute(select(App).where(App.id == app_id))
        app_obj = res.scalar_one_or_none()
        if app_obj:
            client = docker_builder._get_client()
            if client:
                container_name = app_runtime_service.get_container_name(app_obj.name)
                try:
                    c = await asyncio.to_thread(client.containers.get, container_name)
                    if c.status == "running" and c.ports:
                        for _, bindings in c.ports.items():
                            if bindings and len(bindings) > 0:
                                h_port = bindings[0].get("HostPort")
                                if h_port:
                                    effective_port = int(h_port)
                                    break
                except Exception:
                    pass
            if (effective_port is None or effective_port == 8085) and app_obj.target_profile and "host_port" in app_obj.target_profile:
                effective_port = int(app_obj.target_profile["host_port"])

    if effective_port is None:
        effective_port = 8085

    target_host = os.getenv("PANTHEON_TARGET_HOST", "localhost")
    target_url = f"http://{target_host}:{effective_port}/{subpath}"
    if request.url.query:
        target_url = f"{target_url}?{request.url.query}"

    forward_headers = dict(request.headers)
    forward_headers.pop("host", None)
    forward_headers.pop("content-length", None)
    forward_headers["accept-encoding"] = "identity"

    try:
        body = await request.body()
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=False) as client:
            resp = await client.request(
                method=request.method,
                url=target_url,
                headers=forward_headers,
                content=body if body else None,
            )
            headers = dict(resp.headers)
            headers.pop("x-frame-options", None)
            headers.pop("content-security-policy", None)
            headers.pop("X-Frame-Options", None)
            headers.pop("Content-Security-Policy", None)
            headers.pop("content-length", None)
            headers.pop("Content-Length", None)
            headers.pop("transfer-encoding", None)
            headers.pop("Transfer-Encoding", None)
            headers.pop("content-encoding", None)
            headers.pop("Content-Encoding", None)
            headers.pop("access-control-allow-origin", None)
            headers.pop("Access-Control-Allow-Origin", None)

            headers["Access-Control-Allow-Origin"] = "*"
            headers["Access-Control-Allow-Methods"] = "*"
            headers["Access-Control-Allow-Headers"] = "*"

            media_type = resp.headers.get("content-type")
            if not media_type or media_type == "":
                guessed, _ = mimetypes.guess_type(subpath)
                if guessed:
                    media_type = guessed
                elif subpath.endswith((".js", ".mjs", ".ts", ".tsx", ".jsx")):
                    media_type = "application/javascript; charset=utf-8"
                elif subpath.endswith(".css"):
                    media_type = "text/css; charset=utf-8"
                elif subpath.endswith(".json"):
                    media_type = "application/json; charset=utf-8"
                elif subpath.endswith(".wasm"):
                    media_type = "application/wasm"
                else:
                    media_type = "application/octet-stream"

            return Response(
                content=resp.content,
                status_code=resp.status_code,
                media_type=media_type,
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
