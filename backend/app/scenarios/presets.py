"""Preset Scenario Catalog — PRD Module 7 (Phase 6).

Contains pre-configured simulation definitions across all 13 required categories:
1. brute_force
2. credential_guessing
3. sqli_resilience
4. xss_reflection
5. auth_abuse
6. bola (Broken Object Level Authorization)
7. api_abuse
8. cache_pressure
9. traffic_flood
10. service_failure
11. network_partition
12. resource_exhaustion
13. multi_stage_chain

Each preset is strictly typed as a ScenarioDefinition.
"""

from app.scenarios.schema import (
    EstimatedImpact,
    ScenarioCategory,
    ScenarioDefinition,
    ScenarioSource,
    ScenarioTarget,
)

PRESET_SCENARIOS: list[ScenarioDefinition] = [
    # 1. Brute Force
    ScenarioDefinition(
        name="High-Rate Authentication Brute Force",
        description="Emits rapid credential verification requests against the login endpoint to test anti-automation and lockouts.",
        category=ScenarioCategory.BRUTE_FORCE,
        target=ScenarioTarget(path="/api/auth/login", port=8080),
        method="POST",
        payload_category="auth_brute_force",
        concurrency=50,
        duration=30,
        expected_signals=["http_429_rate_limited", "account_temporary_lockout", "audit_login_failed"],
        parameters={
            "rate_per_second": 100,
            "username_pool": ["admin", "root", "test", "demo"],
            "password_list_size": 500,
        },
        estimated_impact=EstimatedImpact.MEDIUM,
        estimated_duration_seconds=30,
        source=ScenarioSource.PRESET,
        tags=["auth", "brute-force", "owasp-top-10"],
    ),
    # 2. Credential Guessing
    ScenarioDefinition(
        name="Common Password Dictionary Stuffing",
        description="Tests top 100 most common enterprise passwords against exposed authentication endpoints.",
        category=ScenarioCategory.CREDENTIAL_GUESSING,
        target=ScenarioTarget(path="/api/auth/token", port=8080),
        method="POST",
        payload_category="dictionary_stuffing",
        concurrency=20,
        duration=45,
        expected_signals=["http_401_unauthorized", "failed_attempt_logged", "ip_rate_limited"],
        parameters={
            "dictionary_name": "top_100_enterprise_passwords",
            "check_exponential_backoff": True,
        },
        estimated_impact=EstimatedImpact.LOW,
        estimated_duration_seconds=45,
        source=ScenarioSource.PRESET,
        tags=["auth", "credentials", "dictionary"],
    ),
    # 3. SQLi Resilience
    ScenarioDefinition(
        name="SQL Injection Syntax & Tautology Probing",
        description="Injects non-destructive boolean-based and tautological SQL syntax payloads into search and query parameters.",
        category=ScenarioCategory.SQLI_RESILIENCE,
        target=ScenarioTarget(path="/api/search", port=8080),
        method="GET",
        payload_category="sqli_probes",
        concurrency=15,
        duration=30,
        expected_signals=["http_400_bad_request", "waf_sqli_detected", "parameter_sanitized"],
        parameters={
            "payloads": [
                "' OR '1'='1",
                "' UNION SELECT NULL--",
                "admin'--",
                "1; SELECT 1",
            ],
            "target_param": "query",
        },
        estimated_impact=EstimatedImpact.LOW,
        estimated_duration_seconds=30,
        source=ScenarioSource.PRESET,
        tags=["injection", "sqli", "data-protection"],
    ),
    # 4. XSS Reflection
    ScenarioDefinition(
        name="Reflected Cross-Site Scripting (XSS) Sanitization",
        description="Probes API inputs with script tags and SVG event handlers to verify HTML entity escaping and CSP enforcement.",
        category=ScenarioCategory.XSS_REFLECTION,
        target=ScenarioTarget(path="/api/items", port=8080),
        method="GET",
        payload_category="xss_vectors",
        concurrency=10,
        duration=25,
        expected_signals=["csp_violation_blocked", "html_escaped_in_response", "http_400_rejected"],
        parameters={
            "payloads": [
                "<script>alert(1)</script>",
                "<img src=x onerror=alert(1)>",
                "javascript:void(0)",
            ],
            "inspect_response_headers": ["Content-Security-Policy", "X-XSS-Protection"],
        },
        estimated_impact=EstimatedImpact.LOW,
        estimated_duration_seconds=25,
        source=ScenarioSource.PRESET,
        tags=["injection", "xss", "sanitization"],
    ),
    # 5. Auth Abuse
    ScenarioDefinition(
        name="JWT Token Tampering & Missing Authorization Probe",
        description="Submits expired tokens, invalid signature algorithms (none), and manipulated claims to protected endpoints.",
        category=ScenarioCategory.AUTH_ABUSE,
        target=ScenarioTarget(path="/api/admin/dashboard", port=8080),
        method="GET",
        payload_category="jwt_manipulation",
        concurrency=15,
        duration=20,
        expected_signals=["http_401_token_expired", "http_403_signature_invalid", "auth_bypass_prevented"],
        parameters={
            "tamper_modes": ["alg_none", "expired_timestamp", "fake_issuer", "tampered_role"],
        },
        estimated_impact=EstimatedImpact.LOW,
        estimated_duration_seconds=20,
        source=ScenarioSource.PRESET,
        tags=["auth", "jwt", "tokens"],
    ),
    # 6. BOLA
    ScenarioDefinition(
        name="BOLA / IDOR Cross-Tenant Object Access",
        description="Attempts to access sequential object identifiers belonging to other tenants to verify object-level access controls.",
        category=ScenarioCategory.BOLA,
        target=ScenarioTarget(path="/api/users/profile", port=8080),
        method="GET",
        payload_category="idor_enumeration",
        concurrency=20,
        duration=30,
        expected_signals=["http_403_forbidden", "tenant_boundary_enforced", "unauthorized_access_logged"],
        parameters={
            "id_step_range": [1, 50],
            "uuid_tampering": True,
        },
        estimated_impact=EstimatedImpact.LOW,
        estimated_duration_seconds=30,
        source=ScenarioSource.PRESET,
        tags=["api-security", "bola", "idor", "multi-tenant"],
    ),
    # 7. API Abuse
    ScenarioDefinition(
        name="Aggressive API Rate Limit Exhaustion",
        description="Fires continuous request bursts exceeding standard token-bucket allowances to verify 429 response enforcement.",
        category=ScenarioCategory.API_ABUSE,
        target=ScenarioTarget(path="/api/public/data", port=8080),
        method="GET",
        payload_category="rate_limit_surge",
        concurrency=100,
        duration=30,
        expected_signals=["http_429_too_many_requests", "retry_after_header_returned"],
        parameters={
            "burst_size": 250,
            "target_rpm": 3000,
        },
        estimated_impact=EstimatedImpact.MEDIUM,
        estimated_duration_seconds=30,
        source=ScenarioSource.PRESET,
        tags=["rate-limiting", "api-abuse", "resilience"],
    ),
    # 8. Cache Pressure
    ScenarioDefinition(
        name="Cache-Busting Query String Randomization",
        description="Sends requests with unique cache-busting query strings to force cache misses and measure backend origin stress.",
        category=ScenarioCategory.CACHE_PRESSURE,
        target=ScenarioTarget(path="/api/catalog", port=8080),
        method="GET",
        payload_category="cache_bypass",
        concurrency=60,
        duration=40,
        expected_signals=["cache_miss_ratio_increase", "origin_latency_within_sla"],
        parameters={
            "random_query_keys": ["_cb", "nocache", "v", "random_seed"],
        },
        estimated_impact=EstimatedImpact.MEDIUM,
        estimated_duration_seconds=40,
        source=ScenarioSource.PRESET,
        tags=["performance", "caching", "origin-protection"],
    ),
    # 9. Traffic Flood
    ScenarioDefinition(
        name="High-Concurrency Layer 7 Traffic Surge",
        description="Ramps up concurrent connections to evaluate ingress throttling, worker pool exhaustion, and connection pooling.",
        category=ScenarioCategory.TRAFFIC_FLOOD,
        target=ScenarioTarget(path="/", port=8080),
        method="GET",
        payload_category="l7_flood",
        concurrency=250,
        duration=60,
        expected_signals=["active_connections_stabilized", "http_503_or_queueing", "p99_latency_spiked"],
        parameters={
            "ramp_up_seconds": 15,
            "sustained_seconds": 45,
        },
        estimated_impact=EstimatedImpact.HIGH,
        estimated_duration_seconds=60,
        source=ScenarioSource.PRESET,
        tags=["dos", "traffic-flood", "scale", "concurrency"],
    ),
    # 10. Service Failure (Chaos)
    ScenarioDefinition(
        name="Container Pod Termination & Auto-Heal Chaos",
        description="Injects sudden pod restarts via Chaos Mesh PodChaos to measure cluster self-healing and service mesh rerouting.",
        category=ScenarioCategory.SERVICE_FAILURE,
        target=ScenarioTarget(service="app-workload", path="/healthz", port=8080),
        method="POD_KILL",
        payload_category="chaos_pod_kill",
        concurrency=1,
        duration=60,
        expected_signals=["pod_crashloop_detected", "replacement_pod_ready", "zero_downtime_failover"],
        parameters={
            "chaos_type": "PodChaos",
            "action": "pod-kill",
            "grace_period_seconds": 0,
        },
        estimated_impact=EstimatedImpact.HIGH,
        estimated_duration_seconds=60,
        source=ScenarioSource.PRESET,
        tags=["chaos", "k8s", "self-healing", "reliability"],
    ),
    # 11. Network Partition (Chaos)
    ScenarioDefinition(
        name="Cross-Service Network Latency & Packet Loss Injection",
        description="Introduces 250ms synthetic latency and 10% packet drop via NetworkChaos to test client timeouts and circuit breakers.",
        category=ScenarioCategory.NETWORK_PARTITION,
        target=ScenarioTarget(service="app-workload", path="/api", port=8080),
        method="NETWORK_DELAY",
        payload_category="chaos_network_latency",
        concurrency=5,
        duration=45,
        expected_signals=["circuit_breaker_opened", "graceful_fallback_returned", "timeout_error_contained"],
        parameters={
            "chaos_type": "NetworkChaos",
            "delay_ms": 250,
            "jitter_ms": 50,
            "loss_percentage": 10,
        },
        estimated_impact=EstimatedImpact.HIGH,
        estimated_duration_seconds=45,
        source=ScenarioSource.PRESET,
        tags=["chaos", "network", "resilience", "circuit-breaker"],
    ),
    # 12. Resource Exhaustion (Chaos)
    ScenarioDefinition(
        name="Container CPU & Memory Starvation Stress",
        description="Applies simulated CPU throttling and 90% memory limit consumption to verify OOM handling and horizontal pod autoscaling.",
        category=ScenarioCategory.RESOURCE_EXHAUSTION,
        target=ScenarioTarget(service="app-workload", path="/", port=8080),
        method="CPU_STRESS",
        payload_category="chaos_stress",
        concurrency=4,
        duration=50,
        expected_signals=["cpu_throttling_reported", "hpa_scale_event_triggered", "no_host_node_eviction"],
        parameters={
            "chaos_type": "StressChaos",
            "cpu_workers": 2,
            "memory_percent": "80%",
        },
        estimated_impact=EstimatedImpact.HIGH,
        estimated_duration_seconds=50,
        source=ScenarioSource.PRESET,
        tags=["chaos", "cpu", "memory", "hpa", "autoscaling"],
    ),
    # 13. Multi-Stage Chain
    ScenarioDefinition(
        name="Chained Reconnaissance to Privilege Escalation Probe",
        description="Executes a 3-step sequence: public endpoint enumeration, test token acquisition, followed by administrative endpoint probing.",
        category=ScenarioCategory.MULTI_STAGE_CHAIN,
        target=ScenarioTarget(path="/api", port=8080),
        method="CHAINED_HTTP",
        payload_category="multi_stage_sequence",
        concurrency=10,
        duration=60,
        expected_signals=["recon_detected", "step_1_passed", "step_2_blocked_at_privilege_boundary"],
        parameters={
            "stages": [
                {"step": 1, "action": "GET /openapi.json", "expect": 200},
                {"step": 2, "action": "POST /api/auth/token", "expect": [200, 401]},
                {"step": 3, "action": "GET /api/admin/users", "expect": 403},
            ]
        },
        estimated_impact=EstimatedImpact.MEDIUM,
        estimated_duration_seconds=60,
        source=ScenarioSource.PRESET,
        tags=["chain", "multi-step", "killchain", "advanced"],
    ),
]


def get_all_presets() -> list[ScenarioDefinition]:
    """Return all 13 preset scenario definitions."""
    return list(PRESET_SCENARIOS)


def get_preset_by_category(category: ScenarioCategory) -> list[ScenarioDefinition]:
    """Filter preset scenarios by category."""
    return [p for p in PRESET_SCENARIOS if p.category == category]
