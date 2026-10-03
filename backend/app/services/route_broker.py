"""Route Broker Service — PRD §7.5 / Module 11 (Phase 8).

The Route Broker is the safety-critical architectural bridge between
the attacker range cluster and customer tenant workloads.

Key Invariants:
1. Zero Tenant Credential Exposure (NFR-1.3):
   The range cluster never holds tenant cluster credentials. Routing is done by
   the tenant cluster exposing an ephemeral Ingress endpoint.
2. Application-Layer Only (FR-5.5):
   Routes exclusively grant HTTP/HTTPS access to the declared target service and port.
   No L3/L4 network-level access is ever granted.
3. Sub-5-Second Emergency Kill Switch (NFR-3.1):
   Direct synchronous API call to revoke the route immediately, bypassing Celery queues.
4. TTL Auto-Expiry & Sweep (FR-5.2, NFR-2.1):
   Every route carries an expires_at timestamp; a background sweep revokes overdue routes
   independently of run state.
5. Transparent Audit Logging (FR-11.1):
   Every route create, revoke, and expiry event is recorded in the append-only audit_log.
"""

import time
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import async_session_factory
from app.logging import get_logger
from app.models import AuditLog, Route
from app.safety.simulation_guard import ScenarioTarget, validate_scenario_scope
from app.services.k8s_service import k8s_tenant_service

logger = get_logger(__name__)


def _utcnow() -> datetime:
    return datetime.now(UTC)


class RouteBrokerService:
    """Core service for managing ephemeral, time-boxed cross-cluster attack routes."""

    async def open_route(
        self,
        org_id: uuid.UUID,
        target_service: str,
        target_port: int,
        ttl_seconds: int = 1800,
        path_prefix: str = "/",
        app_id: uuid.UUID | None = None,
        test_run_id: uuid.UUID | None = None,
        user_id: uuid.UUID | None = None,
        user_email: str | None = None,
        db: AsyncSession | None = None,
    ) -> dict[str, Any]:
        """Open a scoped, time-boxed application-layer route from range to tenant service."""
        # 1. Scope & Security Validation (PRD §7.6 / FR-5.5)
        clean_service = target_service.strip()
        if not clean_service:
            raise ValueError("Target service cannot be empty.")

        if not (1 <= target_port <= 65535):
            raise ValueError(f"Target port {target_port} is invalid. Must be 1-65535.")

        # Disallow raw non-application ports (e.g. SSH, Telnet, SMB) as routes are application-layer only
        disallowed_ports = {22, 23, 135, 139, 445, 3389}
        if target_port in disallowed_ports:
            raise ValueError(
                f"Port {target_port} is disallowed. Routes grant application-layer (HTTP/HTTPS) access only (PRD §7.5 FR-5.5)."
            )

        namespace = k8s_tenant_service.get_namespace_name(org_id)
        target_obj = ScenarioTarget(service=clean_service, path=path_prefix)
        is_safe, _violation, reason = validate_scenario_scope(
            target_obj, tenant_namespace=namespace
        )
        if not is_safe:
            raise ValueError(f"Target outside permitted tenant scope: {reason}")

        # Bounded TTL (60 seconds to 24 hours; default 1800s / 30m)
        clamped_ttl = max(60, min(ttl_seconds, 86400))
        now = _utcnow()
        expires_at = now + timedelta(seconds=clamped_ttl)
        route_id = uuid.uuid4()
        ingress_name = f"route-{str(route_id)[:8]}"

        # Standardized route URL
        route_url = (
            f"http://{ingress_name}.{namespace}.svc.cluster.local:{target_port}{path_prefix}"
        )

        # 2. Provision Kubernetes Ingress object in tenant namespace
        k8s_res = k8s_tenant_service.create_ingress_route(
            namespace=namespace,
            route_id=route_id,
            target_service=clean_service,
            target_port=target_port,
            path_prefix=path_prefix,
            expires_at_iso=expires_at.isoformat(),
            org_id=str(org_id),
            test_run_id=str(test_run_id) if test_run_id else None,
        )

        route_record = Route(
            id=route_id,
            org_id=org_id,
            test_run_id=test_run_id,
            app_id=app_id,
            target_service=clean_service,
            target_port=target_port,
            path_prefix=path_prefix,
            route_url=route_url,
            status="active",
            ttl_seconds=clamped_ttl,
            created_at=now,
            expires_at=expires_at,
            ingress_name=ingress_name,
            namespace=namespace,
        )

        # 3. Persist route & audit log
        audit_entry = AuditLog(
            org_id=org_id,
            user_id=user_id,
            user_email=user_email,
            action="route.opened",
            resource_type="route",
            resource_id=str(route_id),
            details={
                "target_service": clean_service,
                "target_port": target_port,
                "path_prefix": path_prefix,
                "ttl_seconds": clamped_ttl,
                "expires_at": expires_at.isoformat(),
                "route_url": route_url,
                "ingress_name": ingress_name,
                "k8s_simulated": k8s_res.get("simulated", False),
            },
        )

        async def _persist(session: AsyncSession) -> None:
            session.add(route_record)
            session.add(audit_entry)
            await session.commit()

        if db is not None:
            await _persist(db)
        else:
            async with async_session_factory() as session:
                await _persist(session)

        logger.info(
            "route_opened",
            route_id=str(route_id),
            org_id=str(org_id),
            target=f"{clean_service}:{target_port}",
            expires_at=expires_at.isoformat(),
        )

        return self._format_route(route_record)

    async def revoke_route(
        self,
        route_id: uuid.UUID,
        reason: str = "manual_kill_switch",
        org_id: uuid.UUID | None = None,
        user_id: uuid.UUID | None = None,
        user_email: str | None = None,
        db: AsyncSession | None = None,
    ) -> dict[str, Any]:
        """Emergency Kill Switch: Synchronously revokes a route in under 5 seconds (NFR-3.1)."""
        start_time = time.monotonic()

        async def _execute(session: AsyncSession) -> tuple[Route | None, float]:
            query = select(Route).where(Route.id == route_id)
            if org_id:
                query = query.where(Route.org_id == org_id)
            res = await session.execute(query)
            route = res.scalar_one_or_none()
            if not route:
                return None, 0.0

            if route.status != "active":
                return route, 0.0

            # 1. Immediately delete the K8s Ingress object
            if route.ingress_name:
                k8s_tenant_service.delete_ingress_route(
                    namespace=route.namespace,
                    ingress_name=route.ingress_name,
                )

            # 2. Update status and timestamp
            now = _utcnow()
            route.status = "revoked"
            route.revoked_at = now
            route.revocation_reason = reason

            # 3. Append-only audit logging
            audit_entry = AuditLog(
                org_id=route.org_id,
                user_id=user_id,
                user_email=user_email,
                action="route.revoked",
                resource_type="route",
                resource_id=str(route_id),
                details={
                    "revocation_reason": reason,
                    "target_service": route.target_service,
                    "target_port": route.target_port,
                    "ingress_name": route.ingress_name,
                    "opened_at": route.created_at.isoformat(),
                },
            )
            session.add(audit_entry)
            await session.commit()
            duration_s = time.monotonic() - start_time
            return route, duration_s

        if db is not None:
            route_obj, elapsed_s = await _execute(db)
        else:
            async with async_session_factory() as session:
                route_obj, elapsed_s = await _execute(session)

        if not route_obj:
            raise KeyError(f"Route {route_id} not found or access denied.")

        logger.info(
            "route_revoked_kill_switch",
            route_id=str(route_id),
            reason=reason,
            elapsed_seconds=round(elapsed_s, 4),
        )

        formatted = self._format_route(route_obj)
        formatted["kill_switch_latency_seconds"] = round(elapsed_s, 4)
        return formatted

    async def revoke_route_by_test_run(
        self,
        test_run_id: uuid.UUID,
        reason: str = "test_run_completed",
        org_id: uuid.UUID | None = None,
        user_id: uuid.UUID | None = None,
        db: AsyncSession | None = None,
    ) -> list[dict[str, Any]]:
        """Revoke all routes linked to a test run — PRD §7.5."""

        async def _find_and_revoke(session: AsyncSession) -> list[dict[str, Any]]:
            query = select(Route).where(
                Route.test_run_id == test_run_id,
                Route.status == "active",
            )
            if org_id:
                query = query.where(Route.org_id == org_id)
            res = await session.execute(query)
            routes = res.scalars().all()
            results = []
            for r in routes:
                revoked = await self.revoke_route(
                    route_id=r.id,
                    reason=reason,
                    org_id=org_id,
                    user_id=user_id,
                    db=session,
                )
                results.append(revoked)
            return results

        if db is not None:
            return await _find_and_revoke(db)
        async with async_session_factory() as session:
            return await _find_and_revoke(session)

    async def sweep_expired_routes(self, db: AsyncSession | None = None) -> list[dict[str, Any]]:
        """Periodic background sweep task: auto-revokes routes past their TTL (NFR-2.1)."""
        now = _utcnow()

        async def _sweep(session: AsyncSession) -> list[dict[str, Any]]:
            query = select(Route).where(
                Route.status == "active",
                Route.expires_at <= now,
            )
            res = await session.execute(query)
            expired_routes = res.scalars().all()
            swept = []

            for r in expired_routes:
                if r.ingress_name:
                    k8s_tenant_service.delete_ingress_route(
                        namespace=r.namespace,
                        ingress_name=r.ingress_name,
                    )

                r.status = "expired"
                r.revoked_at = now
                r.revocation_reason = "ttl_expired"

                audit_entry = AuditLog(
                    org_id=r.org_id,
                    action="route.expired",
                    resource_type="route",
                    resource_id=str(r.id),
                    details={
                        "target_service": r.target_service,
                        "target_port": r.target_port,
                        "ttl_seconds": r.ttl_seconds,
                        "expired_at": now.isoformat(),
                    },
                )
                session.add(audit_entry)
                swept.append(self._format_route(r))

            if swept:
                await session.commit()
                logger.info("routes_ttl_sweep_completed", expired_count=len(swept))

            return swept

        if db is not None:
            return await _sweep(db)
        async with async_session_factory() as session:
            return await _sweep(session)

    async def get_routes_for_org(
        self,
        org_id: uuid.UUID,
        status: str | None = None,
        db: AsyncSession | None = None,
    ) -> list[dict[str, Any]]:
        """Retrieve routes for an organization, updating any inline-expired active routes."""
        now = _utcnow()

        async def _get(session: AsyncSession) -> list[dict[str, Any]]:
            # Inline sweep check: update any overdue active routes
            await session.execute(
                update(Route)
                .where(
                    Route.org_id == org_id,
                    Route.status == "active",
                    Route.expires_at <= now,
                )
                .values(
                    status="expired",
                    revoked_at=now,
                    revocation_reason="ttl_expired",
                )
            )
            await session.commit()

            query = select(Route).where(Route.org_id == org_id).order_by(Route.created_at.desc())
            if status and status != "all":
                query = query.where(Route.status == status)

            res = await session.execute(query)
            routes = res.scalars().all()
            return [self._format_route(r) for r in routes]

        if db is not None:
            return await _get(db)
        async with async_session_factory() as session:
            return await _get(session)

    async def get_route(
        self,
        route_id: uuid.UUID,
        org_id: uuid.UUID | None = None,
        db: AsyncSession | None = None,
    ) -> dict[str, Any] | None:
        """Retrieve single route details."""

        async def _get(session: AsyncSession) -> dict[str, Any] | None:
            query = select(Route).where(Route.id == route_id)
            if org_id:
                query = query.where(Route.org_id == org_id)
            res = await session.execute(query)
            route = res.scalar_one_or_none()
            return self._format_route(route) if route else None

        if db is not None:
            return await _get(db)
        async with async_session_factory() as session:
            return await _get(session)

    def _format_route(self, route: Route) -> dict[str, Any]:
        """Convert a Route model instance to a JSON-serializable dictionary with remaining TTL."""
        now = _utcnow()
        remaining_s = 0
        if route.status == "active":
            remaining_s = max(0, int((route.expires_at - now).total_seconds()))

        route_id_str = str(route.id)
        short_id = route_id_str[:8]

        return {
            "id": route_id_str,
            "org_id": str(route.org_id),
            "test_run_id": str(route.test_run_id) if route.test_run_id else None,
            "app_id": str(route.app_id) if route.app_id else None,
            "target_service": route.target_service,
            "target_port": route.target_port,
            "path_prefix": route.path_prefix,
            "route_url": route.route_url,
            "internal_url": route.route_url,
            "public_url": f"{settings.pantheon_public_host.rstrip('/')}/r/{short_id}",
            "status": route.status,
            "ttl_seconds": route.ttl_seconds,
            "ttl_remaining_seconds": remaining_s,
            "created_at": route.created_at.isoformat(),
            "expires_at": route.expires_at.isoformat(),
            "revoked_at": route.revoked_at.isoformat() if route.revoked_at else None,
            "revocation_reason": route.revocation_reason,
            "ingress_name": route.ingress_name,
            "namespace": route.namespace,
        }


# Global singleton service instance
route_broker_service = RouteBrokerService()
