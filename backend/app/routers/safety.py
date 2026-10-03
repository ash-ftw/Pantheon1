"""Safety Model & Simulation Guard Router — PRD §7.6 (Phase 7).

Endpoints:
- POST /api/safety/check: Pre-flight safety check against Simulation Guard
- GET /api/safety/policies: Introspect active safety policies and permanently disallowed classes
"""

from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db_session
from app.models import User
from app.safety.simulation_guard import (
    PERMITTED_SCENARIO_KINDS,
    check_simulation_safety,
)
from app.scenarios.schema import ScenarioDefinition
from app.services.auth_service import get_current_user
from app.services.k8s_service import k8s_tenant_service

router = APIRouter(prefix="/api/safety", tags=["safety"])


class SafetyCheckRequest(BaseModel):
    """Scenario safety evaluation payload."""

    definition: ScenarioDefinition
    target_namespace: str | None = None


class SafetyCheckResponse(BaseModel):
    """Simulation Guard evaluation outcome."""

    allowed: bool
    violation_type: str | None = None
    reason: str | None = None
    violating_elements: list[str] = Field(default_factory=list)
    details: dict[str, Any] = Field(default_factory=dict)


class SafetyPoliciesResponse(BaseModel):
    """Platform safety policy specification."""

    permitted_categories: list[str]
    permanently_disallowed_classes: list[str]
    scope_constraints: list[str]
    enforcement_level: str


@router.post("/check", response_model=SafetyCheckResponse)
async def check_scenario_safety(
    payload: SafetyCheckRequest,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> SafetyCheckResponse:
    """Pre-flight check a scenario definition against the Simulation Guard.

    If safety boundaries are breached, logs the violation to the audit log (FR-6.4).
    """
    tenant_ns = payload.target_namespace
    if not tenant_ns and current_user.org_id:
        tenant_ns = k8s_tenant_service.get_namespace_name(current_user.org_id)

    res = await check_simulation_safety(
        definition=payload.definition,
        org_id=current_user.org_id,
        tenant_namespace=tenant_ns,
        db=db,
        user_id=current_user.id,
    )

    return SafetyCheckResponse(
        allowed=res.allowed,
        violation_type=res.violation_type.value if res.violation_type else None,
        reason=res.reason,
        violating_elements=res.violating_elements,
        details=res.details,
    )


@router.get("/policies", response_model=SafetyPoliciesResponse)
async def get_safety_policies() -> SafetyPoliciesResponse:
    """Return the active Simulation Guard safety model policies (PRD §7.6)."""
    return SafetyPoliciesResponse(
        permitted_categories=[c.value for c in PERMITTED_SCENARIO_KINDS],
        permanently_disallowed_classes=[
            "Real malware, rootkits, and Trojan payloads",
            "Persistence mechanisms (crontabs, autoruns, backdoor user creation)",
            "Credential theft against real external accounts or external OAuth providers",
            "Reverse shells and interactive TTY command injection",
            "Botnet and Command-and-Control (C2) beaconing",
            "Ransomware and destructive mass file deletion",
            "Privilege escalation against real host or cluster nodes",
            "Data exfiltration to external webhooks, tunnels, or public endpoints",
            "Internet-wide scanning and indiscriminate CIDR address sweeping",
            "Unrestricted exploit payloads and raw binary shellcode",
        ],
        scope_constraints=[
            "Simulations must target strictly within the customer's assigned tenant namespace",
            "Public internet IP addresses and external domain names are prohibited",
            "Cloud provider metadata endpoints (e.g. 169.254.169.254) are permanently forbidden",
            "Cross-tenant namespace access is blocked at the network and validation layer",
        ],
        enforcement_level="Hard-coded in code with zero bypass path (PRD FR-6.2)",
    )
