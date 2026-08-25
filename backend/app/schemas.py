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
    language: str | None = None
    framework: str | None = None
    exposed_ports: list[int] = []
    detected_db: str | None = None
    db_environment_variables: list[str] = []
    auth_mechanisms: list[str] = []
    auth_env_variables: list[str] = []


class DiscoveryEndpointsRequest(BaseModel):
    app_id: uuid.UUID


class DiscoveryEndpointsResponse(BaseModel):
    app_id: str
    org_id: str
    namespace: str
    specs_found: list[str] = []
    endpoints: list[dict[str, Any]] = []
    classification: dict[str, list[dict[str, Any]]] = {
        "public": [],
        "likely_admin": [],
        "likely_auth": [],
        "upload": [],
        "search": [],
    }


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
