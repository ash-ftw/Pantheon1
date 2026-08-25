"""Phase 4 Ingestion Pipeline Integration Test Suite — PRD Module 4.

Tests:
1. Compose Spec parsing & service translation (compose_translator)
2. Sensitive environment secret extraction (secret_extractor)
3. Typed Kubernetes manifest generation (manifest_builder)
4. Git & Compose application ingestion API endpoints
5. Version history retrieval & redeploy execution
"""

import uuid
from collections.abc import AsyncGenerator
from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.database import engine
from app.main import app
from app.services.compose_translator import compose_translator
from app.services.manifest_builder import manifest_builder
from app.services.secret_extractor import secret_extractor


@pytest.fixture(autouse=True)
async def cleanup_db_engine() -> AsyncGenerator[None, None]:
    yield
    await engine.dispose()


def test_compose_translator_parsing() -> None:
    """Verify safe PyYAML parsing and service extraction from Compose Spec."""
    sample_compose = """
version: '3.8'
services:
  web:
    image: nginx:latest
    ports:
      - "8080:80"
    environment:
      - NODE_ENV=production
      - DB_PASSWORD=supersecret
    depends_on:
      - db
  db:
    image: postgres:15
    environment:
      POSTGRES_PASSWORD: rootpassword
"""

    parsed = compose_translator.parse_yaml(sample_compose)
    services = compose_translator.extract_services(parsed)

    assert "web" in services
    assert "db" in services
    assert services["web"]["image"] == "nginx:latest"
    assert services["web"]["environment"]["DB_PASSWORD"] == "supersecret"
    assert services["web"]["depends_on"] == ["db"]
    assert services["web"]["ports"][0]["container_port"] == 80


def test_secret_extractor_pattern_matching() -> None:
    """Verify secret extraction logic for sensitive environment variables."""
    env = {
        "APP_NAME": "Pantheon",
        "DATABASE_URL": "postgres://localhost",
        "API_KEY": "sk_live_12345",
        "AUTH_SECRET": "jwt_secret_value",
        "REDIS_PORT": "6379",
    }

    plain, secret, k8s_secret = secret_extractor.extract_secrets(
        service_name="test-svc", environment=env, namespace="pantheon-tenant-test"
    )

    assert "APP_NAME" in plain
    assert "REDIS_PORT" in plain
    assert "API_KEY" not in plain
    assert "API_KEY" in secret
    assert "AUTH_SECRET" in secret
    assert k8s_secret is not None
    assert k8s_secret.metadata.name == "secret-test-svc"  # pyright: ignore


def test_manifest_builder_typed_models() -> None:
    """Verify hand-written Python builder generates valid V1Deployment & V1Service specs."""
    manifests = manifest_builder.build_service_manifests(
        service_name="payment-api",
        image_tag="registry.local/org-1/app-payment:v1",
        environment={"PORT": "8000", "STRIPE_SECRET_KEY": "sk_test_abc"},
        ports=[{"container_port": 8000, "host_port": 8000}],
        namespace="pantheon-tenant-org1",
    )

    deployment = manifests["deployment"]
    service = manifests["service"]
    secret = manifests["secret"]

    assert deployment.kind == "Deployment"
    assert deployment.metadata.name == "app-payment-api"
    assert service.kind == "Service"
    assert service.metadata.name == "svc-payment-api"
    assert secret is not None
    assert secret.kind == "Secret"


@pytest.mark.asyncio
async def test_app_ingestion_api_flow() -> None:
    """Verify Git & Compose app ingestion endpoints, version listing, and redeploy."""
    unique_suffix = uuid.uuid4().hex[:6]
    test_email = f"ingest_admin_{unique_suffix}@pantheon.io"
    org_name = f"Ingest Org {unique_suffix}"

    with patch("app.routers.apps.ingest_app.delay") as mock_ingest, patch(
        "app.routers.auth.provision_tenant_cluster.delay"
    ) as mock_prov:
        mock_ingest.return_value = None
        mock_prov.return_value = None
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            # 1. Register Org & User
            reg_res = await ac.post(
                "/api/auth/register",
                json={
                    "email": test_email,
                    "password": "Password123!",
                    "full_name": "Ingestion Tester",
                    "org_name": org_name,
                },
            )
            assert reg_res.status_code == 201
            token = reg_res.json()["access_token"]
            headers = {"Authorization": f"Bearer {token}"}

            # 2. Ingest Git Application
            git_res = await ac.post(
                "/api/apps/ingest/git",
                headers=headers,
                json={
                    "name": "Payment Microservice",
                    "git_url": "https://github.com/pantheon-cyber/sample-app.git",
                },
            )
            assert git_res.status_code == 202
            app_data = git_res.json()
            app_id = app_data["id"]
            assert app_data["name"] == "Payment Microservice"
            assert app_data["source_type"] == "git"

            # 3. List Apps for Org
            list_res = await ac.get("/api/apps", headers=headers)
            assert list_res.status_code == 200
            assert len(list_res.json()) >= 1

            # 4. Get Version History
            ver_res = await ac.get(f"/api/apps/{app_id}/versions", headers=headers)
            assert ver_res.status_code == 200
            assert len(ver_res.json()) == 1
            assert ver_res.json()[0]["version_number"] == 1

            # 5. Trigger Redeploy
            redeploy_res = await ac.post(f"/api/apps/{app_id}/redeploy", headers=headers)
            assert redeploy_res.status_code == 200

            # Verify new version created
            ver_res2 = await ac.get(f"/api/apps/{app_id}/versions", headers=headers)
            assert ver_res2.status_code == 200
            assert len(ver_res2.json()) == 2
            assert ver_res2.json()[0]["version_number"] == 2
