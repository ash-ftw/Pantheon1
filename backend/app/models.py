import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def utcnow() -> datetime:
    return datetime.now(UTC)


class Org(Base):
    """Organization (Tenant) model — PRD §7.1.

    Every tenant-owned table references org_id.
    """

    __tablename__ = "orgs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    plan: Mapped[str] = mapped_column(String(50), default="starter", nullable=False)
    cluster_status: Mapped[str] = mapped_column(String(50), default="provisioning", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )

    # Relationships
    members: Mapped[list["OrgMember"]] = relationship(
        "OrgMember", back_populates="org", cascade="all, delete-orphan"
    )
    users: Mapped[list["User"]] = relationship("User", back_populates="org")
    scenarios: Mapped[list["Scenario"]] = relationship(
        "Scenario", back_populates="org", cascade="all, delete-orphan"
    )
    routes: Mapped[list["Route"]] = relationship(
        "Route", back_populates="org", cascade="all, delete-orphan"
    )


class User(Base):
    """User account model — PRD §7.1.

    Extends basic auth attributes with org_id and role.
    """

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(1024), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    org_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("orgs.id", ondelete="SET NULL"), nullable=True
    )
    role: Mapped[str] = mapped_column(String(50), default="tester", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )

    # Relationships
    org: Mapped[Org | None] = relationship("Org", back_populates="users")


class OrgMember(Base):
    """Junction table for Org membership & roles."""

    __tablename__ = "org_members"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("orgs.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[str] = mapped_column(String(50), default="tester", nullable=False)
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )

    # Relationships
    org: Mapped[Org] = relationship("Org", back_populates="members")
    user: Mapped[User] = relationship("User")


class Invitation(Base):
    """Team invitation table — PRD §7.1."""

    __tablename__ = "invitations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("orgs.id", ondelete="CASCADE"), nullable=False
    )
    email: Mapped[str] = mapped_column(String(320), index=True, nullable=False)
    role: Mapped[str] = mapped_column(String(50), default="tester", nullable=False)
    token: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )


class AuditLog(Base):
    """Append-only security audit log — PRD §7.1.

    Every mutating action is recorded here with org_id scope.
    """

    __tablename__ = "audit_log"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("orgs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    user_email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    action: Mapped[str] = mapped_column(String(255), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    details: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False, index=True
    )


class App(Base):
    """Application model — PRD §7.1 / Module 4."""

    __tablename__ = "apps"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("orgs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    source_type: Mapped[str] = mapped_column(String(50), nullable=False)  # "git" | "compose"
    source_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    compose_yaml: Mapped[str | None] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="queued", nullable=False)

    # Phase 5 — Discovery fields (persisted target analysis & endpoint discovery results)
    discovery_status: Mapped[str] = mapped_column(
        String(50), default="pending", nullable=False
    )  # pending | running | completed | failed
    target_profile: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    discovered_endpoints: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )

    # Relationships
    versions: Mapped[list["AppVersion"]] = relationship(
        "AppVersion", back_populates="app", cascade="all, delete-orphan"
    )
    deployments: Mapped[list["AppDeployment"]] = relationship(
        "AppDeployment", back_populates="app", cascade="all, delete-orphan"
    )


class AppVersion(Base):
    """Application Version table — PRD Module 4 Item 11."""

    __tablename__ = "app_versions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    app_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("apps.id", ondelete="CASCADE"), nullable=False, index=True
    )
    version_number: Mapped[int] = mapped_column(nullable=False, default=1)
    commit_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    image_tag: Mapped[str | None] = mapped_column(String(255), nullable=True)
    detected_framework: Mapped[str | None] = mapped_column(String(100), nullable=True)
    build_logs: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )

    # Relationships
    app: Mapped[App] = relationship("App", back_populates="versions")


class AppDeployment(Base):
    """Application Deployment record — PRD Module 4 Item 11."""

    __tablename__ = "app_deployments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    app_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("apps.id", ondelete="CASCADE"), nullable=False, index=True
    )
    version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("app_versions.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(50), default="queued", nullable=False
    )  # queued, building, pushing, deploying, running, failed
    k8s_namespace: Mapped[str | None] = mapped_column(String(255), nullable=True)
    error_message: Mapped[str | None] = mapped_column(String, nullable=True)
    deployed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )

    # Relationships
    app: Mapped[App] = relationship("App", back_populates="deployments")


class Scenario(Base):
    """Scenario model — PRD Modules 7-9 (Phase 6).

    Represents an attack simulation or chaos engineering scenario.
    Source can be preset (system-wide), ai (generated), or custom.
    """

    __tablename__ = "scenarios"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("orgs.id", ondelete="CASCADE"), nullable=True, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[str] = mapped_column(String, nullable=False, default="")
    category: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    source: Mapped[str] = mapped_column(
        String(20), nullable=False, default="custom"
    )  # preset, ai, custom
    is_preset: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    definition: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )

    # Relationships
    org: Mapped[Org | None] = relationship("Org", back_populates="scenarios")


class Route(Base):
    """Route Broker record — PRD §7.5 / Module 11 (Phase 8).

    Represents a scoped, time-boxed application-layer route from the
    range cluster to a specific tenant service and port.
    """

    __tablename__ = "routes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("orgs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    test_run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )
    app_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("apps.id", ondelete="CASCADE"), nullable=True, index=True
    )

    target_service: Mapped[str] = mapped_column(String(255), nullable=False)
    target_port: Mapped[int] = mapped_column(nullable=False)
    path_prefix: Mapped[str] = mapped_column(String(255), default="/", nullable=False)

    route_url: Mapped[str] = mapped_column(String(512), nullable=False)
    status: Mapped[str] = mapped_column(
        String(50), default="active", nullable=False, index=True
    )  # active, revoked, expired
    ttl_seconds: Mapped[int] = mapped_column(nullable=False, default=1800)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revocation_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)

    ingress_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    namespace: Mapped[str] = mapped_column(String(255), nullable=False)

    # Relationships
    org: Mapped[Org] = relationship("Org", back_populates="routes")
    app: Mapped[App | None] = relationship("App")


class TestRun(Base):
    """Test Run execution record — PRD Module 10 (Phase 9).

    Tracks the live lifecycle of an attack scenario or chaos experiment.
    """

    __test__ = False
    __tablename__ = "test_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("orgs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    app_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("apps.id", ondelete="CASCADE"), nullable=False, index=True
    )
    scenario_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("scenarios.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    scenario_name: Mapped[str] = mapped_column(String(255), nullable=False)
    scenario_category: Mapped[str] = mapped_column(String(50), nullable=False)
    route_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("routes.id", ondelete="SET NULL"), nullable=True, index=True
    )

    status: Mapped[str] = mapped_column(
        String(50), default="queued", nullable=False, index=True
    )  # queued, running, completed, failed, stopped
    current_step: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_steps: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    current_step_name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    parameters: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    metrics: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    logs: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    error_message: Mapped[str | None] = mapped_column(String, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False, index=True
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    org: Mapped["Org"] = relationship("Org")
    app: Mapped["App"] = relationship("App")
    scenario: Mapped["Scenario | None"] = relationship("Scenario")
    route: Mapped["Route | None"] = relationship("Route")
    findings: Mapped[list["Finding"]] = relationship(
        "Finding", back_populates="test_run", cascade="all, delete-orphan"
    )
    attack_nodes: Mapped[list["AttackGraphNode"]] = relationship(
        "AttackGraphNode", back_populates="test_run", cascade="all, delete-orphan"
    )
    attack_edges: Mapped[list["AttackGraphEdge"]] = relationship(
        "AttackGraphEdge", back_populates="test_run", cascade="all, delete-orphan"
    )
    recommendations: Mapped[list["DefenceRecommendation"]] = relationship(
        "DefenceRecommendation", back_populates="test_run", cascade="all, delete-orphan"
    )


class Finding(Base):
    """Security Finding record — PRD Module 10 / Module 14 (Phase 9 & Phase 11).

    Generated when an attack simulation or probe detects a vulnerability, weakness,
    or lack of resilience in the target app.
    """

    __tablename__ = "findings"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("orgs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    test_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("test_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    app_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("apps.id", ondelete="CASCADE"), nullable=False, index=True
    )

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    severity: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )  # critical, high, medium, low, info
    category: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    cwe_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    owasp_category: Mapped[str | None] = mapped_column(String(100), nullable=True)

    description: Mapped[str] = mapped_column(String, nullable=False)
    evidence: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    remediation_guidance: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(
        String(50), default="open", nullable=False
    )  # open, resolved, mitigated

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False, index=True
    )

    # Relationships
    test_run: Mapped["TestRun"] = relationship("TestRun", back_populates="findings")
    app: Mapped["App"] = relationship("App")
    recommendations: Mapped[list["DefenceRecommendation"]] = relationship(
        "DefenceRecommendation", back_populates="finding", cascade="all, delete-orphan"
    )


class AttackGraphNode(Base):
    """Attack Graph Node — PRD Module 12 / Module 9 (Phase 10).

    Represents a discrete entity in an attack execution path:
    attacker, ephemeral route, ingress, target endpoint, backend service, or database.
    Built incrementally during step execution.
    """

    __tablename__ = "attack_graph_nodes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("orgs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    test_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("test_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    node_id: Mapped[str] = mapped_column(String(100), nullable=False)  # React Flow node id
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    node_type: Mapped[str] = mapped_column(
        String(50), default="endpoint", nullable=False
    )  # attacker, route, endpoint, service, database
    status: Mapped[str] = mapped_column(
        String(50), default="probing", nullable=False
    )  # probing, safe, blocked, compromised
    step_discovered: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    position_x: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    position_y: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False, index=True
    )

    # Relationships
    test_run: Mapped["TestRun"] = relationship("TestRun", back_populates="attack_nodes")


class AttackGraphEdge(Base):
    """Attack Graph Edge — PRD Module 12 / Module 9 (Phase 10).

    Represents an attack transition, payload transfer, or defense barrier between nodes.
    Built incrementally as steps unfold.
    """

    __tablename__ = "attack_graph_edges"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    test_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("test_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    edge_id: Mapped[str] = mapped_column(String(100), nullable=False)  # React Flow edge id
    source_node_id: Mapped[str] = mapped_column(String(100), nullable=False)
    target_node_id: Mapped[str] = mapped_column(String(100), nullable=False)
    label: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(
        String(50), default="traversed", nullable=False
    )  # traversed, blocked, compromised, probing
    step_discovered: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False, index=True
    )

    # Relationships
    test_run: Mapped["TestRun"] = relationship("TestRun", back_populates="attack_edges")


class DefenceRecommendation(Base):
    """Defence Recommendation — PRD Module 14 / Module 10 (Phase 11).

    Deterministic and rule-based mitigation recommendations mapped from security findings.
    Provides code-level guidance and 1-click infrastructure mitigations (e.g. NetworkPolicy,
    RateLimit middleware, security headers) that can be applied directly to the tenant cluster.
    """

    __tablename__ = "defence_recommendations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("orgs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    test_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("test_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    finding_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("findings.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    app_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("apps.id", ondelete="CASCADE"), nullable=False, index=True
    )

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    mitigation_type: Mapped[str] = mapped_column(
        String(50), default="infrastructure", nullable=False
    )  # infrastructure, code_guidance
    mechanically_applicable: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    status: Mapped[str] = mapped_column(
        String(50), default="suggested", nullable=False, index=True
    )  # suggested, applied, reverted, dismissed
    code_guidance: Mapped[str] = mapped_column(String, nullable=False)
    infra_manifest: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    target_resource: Mapped[str | None] = mapped_column(String(255), nullable=True)
    applied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reverted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False, index=True
    )

    # Relationships
    finding: Mapped["Finding"] = relationship("Finding", back_populates="recommendations")
    test_run: Mapped["TestRun"] = relationship("TestRun", back_populates="recommendations")
    app: Mapped["App"] = relationship("App")
