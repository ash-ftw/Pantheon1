import asyncio
import concurrent.futures
import uuid
from typing import Any

from sqlalchemy import select, update

from app.database import async_session_factory
from app.logging import get_logger
from app.models import Org
from app.services.k8s_service import k8s_tenant_service
from app.worker import celery_app

logger = get_logger(__name__)


async def _async_provision_tenant(org_id_str: str) -> dict[str, Any]:
    """Async helper executing K8s namespace provisioning and updating Org status."""
    org_id = uuid.UUID(org_id_str)
    async with async_session_factory() as db:
        result = await db.execute(select(Org).where(Org.id == org_id))
        org = result.scalar_one_or_none()
        if not org:
            logger.error("provision_task_org_not_found", org_id=org_id_str)
            return {"status": "failed", "reason": "Org not found"}

        # Update status to provisioning
        org.cluster_status = "provisioning"
        await db.commit()

        try:
            # Provision K8s namespace & default security policies
            prov_result = await k8s_tenant_service.provision_tenant_namespace(
                org_id=org.id, org_slug=org.slug
            )

            # Update status to ready
            await db.execute(
                update(Org).where(Org.id == org_id).values(cluster_status="ready")
            )
            await db.commit()

            logger.info("provision_task_completed", org_id=org_id_str)
            return prov_result
        except Exception as e:
            logger.error("provision_task_failed", org_id=org_id_str, error=str(e))
            await db.execute(
                update(Org).where(Org.id == org_id).values(cluster_status="failed")
            )
            await db.commit()
            return {"status": "failed", "error": str(e)}


@celery_app.task(name="tasks.provision_tenant_cluster")
def provision_tenant_cluster(org_id_str: str) -> dict[str, Any]:
    """Celery task: provisions tenant K8s namespace in background — PRD §7.1 / Module 3."""
    try:
        asyncio.get_running_loop()
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(asyncio.run, _async_provision_tenant(org_id_str))
            return future.result()
    except RuntimeError:
        return asyncio.run(_async_provision_tenant(org_id_str))
