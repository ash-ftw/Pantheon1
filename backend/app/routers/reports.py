"""Reports Router — PRD Module 12 (Phase 13).

Provides REST endpoints for generating, listing, previewing, and downloading
authoritative security reports with derived PDF and CSV exports.
"""

from __future__ import annotations

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db_session
from app.logging import get_logger
from app.models import User
from app.schemas import (
    ReportCreateRequest,
    ReportRead,
    ReportSummaryRead,
)
from app.services.auth_service import get_current_user
from app.services.reporting_service import reporting_service

logger = get_logger(__name__)

router = APIRouter(prefix="/api/reports", tags=["reports"])


@router.post("/generate", response_model=ReportRead, status_code=status.HTTP_201_CREATED)
async def generate_report(
    payload: ReportCreateRequest,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> ReportRead:
    """Generate an authoritative security test report with derived PDF and CSV exports."""
    if not current_user.org_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must belong to an organization to generate reports.",
        )

    try:
        report = await reporting_service.generate_report(
            db=db,
            test_run_id=payload.test_run_id,
            org_id=current_user.org_id,
            title=payload.title,
        )
        return ReportRead.model_validate(report)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error("Error generating report: %s", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate report: {str(e)}",
        )


@router.get("", response_model=list[ReportSummaryRead])
async def list_reports(
    test_run_id: Annotated[uuid.UUID | None, Query(description="Filter by Test Run ID")] = None,
    app_id: Annotated[uuid.UUID | None, Query(description="Filter by App ID")] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> list[ReportSummaryRead]:
    """List generated reports for the current organization."""
    if not current_user.org_id:
        return []

    reports = await reporting_service.list_reports(
        db=db,
        org_id=current_user.org_id,
        test_run_id=test_run_id,
        app_id=app_id,
        limit=limit,
    )

    summaries = []
    for r in reports:
        summaries.append(
            ReportSummaryRead(
                id=r.id,
                org_id=r.org_id,
                test_run_id=r.test_run_id,
                app_id=r.app_id,
                title=r.title,
                executive_summary=r.executive_summary,
                created_at=r.created_at,
                has_pdf=bool(r.pdf_path),
                has_csv=bool(r.csv_path),
            )
        )
    return summaries


@router.get("/runs/{test_run_id}/preview", response_model=dict[str, Any])
async def preview_report(
    test_run_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Preview report markdown and before/after comparison before generating."""
    if not current_user.org_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must belong to an organization.",
        )

    try:
        return await reporting_service.preview_report(
            db=db, test_run_id=test_run_id, org_id=current_user.org_id
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error("Error previewing report: %s", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to preview report: {str(e)}",
        )


@router.get("/{report_id}", response_model=ReportRead)
async def get_report(
    report_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> ReportRead:
    """Retrieve full report record including raw markdown content and metrics."""
    if not current_user.org_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must belong to an organization.",
        )

    report = await reporting_service.get_report(db, report_id, current_user.org_id)
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Report {report_id} not found",
        )
    return ReportRead.model_validate(report)


@router.get("/{report_id}/download")
async def download_report(
    report_id: uuid.UUID,
    format: Annotated[str, Query(pattern="^(pdf|csv|md)$")] = "pdf",
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> Response:
    """Download report file in specified format (pdf, csv, md)."""
    if not current_user.org_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must belong to an organization.",
        )

    try:
        content, media_type, filename = await reporting_service.get_export_bytes(
            db=db,
            report_id=report_id,
            org_id=current_user.org_id,
            format_type=format,
        )
        return Response(
            content=content,
            media_type=media_type,
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error("Error downloading report: %s", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to download report: {str(e)}",
        )
