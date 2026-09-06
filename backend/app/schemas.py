import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field


# --- Auth Schemas ---
class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    full_name: str = Field(min_length=2, max_length=255)
    org_name: str = Field(min_length=2, max_length=255)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in_seconds: int


class UserRead(BaseModel):
    id: uuid.UUID
    email: EmailStr
    full_name: str
    org_id: uuid.UUID | None = None
    role: str
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- Org Schemas ---
class OrgCreate(BaseModel):
    name: str = Field(min_length=2, max_length=255)


class OrgRead(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    plan: str
    cluster_status: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class OrgMemberRead(BaseModel):
    id: uuid.UUID
    org_id: uuid.UUID
    user_id: uuid.UUID
    role: str
    joined_at: datetime
    user_email: str | None = None
    user_name: str | None = None

    model_config = ConfigDict(from_attributes=True)


class OrgMemberUpdate(BaseModel):
    role: str = Field(pattern="^(admin|tester|viewer)$")


class InvitationCreate(BaseModel):
    email: EmailStr
    role: str = Field(default="tester", pattern="^(admin|tester|viewer)$")


class InvitationRead(BaseModel):
    id: uuid.UUID
    org_id: uuid.UUID
    email: EmailStr
    role: str
    token: str
    expires_at: datetime
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class InvitationAccept(BaseModel):
    token: str
    password: str = Field(min_length=8)
    full_name: str = Field(min_length=2, max_length=255)


# --- Audit Log Schemas ---
class AuditLogRead(BaseModel):
    id: uuid.UUID
    org_id: uuid.UUID
    user_id: uuid.UUID | None = None
    user_email: str | None = None
    action: str
    resource_type: str
    resource_id: str | None = None
    details: dict[str, Any]
    ip_address: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- Discovery Schemas ---


class DiscoveryTargetAnalysisRequest(BaseModel):
    app_id: uuid.UUID


class DiscoveryTargetAnalysisResponse(BaseModel):
    app_id: str
    org_id: str
    namespace: str
    discovery_status: str = "pending"
    language: str | None = None
    framework: str | None = None
    exposed_ports: list[int] = []
    detected_db: str | None = None
    db_environment_variables: list[str] = []
    auth_mechanisms: list[str] = []
    auth_env_variables: list[str] = []
    confidence: str = "low"  # high | medium | low
    confidence_basis: str = ""


class DiscoveryEndpointsRequest(BaseModel):
    app_id: uuid.UUID


class DiscoveryEndpointItem(BaseModel):
    path: str
    method: str
    summary: str = ""
    description: str = ""
    classification: str = "public"
    confidence: str = "medium"
    confidence_basis: str = ""
    parameters: list[dict[str, Any]] = []


class DiscoveryEndpointsResponse(BaseModel):
    app_id: str
    org_id: str
    namespace: str
    discovery_status: str = "pending"
    specs_found: list[str] = []
    endpoints: list[DiscoveryEndpointItem] = []
    classification: dict[str, list[DiscoveryEndpointItem]] = {
        "public": [],
        "likely_admin": [],
        "likely_auth": [],
        "upload": [],
        "search": [],
    }


class AppDiscoverySummary(BaseModel):
    """Compact discovery summary for the app list/detail views."""

    discovery_status: str = "pending"
    language: str | None = None
    framework: str | None = None
    exposed_ports: list[int] = []
    detected_db: str | None = None
    endpoint_count: int = 0
    classification_counts: dict[str, int] = {}


# --- Infrastructure Schemas ---
class InfrastructureRead(BaseModel):
    namespace: str
    status: str
    k8s_connected: bool
    quota: dict[str, Any]
    limit_range: dict[str, Any] = Field(
        default_factory=lambda: {"default_cpu": "100m", "default_memory": "128Mi"}
    )
    deployments: list[dict[str, Any]]
    services: list[dict[str, Any]]
    pods: list[dict[str, Any]]
    network_policies: list[dict[str, Any]]


# --- Phase 9: Test Run & Finding Schemas (PRD Module 10) ---
class FindingRead(BaseModel):
    id: uuid.UUID
    org_id: uuid.UUID
    test_run_id: uuid.UUID
    app_id: uuid.UUID
    title: str
    severity: str
    category: str
    cwe_id: str | None = None
    owasp_category: str | None = None
    description: str
    evidence: dict[str, Any] = Field(default_factory=dict)
    remediation_guidance: str
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TestRunCreate(BaseModel):
    app_id: uuid.UUID
    scenario_id: uuid.UUID | None = None
    scenario_name: str | None = None
    scenario_category: str | None = None
    parameters: dict[str, Any] = Field(default_factory=dict)


class TestRunRead(BaseModel):
    id: uuid.UUID
    org_id: uuid.UUID
    app_id: uuid.UUID
    scenario_id: uuid.UUID | None = None
    scenario_name: str
    scenario_category: str
    route_id: uuid.UUID | None = None
    status: str
    current_step: int
    total_steps: int
    current_step_name: str | None = None
    parameters: dict[str, Any] = Field(default_factory=dict)
    metrics: dict[str, Any] = Field(default_factory=dict)
    logs: list[dict[str, Any]] = Field(default_factory=list)
    error_message: str | None = None
    findings: list[FindingRead] = Field(default_factory=list)
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class TestRunStopRequest(BaseModel):
    reason: str = "manual_kill_switch"


# --- Phase 11: Defence Engine & Observability Schemas (PRD Modules 13 & 14) ---
class DefenceRecommendationRead(BaseModel):
    id: uuid.UUID
    org_id: uuid.UUID
    test_run_id: uuid.UUID
    finding_id: uuid.UUID
    app_id: uuid.UUID
    title: str
    category: str
    mitigation_type: str
    mechanically_applicable: bool
    status: str
    code_guidance: str
    infra_manifest: dict[str, Any] = Field(default_factory=dict)
    target_resource: str | None = None
    applied_at: datetime | None = None
    reverted_at: datetime | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DefenceActionResponse(BaseModel):
    success: bool
    recommendation_id: uuid.UUID
    status: str
    message: str
    target_resource: str | None = None
    applied_at: datetime | None = None
    reverted_at: datetime | None = None


class StepLatencyMetric(BaseModel):
    step_number: int
    step_name: str
    latency_ms: float
    status_code: int
    timestamp: datetime


class RunMetricsRead(BaseModel):
    test_run_id: uuid.UUID
    app_id: uuid.UUID
    scenario_name: str
    status: str
    total_steps: int
    current_step: int
    avg_latency_ms: float
    p95_latency_ms: float
    min_latency_ms: float
    max_latency_ms: float
    status_code_counts: dict[str, int]
    cpu_utilization_pct: float
    memory_utilization_mb: float
    network_io_kbps: float
    step_latencies: list[StepLatencyMetric] = Field(default_factory=list)
    container_name: str | None = None
    container_status: str | None = None
    datasource_info: dict[str, Any] = Field(default_factory=dict)


class PlatformMetricsRead(BaseModel):
    active_test_runs: int
    completed_test_runs: int
    open_routes: int
    total_findings: int
    total_recommendations: int
    applied_mitigations: int
    mitigation_rate_pct: float
    cluster_health: str


class ObservabilityEventRead(BaseModel):
    id: str
    timestamp: datetime
    event_type: str
    severity: str
    component: str
    message: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class LokiLogEntry(BaseModel):
    timestamp: str
    message: str
    level: str = "info"
    service: str = "simulation-runner"
    labels: dict[str, str] = Field(default_factory=dict)


class GrafanaConfigRead(BaseModel):
    grafana_url: str
    dashboard_uid: str
    dashboard_url: str
    prometheus_url: str
    loki_url: str
    status: str


# --- Phase 13: Reporting Schemas ---
class ReportCreateRequest(BaseModel):
    test_run_id: uuid.UUID
    title: str | None = None


class BeforeAfterComparisonRead(BaseModel):
    prior_run_id: str | None = None
    prior_run_date: str | None = None
    prior_findings_count: int = 0
    current_findings_count: int = 0
    resolved_findings: list[dict[str, Any]] = Field(default_factory=list)
    new_findings: list[dict[str, Any]] = Field(default_factory=list)
    posture_delta: str = "initial_run"  # improved | degraded | unchanged | initial_run
    posture_score_delta: float = 0.0


class ReportRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    org_id: uuid.UUID
    test_run_id: uuid.UUID | None = None
    app_id: uuid.UUID | None = None
    title: str
    executive_summary: str
    markdown_content: str
    pdf_path: str | None = None
    csv_path: str | None = None
    before_after_comparison: dict[str, Any] = Field(default_factory=dict)
    metrics_summary: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class ReportSummaryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    org_id: uuid.UUID
    test_run_id: uuid.UUID | None = None
    app_id: uuid.UUID | None = None
    title: str
    executive_summary: str
    created_at: datetime
    has_pdf: bool = False
    has_csv: bool = False
