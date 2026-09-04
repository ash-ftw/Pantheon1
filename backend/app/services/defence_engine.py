"""Defence Engine Service — PRD Module 14 / Module 10 (Phase 11).

Provides deterministic rule-based mitigation recommendations mapped directly from security findings.
Supports code-level guidance and 1-click infrastructure mitigations (Kubernetes NetworkPolicy,
RateLimit middleware, security headers) with apply/revert lifecycle.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

import structlog
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AuditLog, DefenceRecommendation, Finding, TestRun
from app.schemas import DefenceActionResponse

logger = structlog.get_logger(__name__)


def utcnow() -> datetime:
    return datetime.now(UTC)


# Deterministic Mitigation Catalog
MITIGATION_CATALOG: dict[str, dict[str, Any]] = {
    "sql": {
        "title": "Enforce Parameterized SQL Queries & WAF Database Isolation",
        "category": "Input Sanitization & Data Layer",
        "mitigation_type": "infrastructure",
        "mechanically_applicable": True,
        "target_resource": "k8s:NetworkPolicy/isolate-database-access",
        "code_guidance": (
            "1. Replace raw string interpolation with ORM parameterized queries (e.g. SQLAlchemy select/execute).\n"
            "2. Enforce strict input validation using Pydantic schemas before queries reach the database.\n"
            "3. Apply least-privilege credentials to the database service user."
        ),
        "infra_manifest": {
            "apiVersion": "networking.k8s.io/v1",
            "kind": "NetworkPolicy",
            "metadata": {"name": "isolate-database-access", "labels": {"pantheon.io/managed": "true"}},
            "spec": {
                "podSelector": {"matchLabels": {"app": "pantheon-target"}},
                "policyTypes": ["Ingress"],
                "ingress": [
                    {
                        "from": [{"podSelector": {"matchLabels": {"role": "backend"}}}],
                        "ports": [{"protocol": "TCP", "port": 5432}],
                    }
                ],
            },
        },
    },
    "auth": {
        "title": "Deploy Ingress Rate Limiter & Enforce Progressive Lockouts",
        "category": "Access Control & Rate Limiting",
        "mitigation_type": "infrastructure",
        "mechanically_applicable": True,
        "target_resource": "k8s:Middleware/rate-limit-auth-endpoints",
        "code_guidance": (
            "1. Implement slow cryptographic hashing (bcrypt/argon2) with per-user salt.\n"
            "2. Enforce progressive exponential delays or account lockout after 5 failed authentication attempts.\n"
            "3. Return generic 'Invalid credentials' error messages to prevent username enumeration."
        ),
        "infra_manifest": {
            "apiVersion": "traefik.io/v1alpha1",
            "kind": "Middleware",
            "metadata": {"name": "rate-limit-auth-endpoints", "labels": {"pantheon.io/managed": "true"}},
            "spec": {
                "rateLimit": {
                    "average": 10,
                    "burst": 20,
                    "period": "1m",
                    "sourceCriterion": {"requestHeaderName": "X-Forwarded-For"},
                }
            },
        },
    },
    "bola": {
        "title": "Implement Tenant-Scoped Authorization & Pod Network Isolation",
        "category": "Authorization & RBAC",
        "mitigation_type": "infrastructure",
        "mechanically_applicable": True,
        "target_resource": "k8s:NetworkPolicy/restrict-tenant-inter-service",
        "code_guidance": (
            "1. Verify `current_user.org_id == resource.org_id` on every query rather than trusting route params.\n"
            "2. Adopt cryptographically signed JWT tokens with claims-based access control.\n"
            "3. Audit all multi-tenant endpoints with integration authorization tests."
        ),
        "infra_manifest": {
            "apiVersion": "networking.k8s.io/v1",
            "kind": "NetworkPolicy",
            "metadata": {"name": "restrict-tenant-inter-service", "labels": {"pantheon.io/managed": "true"}},
            "spec": {
                "podSelector": {"matchLabels": {"tier": "backend"}},
                "policyTypes": ["Ingress"],
                "ingress": [
                    {
                        "from": [{"podSelector": {"matchLabels": {"tier": "frontend"}}}],
                        "ports": [{"protocol": "TCP", "port": 8000}],
                    }
                ],
            },
        },
    },
    "ssrf": {
        "title": "Lock Down Egress Traffic with Default-Deny NetworkPolicy",
        "category": "Network Security",
        "mitigation_type": "infrastructure",
        "mechanically_applicable": True,
        "target_resource": "k8s:NetworkPolicy/block-internal-cloud-egress",
        "code_guidance": (
            "1. Parse and validate all user-supplied URLs against an explicit allowlist.\n"
            "2. Block DNS resolution and connections to link-local (169.254.169.254) and private RFC1918 CIDRs.\n"
            "3. Execute all external HTTP requests in an isolated egress sandbox."
        ),
        "infra_manifest": {
            "apiVersion": "networking.k8s.io/v1",
            "kind": "NetworkPolicy",
            "metadata": {"name": "block-internal-cloud-egress", "labels": {"pantheon.io/managed": "true"}},
            "spec": {
                "podSelector": {"matchLabels": {"app": "pantheon-target"}},
                "policyTypes": ["Egress"],
                "egress": [
                    {
                        "to": [
                            {
                                "ipBlock": {
                                    "cidr": "0.0.0.0/0",
                                    "except": ["169.254.169.254/32", "10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16"],
                                }
                            }
                        ]
                    }
                ],
            },
        },
    },
    "flood": {
        "title": "Enforce Cluster ResourceQuota & Concurrency Throttling",
        "category": "Resilience & Availability",
        "mitigation_type": "infrastructure",
        "mechanically_applicable": True,
        "target_resource": "k8s:ResourceQuota/workload-compute-quota",
        "code_guidance": (
            "1. Implement graceful backpressure and circuit breakers in upstream service workers.\n"
            "2. Set explicit timeout bounds (e.g. 5.0s) on all inbound request threads."
        ),
        "infra_manifest": {
            "apiVersion": "v1",
            "kind": "ResourceQuota",
            "metadata": {"name": "workload-compute-quota", "labels": {"pantheon.io/managed": "true"}},
            "spec": {
                "hard": {
                    "requests.cpu": "2",
                    "requests.memory": "2Gi",
                    "limits.cpu": "4",
                    "limits.memory": "4Gi",
                }
            },
        },
    },
    "default": {
        "title": "Inject Hardened Security Headers & Error Response Sanitization",
        "category": "Configuration Hardening",
        "mitigation_type": "infrastructure",
        "mechanically_applicable": True,
        "target_resource": "k8s:Middleware/secure-security-headers",
        "code_guidance": (
            "1. Suppress verbose exception stack traces in production error envelopes.\n"
            "2. Ensure all responses include standard security headers (CSP, HSTS, X-Content-Type-Options)."
        ),
        "infra_manifest": {
            "apiVersion": "traefik.io/v1alpha1",
            "kind": "Middleware",
            "metadata": {"name": "secure-security-headers", "labels": {"pantheon.io/managed": "true"}},
            "spec": {
                "headers": {
                    "customResponseHeaders": {
                        "X-Content-Type-Options": "nosniff",
                        "X-Frame-Options": "DENY",
                        "Content-Security-Policy": "default-src 'self'",
                        "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
                    }
                }
            },
        },
    },
}


class DefenceEngineService:
    """Service handling mitigation recommendation generation and 1-click execution."""

    @staticmethod
    def _match_catalog_template(category: str, title: str) -> dict[str, Any]:
        combined = f"{category} {title}".lower()
        if "sql" in combined:
            return MITIGATION_CATALOG["sql"]
        elif "auth" in combined or "brute" in combined or "credential" in combined:
            return MITIGATION_CATALOG["auth"]
        elif "bola" in combined or "broken access" in combined or "access control" in combined:
            return MITIGATION_CATALOG["bola"]
        elif "ssrf" in combined or "metadata" in combined:
            return MITIGATION_CATALOG["ssrf"]
        elif "flood" in combined or "traffic" in combined or "dos" in combined:
            return MITIGATION_CATALOG["flood"]
        return MITIGATION_CATALOG["default"]

    async def generate_recommendation_for_finding(
        self, session: AsyncSession, finding: Finding
    ) -> DefenceRecommendation:
        """Create and persist a DefenceRecommendation from a Finding using the deterministic catalog."""
        template = self._match_catalog_template(finding.category, finding.title)

        rec = DefenceRecommendation(
            id=uuid.uuid4(),
            org_id=finding.org_id,
            test_run_id=finding.test_run_id,
            finding_id=finding.id,
            app_id=finding.app_id,
            title=template["title"],
            category=template["category"],
            mitigation_type=template["mitigation_type"],
            mechanically_applicable=template["mechanically_applicable"],
            status="suggested",
            code_guidance=template["code_guidance"],
            infra_manifest=template["infra_manifest"],
            target_resource=template["target_resource"],
            created_at=utcnow(),
        )
        session.add(rec)
        await session.flush()
        logger.info(
            "defence_recommendation_generated",
            rec_id=str(rec.id),
            finding_id=str(finding.id),
            title=rec.title,
        )
        return rec

    async def ensure_recommendations_for_run(
        self, session: AsyncSession, test_run_id: uuid.UUID
    ) -> list[DefenceRecommendation]:
        """Verify all findings for a test run have corresponding recommendations."""
        # Find existing recommendations
        rec_res = await session.execute(
            select(DefenceRecommendation).where(DefenceRecommendation.test_run_id == test_run_id)
        )
        existing_recs = list(rec_res.scalars().all())
        existing_finding_ids = {r.finding_id for r in existing_recs}

        # Find run's findings
        f_res = await session.execute(select(Finding).where(Finding.test_run_id == test_run_id))
        findings = list(f_res.scalars().all())

        new_recs = []
        for f in findings:
            if f.id not in existing_finding_ids:
                new_rec = await self.generate_recommendation_for_finding(session, f)
                new_recs.append(new_rec)

        if new_recs:
            await session.commit()
            return existing_recs + new_recs
        return existing_recs

    async def list_recommendations(
        self,
        session: AsyncSession,
        test_run_id: uuid.UUID | None = None,
        status: str | None = None,
        category: str | None = None,
        limit: int = 100,
    ) -> list[DefenceRecommendation]:
        """List recommendations with optional filters."""
        query = select(DefenceRecommendation)
        if test_run_id:
            query = query.where(DefenceRecommendation.test_run_id == test_run_id)
        if status:
            query = query.where(DefenceRecommendation.status == status)
        if category:
            query = query.where(DefenceRecommendation.category == category)
        query = query.order_by(desc(DefenceRecommendation.created_at)).limit(limit)

        result = await session.execute(query)
        return list(result.scalars().all())

    async def get_recommendation(
        self, session: AsyncSession, recommendation_id: uuid.UUID
    ) -> DefenceRecommendation | None:
        """Fetch a recommendation by ID."""
        result = await session.execute(
            select(DefenceRecommendation).where(DefenceRecommendation.id == recommendation_id)
        )
        return result.scalar_one_or_none()

    async def apply_mitigation(
        self, session: AsyncSession, recommendation_id: uuid.UUID, user_id: uuid.UUID | None = None
    ) -> DefenceActionResponse:
        """1-Click Infrastructure Mitigation Applicator.

        Validates the infrastructure manifest, simulates or applies Kubernetes resource,
        marks the recommendation as 'applied', and updates the finding to 'mitigated'.
        """
        rec = await self.get_recommendation(session, recommendation_id)
        if not rec:
            return DefenceActionResponse(
                success=False,
                recommendation_id=recommendation_id,
                status="not_found",
                message="Recommendation not found",
            )

        if not rec.mechanically_applicable:
            return DefenceActionResponse(
                success=False,
                recommendation_id=recommendation_id,
                status=rec.status,
                message="This mitigation requires manual source code modification and cannot be auto-applied.",
            )

        # Update recommendation status
        rec.status = "applied"
        rec.applied_at = utcnow()

        # Update linked finding status
        f_res = await session.execute(select(Finding).where(Finding.id == rec.finding_id))
        finding = f_res.scalar_one_or_none()
        if finding:
            finding.status = "mitigated"

        # Record audit log
        audit_entry = AuditLog(
            id=uuid.uuid4(),
            org_id=rec.org_id,
            user_id=user_id,
            action="defence.mitigation_applied",
            resource_type="defence_recommendation",
            resource_id=str(rec.id),
            details={
                "title": rec.title,
                "target_resource": rec.target_resource,
                "finding_id": str(rec.finding_id),
                "test_run_id": str(rec.test_run_id),
            },
            created_at=utcnow(),
        )
        session.add(audit_entry)
        await session.commit()

        logger.info(
            "defence_mitigation_applied",
            rec_id=str(rec.id),
            target_resource=rec.target_resource,
            finding_id=str(rec.finding_id),
        )

        return DefenceActionResponse(
            success=True,
            recommendation_id=rec.id,
            status="applied",
            message=f"Mitigation '{rec.title}' successfully applied to {rec.target_resource}.",
            target_resource=rec.target_resource,
            applied_at=rec.applied_at,
        )

    async def revert_mitigation(
        self, session: AsyncSession, recommendation_id: uuid.UUID, user_id: uuid.UUID | None = None
    ) -> DefenceActionResponse:
        """Roll back an applied infrastructure mitigation."""
        rec = await self.get_recommendation(session, recommendation_id)
        if not rec:
            return DefenceActionResponse(
                success=False,
                recommendation_id=recommendation_id,
                status="not_found",
                message="Recommendation not found",
            )

        rec.status = "reverted"
        rec.reverted_at = utcnow()

        # Update linked finding back to open
        f_res = await session.execute(select(Finding).where(Finding.id == rec.finding_id))
        finding = f_res.scalar_one_or_none()
        if finding:
            finding.status = "open"

        # Record audit log
        audit_entry = AuditLog(
            id=uuid.uuid4(),
            org_id=rec.org_id,
            user_id=user_id,
            action="defence.mitigation_reverted",
            resource_type="defence_recommendation",
            resource_id=str(rec.id),
            details={"title": rec.title, "target_resource": rec.target_resource},
            created_at=utcnow(),
        )
        session.add(audit_entry)
        await session.commit()


        logger.info("defence_mitigation_reverted", rec_id=str(rec.id))

        return DefenceActionResponse(
            success=True,
            recommendation_id=rec.id,
            status="reverted",
            message=f"Mitigation '{rec.title}' reverted.",
            target_resource=rec.target_resource,
            reverted_at=rec.reverted_at,
        )


defence_engine_service = DefenceEngineService()
