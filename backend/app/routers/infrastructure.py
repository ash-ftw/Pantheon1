from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db_session
from app.models import User
from app.schemas import InfrastructureRead
from app.services.auth_service import get_current_user
from app.services.k8s_service import k8s_tenant_service
from app.tasks.provisioning import provision_tenant_cluster

router = APIRouter(prefix="/api/infrastructure", tags=["infrastructure"])


@router.get("/resources", response_model=InfrastructureRead)
async def get_infrastructure_resources(
    current_user: User = Depends(get_current_user),
) -> InfrastructureRead:
    """Infrastructure View — PRD Module 3 (Phase 3).

    Exposes scoped read-only view over the kubernetes Python client
    for the org's isolated tenant namespace (Deployments, Services,
    Pods, Quotas, NetworkPolicies). Raw kubectl is never exposed.
    """
    if not current_user.org_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User has no associated org"
        )

    res = await k8s_tenant_service.get_cluster_resources(current_user.org_id)
    return InfrastructureRead(**res)


@router.post("/provision", status_code=status.HTTP_202_ACCEPTED)
async def trigger_provisioning(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, str]:
    """Trigger or retry background Kubernetes namespace provisioning for org."""
    if not current_user.org_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User has no associated org"
        )

    if current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin role required")

    try:
        provision_tenant_cluster.delay(str(current_user.org_id))
    except Exception:
        from app.tasks.provisioning import _async_provision_tenant

        await _async_provision_tenant(str(current_user.org_id))

    return {
        "status": "provisioning_queued",
        "org_id": str(current_user.org_id),
        "message": "Tenant Kubernetes namespace provisioning queued in background",
    }
