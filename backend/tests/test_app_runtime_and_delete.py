"""Tests for App Runtime Lifecycle (Start, Stop, Status Sync) and App Deletion."""

import uuid
from unittest.mock import MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.database import async_session_factory
from app.main import app
from app.models import App, AppDeployment, AppVersion, Org, OrgMember, User
from app.services.auth_service import create_access_token


@pytest.fixture
async def setup_app_test_data():
    """Create test organization, user, and sample apps."""
    async with async_session_factory() as db:
        unique_id = uuid.uuid4().hex[:8]
        org = Org(name=f"Runtime Test Org {unique_id}", slug=f"runtime-org-{unique_id}")
        db.add(org)
        await db.commit()
        await db.refresh(org)

        user = User(
            email=f"tester-{unique_id}@pantheon.local",
            hashed_password="hashed_pw_test",
            full_name="Runtime Tester",
            org_id=org.id,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

        member = OrgMember(org_id=org.id, user_id=user.id, role="admin")
        db.add(member)

        # App 1: Previously built app with a version record
        app_running = App(
            org_id=org.id,
            name=f"test-app-run-{unique_id}",
            source_type="git",
            source_url="https://github.com/example/test-run.git",
            status="running",
        )
        db.add(app_running)
        await db.commit()
        await db.refresh(app_running)

        ver = AppVersion(
            app_id=app_running.id,
            version_number=1,
            image_tag=f"localhost:5000/test-org/app-{unique_id}:v1",
        )
        db.add(ver)
        await db.commit()
        await db.refresh(ver)

        dep = AppDeployment(
            app_id=app_running.id,
            version_id=ver.id,
            status="running",
        )
        db.add(dep)
        await db.commit()

        # App 2: Failed app ingestion
        app_failed = App(
            org_id=org.id,
            name=f"test-app-fail-{unique_id}",
            source_type="git",
            source_url="https://github.com/example/test-fail.git",
            status="failed",
        )
        db.add(app_failed)
        await db.commit()
        await db.refresh(app_failed)

        token = create_access_token(
            user_id=user.id,
            email=user.email,
            org_id=org.id,
            role="admin",
        )

        yield {
            "org": org,
            "user": user,
            "token": token,
            "app_running": app_running,
            "app_failed": app_failed,
        }


@pytest.mark.asyncio
async def test_list_apps_syncs_stopped_container_status(setup_app_test_data):
    """Verify that if an app is marked running in DB but container is exited/stopped, list_apps syncs it to stopped."""
    data = setup_app_test_data
    token = data["token"]
    app_running = data["app_running"]

    # Mock is_container_running to return False (simulating system restart / exited container)
    with (
        patch(
            "app.services.app_runtime_service.app_runtime_service.is_container_running",
            return_value=False,
        ),
        patch("app.services.docker_builder.docker_builder._get_client", return_value=MagicMock()),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.get(
                "/api/apps",
                headers={"Authorization": f"Bearer {token}"},
            )

        assert resp.status_code == 200
        apps_list = resp.json()
        target_app = next((a for a in apps_list if a["id"] == str(app_running.id)), None)
        assert target_app is not None
        assert target_app["status"] == "stopped"

    # Verify DB was also updated to stopped
    async with async_session_factory() as db:
        res = await db.execute(select(App).where(App.id == app_running.id))
        refreshed = res.scalar_one()
        assert refreshed.status == "stopped"


@pytest.mark.asyncio
async def test_start_and_stop_app_instance(setup_app_test_data):
    """Verify starting and stopping an app instance via API."""
    data = setup_app_test_data
    token = data["token"]
    app_obj = data["app_running"]

    # Start app
    with patch("app.services.docker_builder.docker_builder._get_client", return_value=None):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp_start = await ac.post(
                f"/api/apps/{app_obj.id}/start",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert resp_start.status_code == 200
            assert resp_start.json()["status"] == "running"

            # Stop app
            resp_stop = await ac.post(
                f"/api/apps/{app_obj.id}/stop",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert resp_stop.status_code == 200
            assert resp_stop.json()["status"] == "stopped"


@pytest.mark.asyncio
async def test_delete_app_instance_cascades(setup_app_test_data):
    """Verify DELETE /api/apps/{id} removes the app and all associated records."""
    data = setup_app_test_data
    token = data["token"]
    app_failed = data["app_failed"]
    app_running = data["app_running"]

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Delete failed app
        resp = await ac.delete(
            f"/api/apps/{app_failed.id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "deleted"
        assert resp.json()["id"] == str(app_failed.id)

        # Delete running app with version & deployment
        resp_run = await ac.delete(
            f"/api/apps/{app_running.id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp_run.status_code == 200

    # Verify both apps are gone from DB
    async with async_session_factory() as db:
        res_fail = await db.execute(select(App).where(App.id == app_failed.id))
        assert res_fail.scalar_one_or_none() is None

        res_run = await db.execute(select(App).where(App.id == app_running.id))
        assert res_run.scalar_one_or_none() is None

        # Verify cascade on versions
        res_vers = await db.execute(select(AppVersion).where(AppVersion.app_id == app_running.id))
        assert len(res_vers.scalars().all()) == 0
