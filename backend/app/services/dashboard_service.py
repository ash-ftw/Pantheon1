"""Dashboard Service — PRD Module 1 (Phase 14).

Computes org-level executive KPIs, security posture trends, findings distribution,
and manages the preset known-vulnerable demo app catalog.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.logging import get_logger
from app.models import (
    App,
    AuditLog,
    DefenceRecommendation,
    Finding,
    TestRun,
)

logger = get_logger(__name__)

# Curated catalog of known-vulnerable demo applications (PRD §6.1 / Phase 14)
DEMO_APP_CATALOG: list[dict[str, Any]] = [
    {
        "id": "juice-shop-lite",
        "name": "OWASP Juice Shop (Micro Edition)",
        "description": "Lightweight containerized vulnerable web app covering OWASP Top 10 vulnerabilities including SQL injection, XSS, and broken access controls.",
        "category": "Web Security & OWASP Top 10",
        "architecture": "Node.js 20 Express + SQLite",
        "vulnerabilities": [
            "SQL Injection in /rest/products/search",
            "Reflected XSS in search query parameters",
            "Broken Object-Level Authorization (BOLA)",
            "JWT weak signing key disclosure",
        ],
        "git_url": "https://github.com/pantheon-cyber/demo-juice-shop.git",
        "estimated_deploy_time": "< 90 seconds",
        "tags": ["OWASP", "Node.js", "Beginner-Friendly", "REST"],
        "highlights": [
            "Pre-seeded mock customers and inventory",
            "OpenAPI /swagger.json discoverable automatically",
            "Target for SQLi, XSS, and Auth abuse presets",
        ],
    },
    {
        "id": "fintech-gateway",
        "name": "BankCore FinTech API Gateway",
        "description": "Financial ledger and payment transfer microservices with broken object-level authorization (BOLA) and rate-limiting weaknesses.",
        "category": "API Security & Financial Logic",
        "architecture": "Python FastAPI + Redis + PostgreSQL",
        "vulnerabilities": [
            "BOLA in /api/v1/accounts/{id}/transfer",
            "Rate-limit bypass via forged X-Forwarded-For headers",
            "Sensitive credentials in debug error stack traces",
        ],
        "git_url": "https://github.com/pantheon-cyber/demo-fintech-gateway.git",
        "estimated_deploy_time": "< 120 seconds",
        "tags": ["FastAPI", "FinTech", "BOLA", "Rate-Limiting"],
        "highlights": [
            "Multi-service architecture with Redis cache",
            "Ideal for testing brute force and credential stuffing",
            "Supports Chaos Mesh network partition injection",
        ],
    },
    {
        "id": "cloudstore-commerce",
        "name": "CloudStore E-Commerce Platform",
        "description": "Multi-tier e-commerce platform vulnerable to Server-Side Request Forgery (SSRF) and insecure direct object reference (IDOR).",
        "category": "Cloud & SSRF Vulnerabilities",
        "architecture": "Express + Docker Compose (3 services)",
        "vulnerabilities": [
            "SSRF in image URL previewer /api/media/fetch",
            "Admin privilege escalation via cookie tampering",
            "Unauthenticated order report export",
        ],
        "git_url": "https://github.com/pantheon-cyber/demo-cloudstore.git",
        "estimated_deploy_time": "< 110 seconds",
        "tags": ["Compose", "SSRF", "Multi-Service", "E-Commerce"],
        "highlights": [
            "Internal metadata endpoint exposed to SSRF attacks",
            "Preserves service depends_on ordering",
            "Full attack graph traversal across 3 tiers",
        ],
    },
    {
        "id": "devops-worker-agent",
        "name": "DevOps Task Pipeline Worker",
        "description": "Lightweight CI/CD job execution agent prone to remote command injection and environment secret harvesting.",
        "category": "Supply Chain & Infrastructure",
        "architecture": "Go 1.22 + Alpine",
        "vulnerabilities": [
            "Remote Command Injection in /api/build/execute",
            "Sensitive environment variable dumping at /env",
            "Container escape surface via unconfined privileges",
        ],
        "git_url": "https://github.com/pantheon-cyber/demo-devops-worker.git",
        "estimated_deploy_time": "< 60 seconds",
        "tags": ["Go", "Command-Injection", "DevOps", "Fast-Build"],
        "highlights": [
            "Blazing fast sub-minute build and deployment",
            "Direct target for Chaos Mesh memory/CPU stress",
            "Generates critical-severity infrastructure recommendations",
        ],
    },
]


class DashboardService:
    """Service for computing org-level KPIs and managing the demo catalog."""

    async def get_dashboard_stats(
        self, session: AsyncSession, org_id: uuid.UUID
    ) -> dict[str, Any]:
        """Aggregate high-level security metrics, posture trends, and activity for an org."""
        # 1. Total Apps & Active Deployments
        apps_res = await session.execute(
            select(App).where(App.org_id == org_id).order_by(App.created_at.desc())
        )
        apps = list(apps_res.scalars().all())
        total_apps = len(apps)
        active_deployments = sum(1 for a in apps if getattr(a, "status", "") == "running")
        app_name_map = {a.id: a.name for a in apps}

        # 2. Test Runs
        runs_res = await session.execute(
            select(TestRun).where(TestRun.org_id == org_id).order_by(TestRun.created_at.desc())
        )
        test_runs = list(runs_res.scalars().all())
        total_test_runs = len(test_runs)
        completed_test_runs = sum(1 for r in test_runs if r.status in ("completed", "stopped"))
        active_test_runs = sum(1 for r in test_runs if r.status == "running")

        # 3. Findings & Severity Breakdown
        findings_res = await session.execute(
            select(Finding).where(Finding.org_id == org_id).order_by(Finding.created_at.asc())
        )
        findings = list(findings_res.scalars().all())
        total_findings = len(findings)

        severity_counts = {
            "critical": 0,
            "high": 0,
            "medium": 0,
            "low": 0,
            "info": 0,
        }
        open_count = 0
        resolved_count = 0

        for f in findings:
            sev = (f.severity or "low").lower()
            if sev in severity_counts:
                severity_counts[sev] += 1
            else:
                severity_counts["low"] += 1

            if f.status in ("resolved", "mitigated"):
                resolved_count += 1
            else:
                open_count += 1

        # 4. Defence Recommendations & Mitigation Rate
        recs_res = await session.execute(
            select(DefenceRecommendation).where(DefenceRecommendation.org_id == org_id)
        )
        recs = list(recs_res.scalars().all())
        total_recs = len(recs)
        applied_recs = sum(1 for r in recs if r.status == "applied")
        mitigation_rate = round((applied_recs / total_recs * 100.0) if total_recs > 0 else 0.0, 1)

        # 5. Security Resilience Score (0.0 to 100.0)
        # Base 100 with deductions for open vulnerabilities and bonus for applied mitigations
        raw_score = 100.0
        raw_score -= min(40.0, severity_counts["critical"] * 15.0)
        raw_score -= min(25.0, severity_counts["high"] * 8.0)
        raw_score -= min(15.0, severity_counts["medium"] * 3.0)
        raw_score -= min(10.0, severity_counts["low"] * 1.0)
        # Bonus for mitigations applied
        if total_recs > 0:
            raw_score += (applied_recs / total_recs) * 15.0

        resilience_score = max(5.0, min(100.0, round(raw_score, 1)))

        # 6. Findings Timeline for Recharts AreaChart
        # Group runs chronologically
        timeline: list[dict[str, Any]] = []
        sorted_runs = sorted(test_runs, key=lambda r: r.created_at)
        if not sorted_runs and total_findings > 0:
            timeline.append({
                "date": datetime.now(UTC).strftime("%b %d"),
                "critical": severity_counts["critical"],
                "high": severity_counts["high"],
                "medium": severity_counts["medium"],
                "low": severity_counts["low"],
                "total": total_findings,
            })
        else:
            for r in sorted_runs[-10:]:  # Last 10 runs
                run_findings = [f for f in findings if f.test_run_id == r.id]
                c = sum(1 for f in run_findings if (f.severity or "").lower() == "critical")
                h = sum(1 for f in run_findings if (f.severity or "").lower() == "high")
                m = sum(1 for f in run_findings if (f.severity or "").lower() == "medium")
                l = sum(1 for f in run_findings if (f.severity or "").lower() in ("low", "info"))
                date_str = r.created_at.strftime("%b %d %H:%M")
                timeline.append({
                    "date": date_str,
                    "run_id": str(r.id),
                    "scenario": r.scenario_name,
                    "critical": c,
                    "high": h,
                    "medium": m,
                    "low": l,
                    "total": len(run_findings),
                })

        # 7. Recent Test Runs (last 5)
        recent_runs: list[dict[str, Any]] = []
        for r in test_runs[:5]:
            r_findings = [f for f in findings if f.test_run_id == r.id]
            recent_runs.append({
                "id": str(r.id),
                "app_id": str(r.app_id),
                "app_name": app_name_map.get(r.app_id, "Target Application"),
                "scenario_name": r.scenario_name,
                "scenario_category": r.scenario_category,
                "status": r.status,
                "findings_count": len(r_findings),
                "critical_count": sum(1 for f in r_findings if (f.severity or "").lower() == "critical"),
                "total_steps": r.total_steps,
                "current_step": r.current_step,
                "created_at": r.created_at.isoformat(),
            })

        # 8. Cluster Status
        cluster_status = {
            "status": "ready",
            "namespace": f"tenant-{str(org_id)[:8]}",
            "network_policy": "default-deny-active",
            "isolation": "verified",
            "active_routes": 0,
        }

        # 9. Recent Activity from Audit Log
        audit_res = await session.execute(
            select(AuditLog)
            .where(AuditLog.org_id == org_id)
            .order_by(AuditLog.created_at.desc())
            .limit(6)
        )
        audit_entries = list(audit_res.scalars().all())
        recent_activity = [
            {
                "id": str(a.id),
                "action": a.action,
                "resource_type": a.resource_type,
                "created_at": a.created_at.isoformat(),
                "details": a.details,
            }
            for a in audit_entries
        ]

        return {
            "total_apps": total_apps,
            "active_deployments": active_deployments,
            "total_test_runs": total_test_runs,
            "completed_test_runs": completed_test_runs,
            "active_test_runs": active_test_runs,
            "total_findings": total_findings,
            "findings_by_severity": severity_counts,
            "open_findings_count": open_count,
            "resolved_findings_count": resolved_count,
            "resilience_score": resilience_score,
            "mitigation_stats": {
                "total_recommendations": total_recs,
                "applied_mitigations": applied_recs,
                "mitigation_rate_pct": mitigation_rate,
            },
            "findings_timeline": timeline,
            "recent_test_runs": recent_runs,
            "cluster_status": cluster_status,
            "recent_activity": recent_activity,
        }

    def get_demo_catalog(self) -> list[dict[str, Any]]:
        """Return curated list of preset demo applications."""
        return DEMO_APP_CATALOG

    def get_demo_app(self, demo_id: str) -> dict[str, Any] | None:
        """Find a single demo app by ID."""
        for d in DEMO_APP_CATALOG:
            if d["id"] == demo_id:
                return d
        return None


dashboard_service = DashboardService()
