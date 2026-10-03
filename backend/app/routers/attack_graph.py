"""Attack Graph API Router — PRD Module 12 / Module 9 (Phase 10).

Endpoints:
- GET /api/attack-graph/runs: List runs available for graph inspection & replay
- GET /api/attack-graph/{test_run_id}: Get Attack Graph (nodes & edges) for test run
- GET /api/test-runs/{test_run_id}/graph: RESTful subresource alias
"""

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db_session
from app.logging import get_logger
from app.models import AttackGraphEdge, AttackGraphNode, Finding, TestRun, User
from app.services.auth_service import get_current_user
from app.services.simulation_engine import simulation_engine

logger = get_logger(__name__)

router = APIRouter(tags=["attack-graph"])


@router.get("/api/attack-graph/runs", response_model=list[dict[str, Any]])
async def list_attack_graph_runs(
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> list[dict[str, Any]]:
    """List test runs with graph data available for visualization and timeline replay."""
    query = select(TestRun).order_by(TestRun.created_at.desc())
    if current_user.org_id:
        query = query.where(TestRun.org_id == current_user.org_id)

    res = await db.execute(query)
    runs = res.scalars().all()

    items = []
    for r in runs:
        # Get node and edge counts
        n_count_res = await db.execute(
            select(func.count(AttackGraphNode.id)).where(AttackGraphNode.test_run_id == r.id)
        )
        e_count_res = await db.execute(
            select(func.count(AttackGraphEdge.id)).where(AttackGraphEdge.test_run_id == r.id)
        )
        f_count_res = await db.execute(
            select(func.count(Finding.id)).where(Finding.test_run_id == r.id)
        )

        n_count = n_count_res.scalar() or 0
        e_count = e_count_res.scalar() or 0
        f_count = f_count_res.scalar() or 0

        # If 0 nodes, compute estimated count (attacker + route + steps)
        if n_count == 0:
            n_count = 2 + (r.total_steps or 1)
            e_count = 1 + (r.total_steps or 1)

        items.append(
            {
                "id": str(r.id),
                "org_id": str(r.org_id),
                "app_id": str(r.app_id),
                "scenario_name": r.scenario_name,
                "scenario_category": r.scenario_category,
                "status": r.status,
                "current_step": r.current_step,
                "total_steps": r.total_steps,
                "current_step_name": r.current_step_name,
                "node_count": n_count,
                "edge_count": e_count,
                "findings_count": f_count,
                "created_at": r.created_at.isoformat(),
                "completed_at": r.completed_at.isoformat() if r.completed_at else None,
            }
        )
    return items


@router.get("/api/attack-graph/{test_run_id}", response_model=dict[str, Any])
@router.get("/api/test-runs/{test_run_id}/graph", response_model=dict[str, Any])
async def get_test_run_attack_graph(
    test_run_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Fetch all Attack Graph nodes and edges for the specified test run."""
    run_res = await db.execute(select(TestRun).where(TestRun.id == test_run_id))
    run = run_res.scalar_one_or_none()
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Test run '{test_run_id}' not found.",
        )

    if current_user.org_id and run.org_id != current_user.org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to test run outside organization.",
        )

    return await simulation_engine.get_test_run_graph(test_run_id=test_run_id, db=db)
