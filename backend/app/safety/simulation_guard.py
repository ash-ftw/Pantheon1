"""Safety Model & Simulation Guard — PRD §7.6 (Phase 7).

Mandatory safety validation gate executed before any simulation can be saved or run.
Enforces:
1. Strict in-code allowlist of permitted scenario kinds (FR-6.1)
2. Hard-coded permanent disallowlist of destructive attack classes (FR-6.2)
   - Real malware / rootkits
   - Persistence mechanisms
   - Credential theft against real external accounts
   - Reverse shells / interactive shell injection
   - Botnet / C2 behaviors
   - Ransomware / file destruction
   - Real host privilege escalation
   - Data exfiltration to external destinations
   - Internet-wide scanning & public target enumeration
   - Unrestricted exploit payloads
3. Strict tenant scope validation (FR-6.3)
   - Targets must resolve strictly within the customer's own tenant namespace
   - Public IPs, cloud metadata endpoints, and other tenant namespaces are rejected
4. Transparent rejection reporting & audit logging (FR-6.4, NFR-4.2)
"""

import ipaddress
import re
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any
from urllib.parse import urlparse
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.logging import get_logger
from app.scenarios.schema import ScenarioCategory, ScenarioDefinition, ScenarioTarget
from app.services.audit_service import log_audit_event

logger = get_logger(__name__)


class SafetyViolationType(StrEnum):
    DISALLOWED_CATEGORY = "disallowed_category"
    DISALLOWED_ATTACK_CLASS = "disallowed_attack_class"
    OUT_OF_SCOPE_TARGET = "out_of_scope_target"
    CLOUD_METADATA_ACCESS = "cloud_metadata_access"
    CROSS_TENANT_ACCESS = "cross_tenant_access"
    PERSISTENCE_DETECTED = "persistence_detected"
    REVERSE_SHELL_DETECTED = "reverse_shell_detected"
    RANSOMWARE_DETECTED = "ransomware_detected"
    EXFILTRATION_DETECTED = "exfiltration_detected"
    INTERNET_SCANNING_DETECTED = "internet_scanning_detected"


@dataclass
class SimulationGuardResult:
    """Outcome of Simulation Guard safety evaluation."""

    allowed: bool
    violation_type: SafetyViolationType | None = None
    reason: str | None = None
    violating_elements: list[str] = field(default_factory=list)
    details: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# 1. In-Code Allowlist (FR-6.1)
# ---------------------------------------------------------------------------

PERMITTED_SCENARIO_KINDS: set[ScenarioCategory] = {
    ScenarioCategory.BRUTE_FORCE,
    ScenarioCategory.CREDENTIAL_GUESSING,
    ScenarioCategory.SQLI_RESILIENCE,
    ScenarioCategory.XSS_REFLECTION,
    ScenarioCategory.AUTH_ABUSE,
    ScenarioCategory.BOLA,
    ScenarioCategory.API_ABUSE,
    ScenarioCategory.CACHE_PRESSURE,
    ScenarioCategory.TRAFFIC_FLOOD,
    ScenarioCategory.SERVICE_FAILURE,
    ScenarioCategory.NETWORK_PARTITION,
    ScenarioCategory.RESOURCE_EXHAUSTION,
    ScenarioCategory.MULTI_STAGE_CHAIN,
}


# ---------------------------------------------------------------------------
# 2. Hard-Coded Disallowed Attack Signatures (FR-6.2)
# ---------------------------------------------------------------------------

# Reverse shells and interactive command injection
REVERSE_SHELL_PATTERNS = [
    re.compile(r"/bin/(?:ba)?sh\s+-i", re.IGNORECASE),
    re.compile(r"nc(?:at)?\s+.*-e\s+/bin/", re.IGNORECASE),
    re.compile(r"/dev/tcp/\d+\.\d+\.\d+\.\d+", re.IGNORECASE),
    re.compile(r"mkfifo\s+/tmp/.*cat\s+/tmp/", re.IGNORECASE),
    re.compile(r"python.*socket.*os\.dup2", re.IGNORECASE),
    re.compile(r"bash\s+-c\s+.*>&/dev/tcp", re.IGNORECASE),
    re.compile(r"cmd\.exe\s+/c\s+powershell.*-enc", re.IGNORECASE),
]

# Ransomware and catastrophic file destruction
RANSOMWARE_PATTERNS = [
    re.compile(r"vssadmin\s+delete\s+shadows", re.IGNORECASE),
    re.compile(r"rm\s+-rf\s+/(?:\s|$|\*)", re.IGNORECASE),
    re.compile(r"mkfs\.(?:ext\d|xfs|ntfs)", re.IGNORECASE),
    re.compile(r"wbadmin\s+delete\s+catalog", re.IGNORECASE),
    re.compile(r"cipher\s+/w:", re.IGNORECASE),
    re.compile(r"gpg\s+--symmetric.*--batch", re.IGNORECASE),
]

# Persistence mechanisms
PERSISTENCE_PATTERNS = [
    re.compile(r"/etc/cron\.(?:daily|hourly|d/)", re.IGNORECASE),
    re.compile(r"crontab\s+-[le]", re.IGNORECASE),
    re.compile(r"useradd\s+-[mp]", re.IGNORECASE),
    re.compile(r"net\s+user\s+.*(?:\s+/add)", re.IGNORECASE),
    re.compile(r"authorized_keys", re.IGNORECASE),
    re.compile(r"systemctl\s+enable", re.IGNORECASE),
    re.compile(r"CurrentVersion\\Run", re.IGNORECASE),
]

# Data exfiltration to external webhooks or tunnels
EXFILTRATION_PATTERNS = [
    re.compile(r"webhook\.site", re.IGNORECASE),
    re.compile(r"requestbin\.(?:com|net)", re.IGNORECASE),
    re.compile(r"ngrok(?:\.io|-free\.app)", re.IGNORECASE),
    re.compile(r"pastebin\.com", re.IGNORECASE),
    re.compile(r"transfer\.sh", re.IGNORECASE),
    re.compile(r"burpcollaborator\.net", re.IGNORECASE),
    re.compile(r"oastify\.com", re.IGNORECASE),
]

# Internet-wide scanning / public CIDR sweeps
INTERNET_SCAN_PATTERNS = [
    re.compile(r"0\.0\.0\.0/0"),
    re.compile(r"(?:masscan|zmap|unicornscan)", re.IGNORECASE),
    re.compile(r"--rate\s+\d{5,}", re.IGNORECASE),
]

# Disallowed targets: Cloud Metadata endpoints
PROHIBITED_METADATA_IPS = {
    "169.254.169.254",  # AWS / GCP / Azure IMDS
    "169.254.169.123",  # AWS NTP
    "100.100.100.200",  # Alibaba Cloud IMDS
    "fd00:ec2::254",    # AWS IPv6 IMDS
}

PROHIBITED_METADATA_DOMAINS = {
    "metadata.google.internal",
    "metadata.internal",
    "instance-data",
}


# ---------------------------------------------------------------------------
# Scope Validation (FR-6.3)
# ---------------------------------------------------------------------------


def validate_scenario_scope(
    target: ScenarioTarget,
    tenant_namespace: str | None = None,
) -> tuple[bool, SafetyViolationType | None, str | None]:
    """Validate that the target destination resolves strictly inside the customer tenant environment."""
    raw_service = (target.service or "").strip().lower()
    raw_path = (target.path or "/").strip()

    # Parse potential URL in service or path
    url_target = raw_service if "://" in raw_service else f"http://{raw_service}"
    parsed = urlparse(url_target)
    hostname = parsed.hostname or raw_service

    # Check 1: Cloud Metadata Services
    if hostname in PROHIBITED_METADATA_IPS or hostname in PROHIBITED_METADATA_DOMAINS:
        return (
            False,
            SafetyViolationType.CLOUD_METADATA_ACCESS,
            f"Target destination '{hostname}' is a prohibited cloud provider metadata service (PRD §7.6 FR-6.2/6.3).",
        )

    # Check 2: Check if target is a raw IP address
    try:
        ip_obj = ipaddress.ip_address(hostname)
        # Cloud metadata link-local
        if ip_obj.is_link_local:
            return (
                False,
                SafetyViolationType.CLOUD_METADATA_ACCESS,
                f"Target IP '{hostname}' is link-local / cloud metadata and is permanently forbidden.",
            )
        # Public IP addresses are prohibited (simulations only target tenant workloads)
        if ip_obj.is_global:
            return (
                False,
                SafetyViolationType.OUT_OF_SCOPE_TARGET,
                f"Target destination '{hostname}' is a public internet IP address. Only tenant workloads are permitted (PRD §7.6 FR-6.3).",
            )
    except ValueError:
        # Hostname is a domain/service name
        pass

    # Check 3: External public internet domain names
    if any(hostname.endswith(tld) for tld in (".com", ".net", ".org", ".io", ".dev", ".co", ".ai")):
        # Unless it is an explicit cluster-local service name like .svc.cluster.local
        if not hostname.endswith(".svc.cluster.local"):
            return (
                False,
                SafetyViolationType.OUT_OF_SCOPE_TARGET,
                f"Target domain '{hostname}' resolves outside the customer tenant environment. Public external targets are permanently disallowed (PRD §7.6 FR-6.3).",
            )

    # Check 4: Cross-tenant namespace access
    if tenant_namespace and ".svc.cluster.local" in hostname:
        # Format: <service>.<namespace>.svc.cluster.local
        parts = hostname.split(".")
        if len(parts) >= 2:
            target_ns = parts[1]
            if target_ns != tenant_namespace and target_ns.startswith("tenant-"):
                return (
                    False,
                    SafetyViolationType.CROSS_TENANT_ACCESS,
                    f"Target attempts cross-tenant boundary access into namespace '{target_ns}' (PRD §7.6 FR-6.3, NFR-1.1).",
                )

    # Check 5: Path metadata probe
    if "latest/meta-data" in raw_path or "metadata/v1" in raw_path:
        return (
            False,
            SafetyViolationType.CLOUD_METADATA_ACCESS,
            "Target path attempts cloud metadata harvesting (PRD §7.6 FR-6.2).",
        )

    return True, None, None


# ---------------------------------------------------------------------------
# Deep Payload Inspection (FR-6.2)
# ---------------------------------------------------------------------------


def validate_payload_safety(definition: ScenarioDefinition) -> tuple[bool, SafetyViolationType | None, str | None, list[str]]:
    """Deep inspect parameters, headers, query params, and description for disallowed attack patterns."""
    text_corpus: list[str] = [
        definition.name,
        definition.description,
        definition.payload_category,
        definition.target.path,
    ]

    # Collect headers & query params
    text_corpus.extend(definition.target.headers.values())
    text_corpus.extend(definition.target.query_params.values())

    # Collect parameter values
    def _collect_strings(val: Any) -> None:
        if isinstance(val, str):
            text_corpus.append(val)
        elif isinstance(val, dict):
            for v in val.values():
                _collect_strings(v)
        elif isinstance(val, list):
            for item in val:
                _collect_strings(item)

    _collect_strings(definition.parameters)

    combined_text = "\n".join(text_corpus)

    # 1. Reverse shell detection
    for pat in REVERSE_SHELL_PATTERNS:
        match = pat.search(combined_text)
        if match:
            return (
                False,
                SafetyViolationType.REVERSE_SHELL_DETECTED,
                f"Disallowed reverse shell / interactive TTY execution payload detected: '{match.group(0)}' (PRD §7.6 FR-6.2).",
                [match.group(0)],
            )

    # 2. Ransomware & disk destruction
    for pat in RANSOMWARE_PATTERNS:
        match = pat.search(combined_text)
        if match:
            return (
                False,
                SafetyViolationType.RANSOMWARE_DETECTED,
                f"Disallowed ransomware or destructive file deletion signature detected: '{match.group(0)}' (PRD §7.6 FR-6.2).",
                [match.group(0)],
            )

    # 3. Persistence mechanisms
    for pat in PERSISTENCE_PATTERNS:
        match = pat.search(combined_text)
        if match:
            return (
                False,
                SafetyViolationType.PERSISTENCE_DETECTED,
                f"Disallowed persistence mechanism signature detected: '{match.group(0)}' (PRD §7.6 FR-6.2).",
                [match.group(0)],
            )

    # 4. Data exfiltration to external webhooks
    for pat in EXFILTRATION_PATTERNS:
        match = pat.search(combined_text)
        if match:
            return (
                False,
                SafetyViolationType.EXFILTRATION_DETECTED,
                f"Disallowed external data exfiltration destination detected: '{match.group(0)}' (PRD §7.6 FR-6.2).",
                [match.group(0)],
            )

    # 5. Internet-wide scanning
    for pat in INTERNET_SCAN_PATTERNS:
        match = pat.search(combined_text)
        if match:
            return (
                False,
                SafetyViolationType.INTERNET_SCANNING_DETECTED,
                f"Disallowed internet-wide scanning / indiscriminate CIDR probe detected: '{match.group(0)}' (PRD §7.6 FR-6.2).",
                [match.group(0)],
            )

    return True, None, None, []


# ---------------------------------------------------------------------------
# Primary Execution Gate
# ---------------------------------------------------------------------------


async def check_simulation_safety(
    definition: ScenarioDefinition,
    org_id: UUID | None = None,
    tenant_namespace: str | None = None,
    db: AsyncSession | None = None,
    user_id: UUID | None = None,
) -> SimulationGuardResult:
    """Run all safety verification checks against a scenario definition.

    If safety checks fail and a DB session is provided, automatically logs
    the rejection to the audit log (FR-6.4).
    """
    # 1. Allowlist verification (FR-6.1)
    if definition.category not in PERMITTED_SCENARIO_KINDS:
        res = SimulationGuardResult(
            allowed=False,
            violation_type=SafetyViolationType.DISALLOWED_CATEGORY,
            reason=f"Scenario category '{definition.category}' is not in the permitted simulation allowlist (PRD §7.6 FR-6.1).",
            details={"category": str(definition.category)},
        )
        await _record_rejection_audit(db, org_id, user_id, definition, res)
        return res

    # 2. Scope verification (FR-6.3)
    scope_valid, scope_violation, scope_reason = validate_scenario_scope(
        definition.target, tenant_namespace=tenant_namespace
    )
    if not scope_valid:
        res = SimulationGuardResult(
            allowed=False,
            violation_type=scope_violation,
            reason=scope_reason,
            details={"target": definition.target.model_dump()},
        )
        await _record_rejection_audit(db, org_id, user_id, definition, res)
        return res

    # 3. Deep payload & attack class inspection (FR-6.2)
    payload_valid, payload_violation, payload_reason, matched_items = validate_payload_safety(definition)
    if not payload_valid:
        res = SimulationGuardResult(
            allowed=False,
            violation_type=payload_violation,
            reason=payload_reason,
            violating_elements=matched_items,
            details={"matched_elements": matched_items},
        )
        await _record_rejection_audit(db, org_id, user_id, definition, res)
        return res

    # All safety checks passed
    return SimulationGuardResult(
        allowed=True,
        reason="Scenario conforms to Pantheon Simulation Guard policy and tenant scope boundaries.",
    )


async def _record_rejection_audit(
    db: AsyncSession | None,
    org_id: UUID | None,
    user_id: UUID | None,
    definition: ScenarioDefinition,
    result: SimulationGuardResult,
) -> None:
    """Log safety rejection to audit log (FR-6.4)."""
    logger.warning(
        "simulation_guard_rejection",
        scenario_name=definition.name,
        violation_type=result.violation_type,
        reason=result.reason,
        org_id=str(org_id) if org_id else None,
    )
    if db and org_id and user_id:
        try:
            await log_audit_event(
                db=db,
                org_id=org_id,
                user_id=user_id,
                action="safety.rejection",
                resource_type="scenario",
                resource_id=definition.name[:50],
                details={
                    "name": definition.name,
                    "category": str(definition.category),
                    "violation_type": result.violation_type.value if result.violation_type else "unknown",
                    "reason": result.reason,
                    "target_service": definition.target.service,
                    "target_path": definition.target.path,
                },
            )
        except Exception as e:
            logger.error("safety_rejection_audit_logging_failed", error=str(e))
