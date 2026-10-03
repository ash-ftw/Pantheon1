"""Defence Engine Router — PRD Module 14 / Module 10 (Phase 11).

REST endpoints for querying mitigation recommendations, retrieving infrastructure manifests,
and triggering 1-click mitigation application / rollback.
"""

from __future__ import annotations

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db_session
from app.schemas import DefenceActionResponse, DefenceRecommendationRead
from app.services.defence_engine import defence_engine_service

router = APIRouter(prefix="/api/defence", tags=["defence-engine"])


@router.get("/recommendations", response_model=list[DefenceRecommendationRead])
async def list_recommendations(
    test_run_id: Annotated[uuid.UUID | None, Query(description="Filter by Test Run ID")] = None,
    status: Annotated[
        str | None, Query(description="Filter by status (suggested, applied, reverted, dismissed)")
    ] = None,
    category: Annotated[str | None, Query(description="Filter by category")] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
    db: AsyncSession = Depends(get_db_session),
) -> list[DefenceRecommendationRead]:
    """List defence recommendations with optional filters.

    If test_run_id is provided, automatically ensures all findings have recommendations generated.
    """
    if test_run_id:
        await defence_engine_service.ensure_recommendations_for_run(db, test_run_id)

    recs = await defence_engine_service.list_recommendations(
        db, test_run_id=test_run_id, status=status, category=category, limit=limit
    )
    return [DefenceRecommendationRead.model_validate(r) for r in recs]


@router.get("/recommendations/{recommendation_id}", response_model=DefenceRecommendationRead)
async def get_recommendation(
    recommendation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
) -> DefenceRecommendationRead:
    """Fetch a single defence recommendation by ID."""
    rec = await defence_engine_service.get_recommendation(db, recommendation_id)
    if not rec:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Defence recommendation {recommendation_id} not found",
        )
    return DefenceRecommendationRead.model_validate(rec)


@router.post("/recommendations/{recommendation_id}/apply", response_model=DefenceActionResponse)
async def apply_mitigation(
    recommendation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
) -> DefenceActionResponse:
    """1-Click Infrastructure Mitigation Applicator.

    Validates and deploys the infrastructure manifest (NetworkPolicy, RateLimit Middleware,
    Security Headers) to the tenant cluster, transitions recommendation to 'applied',
    and updates the associated finding to 'mitigated'.
    """
    result = await defence_engine_service.apply_mitigation(db, recommendation_id)
    if not result.success and result.status == "not_found":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Defence recommendation {recommendation_id} not found",
        )
    if not result.success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.message,
        )
    return result


@router.post("/recommendations/{recommendation_id}/revert", response_model=DefenceActionResponse)
async def revert_mitigation(
    recommendation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
) -> DefenceActionResponse:
    """Roll back an applied infrastructure mitigation."""
    result = await defence_engine_service.revert_mitigation(db, recommendation_id)
    if not result.success and result.status == "not_found":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Defence recommendation {recommendation_id} not found",
        )
    if not result.success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.message,
        )
    return result


@router.post("/recommendations/{recommendation_id}/explain")
async def explain_recommendation(
    recommendation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """AI Assistant (Phase 12 / FR-9.2) - Contextual Defence Recommendation Explanation.

    Uses NVIDIA NIM Nemotron to generate deep cybersecurity rationale, root cause analysis,
    and tailored mitigation instructions for this specific finding.
    """
    rec = await defence_engine_service.get_recommendation(db, recommendation_id)
    if not rec:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Defence recommendation {recommendation_id} not found",
        )

    from app.models import Finding

    f_res = await db.execute(select(Finding).where(Finding.id == rec.finding_id))
    finding = f_res.scalar_one_or_none()

    prompt = (
        f"Explain the technical risk and concrete remediation for this security finding:\n\n"
        f"Title: {rec.title}\n"
        f"Category: {rec.category}\n"
        f"Mitigation Type: {rec.mitigation_type}\n"
        f"Finding Severity: {finding.severity if finding else 'Unknown'}\n"
        f"Finding Details: {finding.description if finding else 'N/A'}\n"
        f"Current Code Guidance:\n{rec.code_guidance}\n\n"
        f"Provide a clear, professional breakdown: 1. Attack Mechanics, 2. Architectural Impact, 3. Immediate Actionable Fix."
    )

    from app.services.ai_service import ai_service

    try:
        content, reasoning = await ai_service.generate_chat(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.4,
            enable_thinking=True,
        )
        return {
            "recommendation_id": str(recommendation_id),
            "title": rec.title,
            "explanation": content,
            "reasoning": reasoning,
            "model": ai_service.model,
        }
    except Exception as e:
        # Fallback to catalog guidance
        return {
            "recommendation_id": str(recommendation_id),
            "title": rec.title,
            "explanation": rec.code_guidance,
            "reasoning": None,
            "model": "rule-based-fallback",
            "warning": str(e),
        }
