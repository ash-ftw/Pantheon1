"""App Runtime & Container Lifecycle Service — PRD Module 4.

Manages runtime container execution, state synchronization, stop/start,
and resource cleanup for tenant applications.
"""

import asyncio
from typing import Any

from docker.errors import DockerException, NotFound
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.logging import get_logger
from app.models import App, AppVersion
from app.services.docker_builder import docker_builder

logger = get_logger(__name__)


class AppRuntimeService:
    """Manages Docker container runtime state (start, stop, status sync, delete) for tenant apps."""

    def get_container_name(self, app_name: str) -> str:
        """Derive standard Docker container name from application name."""
        service_name = app_name.lower().replace(" ", "-")
        return f"pantheon-app-{service_name}"

    def is_container_running(self, app_name: str) -> bool:
        """Check if Docker container exists and is actively in 'running' state."""
        try:
            client = docker_builder._get_client()
            if not client:
                return False
            container_name = self.get_container_name(app_name)
            c = client.containers.get(container_name)
            c.reload()
            return c.status == "running"
        except (NotFound, DockerException, Exception):
            return False

    async def sync_app_status(self, app: App, db: AsyncSession) -> bool:
        """Sync app database status with actual Docker container status.

        Returns True if status changed and needs commit.
        """
        # Only synchronize runtime state if the app was previously built/running/stopped
        if app.status not in ("running", "stopped"):
            return False

        # If Docker daemon is unavailable, preserve current status without false transitions
        client = docker_builder._get_client()
        if not client:
            return False

        is_running = await asyncio.to_thread(self.is_container_running, app.name)
        new_status = "running" if is_running else "stopped"

        if app.status != new_status:
            logger.info(
                "syncing_app_runtime_status",
                app_id=str(app.id),
                app_name=app.name,
                old_status=app.status,
                new_status=new_status,
            )
            app.status = new_status
            db.add(app)
            return True

        return False

    async def start_app(self, app: App, db: AsyncSession) -> dict[str, Any]:
        """Start the app's Docker container instance.

        If container already exists (e.g. exited), starts it directly.
        If container does not exist, launches it from the latest built image tag.
        """
        container_name = self.get_container_name(app.name)
        client = docker_builder._get_client()

        if not client:
            # Fallback for mock/CI environments without Docker daemon
            app.status = "running"
            await db.commit()
            return {"status": "running", "container": container_name, "mode": "simulated"}

        # 1. Try starting existing container if found
        try:
            c = await asyncio.to_thread(client.containers.get, container_name)
            if c.status != "running":
                await asyncio.to_thread(c.start)
                await asyncio.to_thread(c.reload)
            app.status = "running"
            await db.commit()
            return {"status": "running", "container": container_name, "state": c.status}
        except NotFound:
            pass
        except Exception as e:
            logger.warning(
                "container_start_failed_retrying_recreate", container=container_name, error=str(e)
            )

        # 2. Recreate container from latest image version
        res = await db.execute(
            select(AppVersion)
            .where(AppVersion.app_id == app.id)
            .order_by(AppVersion.version_number.desc())
        )
        ver = res.scalars().first()
        if not ver or not ver.image_tag:
            raise ValueError(
                "No built container image found for this application. Please redeploy first."
            )

        target_port = 8085
        if app.target_profile and "exposed_ports" in app.target_profile:
            ports = app.target_profile.get("exposed_ports", [])
            if ports and isinstance(ports, list) and len(ports) > 0:
                target_port = ports[0]

        # Clean up any stale container with the same name before recreating
        try:
            old_c = await asyncio.to_thread(client.containers.get, container_name)
            await asyncio.to_thread(old_c.remove, force=True)
        except Exception:
            pass

        def _run_container():
            return client.containers.run(
                image=ver.image_tag,
                name=container_name,
                detach=True,
                ports={f"{target_port}/tcp": target_port},
            )

        c = await asyncio.to_thread(_run_container)
        app.status = "running"
        await db.commit()
        return {"status": "running", "container": container_name, "state": "running"}

    async def stop_app(self, app: App, db: AsyncSession) -> dict[str, Any]:
        """Stop the application's Docker container instance."""
        container_name = self.get_container_name(app.name)
        client = docker_builder._get_client()

        if client:
            try:
                c = await asyncio.to_thread(client.containers.get, container_name)
                await asyncio.to_thread(c.stop, timeout=2)
            except Exception as e:
                logger.info("container_stop_note", container=container_name, error=str(e))

        app.status = "stopped"
        await db.commit()
        return {"status": "stopped", "container": container_name}

    async def delete_app_resources(self, app_name: str) -> None:
        """Clean up Docker container when deleting an application."""
        container_name = self.get_container_name(app_name)
        client = docker_builder._get_client()
        if client:
            try:
                c = await asyncio.to_thread(client.containers.get, container_name)
                try:
                    await asyncio.to_thread(c.stop, timeout=2)
                except Exception:
                    pass
                await asyncio.to_thread(c.remove, force=True)
            except Exception:
                pass


app_runtime_service = AppRuntimeService()
