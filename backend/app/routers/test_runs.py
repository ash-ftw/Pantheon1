"""Test Runs API Router — PRD Module 10 (Phase 9).

Endpoints:
- POST /api/test-runs: Launch simulation run
- GET /api/test-runs: List test runs for organization
- GET /api/test-runs/{test_run_id}: Get test run status & metrics
- POST /api/test-runs/{test_run_id}/stop: Emergency Stop (Kill Switch)
- GET /api/test-runs/{test_run_id}/findings: List security findings
- WEBSOCKET /api/test-runs/{test_run_id}/ws: Real-time event streaming
"""

import asyncio
import json
import uuid
from typing import Any

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db_session
from app.logging import get_logger
from app.models import Finding, TestRun, User
from app.schemas import (
    TestRunCreate,
    TestRunStopRequest,
)
from app.services.auth_service import get_current_user
from app.services.simulation_engine import simulation_engine

logger = get_logger(__name__)

router = APIRouter(prefix="/api/test-runs", tags=["test-runs"])


@router.post("", status_code=status.HTTP_201_CREATED, response_model=dict[str, Any])
async def create_test_run(
    payload: TestRunCreate,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Launch a new attack simulation run with safety gate and route broker wiring."""
    if not current_user.org_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must belong to an organization to launch test runs.",
        )

    try:
        run_data = await simulation_engine.launch_test_run(
            org_id=current_user.org_id,
            app_id=payload.app_id,
            scenario_id=payload.scenario_id,
            scenario_name=payload.scenario_name,
            scenario_category=payload.scenario_category,
            parameters=payload.parameters,
            db=db,
        )
        return run_data
    except ValueError as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(err),
        )


@router.get("", response_model=list[dict[str, Any]])
async def list_test_runs(
    app_id: uuid.UUID | None = Query(None, description="Filter by app ID"),
    status_filter: str | None = Query(None, alias="status", description="Filter by status"),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> list[dict[str, Any]]:
    """List test runs for current organization."""
    if not current_user.org_id:
        return []

    query = (
        select(TestRun)
        .where(TestRun.org_id == current_user.org_id)
        .options(selectinload(TestRun.findings))
        .order_by(TestRun.created_at.desc())
        .limit(limit)
    )
    if app_id:
        query = query.where(TestRun.app_id == app_id)
    if status_filter and status_filter.lower() != "all":
        query = query.where(TestRun.status == status_filter.lower())

    res = await db.execute(query)
    runs = res.scalars().all()
    return [simulation_engine._format_test_run(r) for r in runs]


@router.get("/{test_run_id}", response_model=dict[str, Any])
async def get_test_run(
    test_run_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Retrieve full test run details including logs and metrics."""
    query = select(TestRun).where(TestRun.id == test_run_id).options(selectinload(TestRun.findings))
    if current_user.org_id:
        query = query.where(TestRun.org_id == current_user.org_id)

    res = await db.execute(query)
    run = res.scalar_one_or_none()
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Test run '{test_run_id}' not found.",
        )
    return simulation_engine._format_test_run(run)


@router.post("/{test_run_id}/stop", response_model=dict[str, Any])
async def stop_test_run_endpoint(
    test_run_id: uuid.UUID,
    payload: TestRunStopRequest = TestRunStopRequest(),
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Emergency Kill Switch: immediately halts worker and revokes route in < 5s."""
    try:
        updated_run = await simulation_engine.stop_test_run(
            run_id=test_run_id,
            reason=payload.reason,
            org_id=current_user.org_id,
            db=db,
        )
        return updated_run
    except ValueError as err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(err),
        )


@router.get("/{test_run_id}/findings", response_model=list[dict[str, Any]])
async def get_test_run_findings(
    test_run_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> list[dict[str, Any]]:
    """List security findings identified during a test run."""
    query = select(Finding).where(Finding.test_run_id == test_run_id)
    if current_user.org_id:
        query = query.where(Finding.org_id == current_user.org_id)

    res = await db.execute(query)
    findings = res.scalars().all()
    return [
        {
            "id": str(f.id),
            "org_id": str(f.org_id),
            "test_run_id": str(f.test_run_id),
            "app_id": str(f.app_id),
            "title": f.title,
            "severity": f.severity,
            "category": f.category,
            "cwe_id": f.cwe_id,
            "owasp_category": f.owasp_category,
            "description": f.description,
            "evidence": f.evidence,
            "remediation_guidance": f.remediation_guidance,
            "status": f.status,
            "created_at": f.created_at.isoformat(),
        }
        for f in findings
    ]


@router.websocket("/{test_run_id}/ws")
async def test_run_websocket_stream(
    websocket: WebSocket,
    test_run_id: uuid.UUID,
) -> None:
    """Real-time WebSocket streaming endpoint for test run progress and logs.

    Subscribes to Redis Pub/Sub channel 'pantheon:test_run:{test_run_id}' with in-memory fallback.
    """
    await websocket.accept()
    logger.info("test_run_ws_connected", run_id=str(test_run_id))

    in_mem_queue = simulation_engine.subscribe_in_memory(test_run_id)
    redis_client = await simulation_engine.get_redis()
    pubsub = None

    async def _listen_redis() -> None:
        nonlocal pubsub
        if redis_client is not None:
            try:
                pubsub = redis_client.pubsub()
                await pubsub.subscribe(f"pantheon:test_run:{test_run_id}")
                async for message in pubsub.listen():
                    if message["type"] == "message":
                        data_str = message["data"]
                        await websocket.send_text(data_str)
            except asyncio.CancelledError:
                pass
            except Exception as e:
                logger.debug("redis_pubsub_listener_error", error=str(e))

    async def _listen_in_memory() -> None:
        try:
            while True:
                msg = await in_mem_queue.get()
                await websocket.send_text(json.dumps(msg))
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.debug("in_memory_listener_error", error=str(e))

    redis_task = None
    in_mem_task = None
    if redis_client is not None:
        redis_task = asyncio.create_task(_listen_redis())
    else:
        # Fallback to in-memory listener if Redis is unavailable
        in_mem_task = asyncio.create_task(_listen_in_memory())

    try:
        # Keep connection open and handle optional client ping/pong
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text(json.dumps({"event": "pong"}))
    except WebSocketDisconnect:
        logger.info("test_run_ws_disconnected", run_id=str(test_run_id))
    except Exception as err:
        logger.debug("test_run_ws_error", run_id=str(test_run_id), error=str(err))
    finally:
        if redis_task and not redis_task.done():
            redis_task.cancel()
        if in_mem_task and not in_mem_task.done():
            in_mem_task.cancel()
        if pubsub is not None:
            try:
                await pubsub.unsubscribe(f"pantheon:test_run:{test_run_id}")
                await pubsub.close()
            except Exception:
                pass
        simulation_engine.unsubscribe_in_memory(test_run_id, in_mem_queue)
