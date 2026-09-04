"""Shared Scenario Pydantic Schema — PRD Modules 7-9 (Phase 6).

This schema is the authoritative and ONLY representation any simulation scenario
can take in Pantheon. All three authoring paths (preset, AI, custom) must
validate against this exact model.
"""

from datetime import datetime
from enum import StrEnum
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ScenarioCategory(StrEnum):
    BRUTE_FORCE = "brute_force"
    CREDENTIAL_GUESSING = "credential_guessing"
    SQLI_RESILIENCE = "sqli_resilience"
    XSS_REFLECTION = "xss_reflection"
    AUTH_ABUSE = "auth_abuse"
    BOLA = "bola"
    API_ABUSE = "api_abuse"
    CACHE_PRESSURE = "cache_pressure"
    TRAFFIC_FLOOD = "traffic_flood"
    SERVICE_FAILURE = "service_failure"
    NETWORK_PARTITION = "network_partition"
    RESOURCE_EXHAUSTION = "resource_exhaustion"
    MULTI_STAGE_CHAIN = "multi_stage_chain"


class ScenarioSource(StrEnum):
    PRESET = "preset"
    AI = "ai"
    CUSTOM = "custom"


class EstimatedImpact(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ScenarioTarget(BaseModel):
    """Target workload definition for HTTP and chaos simulations."""

    model_config = ConfigDict(extra="ignore")

    service: str = Field(default="default", description="Target service name in tenant namespace")
    path: str = Field(default="/", description="Target HTTP path")
    port: int = Field(default=8080, ge=1, le=65535, description="Target port number")
    protocol: Literal["http", "https", "grpc", "internal"] = Field(
        default="http", description="Network protocol"
    )
    headers: dict[str, str] = Field(default_factory=dict, description="Custom HTTP headers")
    query_params: dict[str, str] = Field(
        default_factory=dict, description="Custom URL query parameters"
    )

    @field_validator("path")
    @classmethod
    def validate_path(cls, v: str) -> str:
        if not v.startswith("/"):
            return f"/{v}"
        return v


class ScenarioDefinition(BaseModel):
    """Core Pydantic definition for all simulation scenarios.

    Must adhere strictly to:
    {target, method, payload_category, concurrency, duration, expected_signals}.
    """

    model_config = ConfigDict(extra="ignore")

    name: str = Field(min_length=3, max_length=255, description="Scenario title")
    description: str = Field(
        min_length=5, description="Detailed description of simulation intent"
    )
    category: ScenarioCategory = Field(description="One of the 13 required scenario categories")
    target: ScenarioTarget = Field(
        default_factory=ScenarioTarget, description="Target destination"
    )
    method: str = Field(
        default="GET",
        description="HTTP method (GET, POST, PUT, DELETE, etc.) or Chaos action (pod_kill, latency, etc.)",
    )
    payload_category: str = Field(
        default="standard",
        description="Semantic payload bucket (e.g. auth_dictionary, sql_blind, rate_flood)",
    )
    concurrency: int = Field(
        default=10, ge=1, le=500, description="Concurrent attack workers or connections"
    )
    duration: int = Field(
        default=30, ge=5, le=600, description="Simulation duration in seconds (5-600s)"
    )
    expected_signals: list[str] = Field(
        min_length=1,
        description="Expected defense/reaction signals (e.g. http_429, pod_restarted)",
    )
    parameters: dict[str, Any] = Field(
        default_factory=dict, description="Category-specific runtime parameters"
    )
    estimated_impact: EstimatedImpact = Field(
        default=EstimatedImpact.MEDIUM, description="Anticipated disruption level"
    )
    estimated_duration_seconds: int = Field(
        default=30, ge=5, le=600, description="Estimated total execution time"
    )
    source: ScenarioSource = Field(
        default=ScenarioSource.CUSTOM, description="Origin: preset, ai, or custom"
    )
    tags: list[str] = Field(default_factory=list, description="Categorization tags")

    @field_validator("method")
    @classmethod
    def normalize_method(cls, v: str) -> str:
        return v.strip().upper()


# ---------------------------------------------------------------------------
# API Request / Response Models
# ---------------------------------------------------------------------------


class ScenarioCreateRequest(BaseModel):
    """Request payload to save a custom or AI-generated scenario."""

    name: str = Field(min_length=3, max_length=255)
    description: str = Field(min_length=5)
    category: ScenarioCategory
    definition: ScenarioDefinition
    source: ScenarioSource = ScenarioSource.CUSTOM
    is_preset: bool = False


class ScenarioValidateRequest(BaseModel):
    """Request payload to test validation of any arbitrary scenario definition."""

    definition: dict[str, Any]


class ScenarioValidationResponse(BaseModel):
    """Result of validating a scenario definition against the Pydantic schema."""

    valid: bool
    errors: list[str] = Field(default_factory=list)
    normalized_definition: ScenarioDefinition | None = None


class ScenarioResponse(BaseModel):
    """Scenario database record representation."""

    id: UUID
    org_id: UUID | None
    name: str
    slug: str
    description: str
    category: str
    source: str
    is_preset: bool
    definition: ScenarioDefinition
    created_at: datetime
    updated_at: datetime


class AIGenerateScenarioRequest(BaseModel):
    """Prompt payload for AI Scenario Builder."""

    prompt: str = Field(
        min_length=5, max_length=1000, description="Natural language scenario request"
    )
    app_id: UUID | None = Field(
        default=None, description="Optional deployed app to contextualize against"
    )
    target_path: str | None = Field(
        default=None, description="Specific endpoint path if preselected"
    )
    category: ScenarioCategory | None = Field(
        default=None, description="Optional target category hint"
    )
