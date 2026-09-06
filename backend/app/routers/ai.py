"""AI Assistant Router — PRD Phase 12.

Exposes NVIDIA NIM (nvidia/nemotron-3.5-lightning-30b-a3b) endpoints:
- GET /api/ai/status: Introspect AI provider configuration and readiness
- POST /api/ai/scenario/generate: Generate scenario with reasoning extraction
- POST /api/ai/scenario/stream: SSE endpoint streaming reasoning and content deltas
- POST /api/ai/explain: AI cybersecurity reasoning for findings/remediations
"""

from __future__ import annotations

import json
from collections.abc import AsyncGenerator
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db_session
from app.models import App, User
from app.scenarios.schema import (
    AIGenerateScenarioRequest,
    ScenarioDefinition,
)
from app.services.ai_scenario_service import generate_scenario
from app.services.ai_service import DEFAULT_SYSTEM_PROMPT, ai_service
from app.services.auth_service import get_current_user

router = APIRouter(prefix="/api/ai", tags=["ai"])


class AIStatusResponse(BaseModel):
    """AI Assistant Layer status and metadata."""

    provider: str
    model: str
    base_url: str
    thinking_enabled: bool
    reasoning_budget: int
    configured: bool


class AIExplainRequest(BaseModel):
    """Cybersecurity explanation request payload."""

    topic: str
    context: dict[str, Any] = Field(default_factory=dict)
    target_profile: dict[str, Any] = Field(default_factory=dict)


class AIExplainResponse(BaseModel):
    """Reasoning-backed explanation output."""

    explanation: str
    reasoning: str | None = None
    model: str


@router.get("/status", response_model=AIStatusResponse)
async def get_ai_status(
    current_user: User = Depends(get_current_user),
) -> AIStatusResponse:
    """Introspect active AI Assistant provider settings and readiness."""
    return AIStatusResponse(
        provider=settings.ai_provider,
        model=settings.nvidia_nim_model,
        base_url=settings.nvidia_nim_base_url,
        thinking_enabled=settings.nvidia_nim_enable_thinking,
        reasoning_budget=settings.nvidia_nim_reasoning_budget,
        configured=bool(settings.nvidia_nim_api_key),
    )


@router.post("/scenario/generate")
async def generate_ai_scenario(
    request: AIGenerateScenarioRequest,
    current_user: User = Depends(get_current_user),
) -> ScenarioDefinition:
    """Generate a validated simulation scenario using NVIDIA NIM Nemotron."""
    if not current_user.org_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must belong to an organization to generate scenarios",
        )
    return await generate_scenario(request=request, org_id=current_user.org_id)


@router.post("/scenario/stream")
async def stream_ai_scenario(
    request: AIGenerateScenarioRequest,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> StreamingResponse:
    """Stream scenario generation with live reasoning traces via Server-Sent Events (SSE)."""
    if not current_user.org_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must belong to an organization to generate scenarios",
        )
    app_context: dict[str, Any] = {}
    if request.app_id:
        res = await db.execute(
            select(App).where(App.id == request.app_id, App.org_id == current_user.org_id)
        )

        app = res.scalar_one_or_none()
        if app:
            app_context = {
                "name": app.name,
                "target_profile": app.target_profile or {},
                "discovered_endpoints": (app.discovered_endpoints or {}).get("endpoints", []),
            }

    schema_json = json.dumps(ScenarioDefinition.model_json_schema(), indent=2)
    sys_prompt = (
        "You are Pantheon AI Scenario Architect powered by NVIDIA NIM Nemotron. "
        "Formulate safe, realistic security testing scenarios adhering strictly to authorized standards. "
        "Your final response MUST be a pure JSON object adhering to the provided ScenarioDefinition schema."
    )

    user_prompt = (
        f'Generate a security simulation scenario for:\n"{request.prompt}"\n\n'
        f"Category: {request.category.value if request.category else 'auto-detect'}\n"
        f"Target Path: {request.target_path or 'auto-resolve'}\n\n"
        f"Required JSON Schema:\n```json\n{schema_json}\n```\n\n"
    )
    if app_context:
        user_prompt += f"Target App Context:\n```json\n{json.dumps(app_context, indent=2)}\n```\n\n"
    user_prompt += "Respond ONLY with valid JSON."

    async def event_generator() -> AsyncGenerator[str, None]:
        async for chunk in ai_service.stream_chat(
            messages=[{"role": "user", "content": user_prompt}],
            system_prompt=sys_prompt,
            temperature=0.3,
            enable_thinking=True,
        ):
            chunk_type = chunk.get("type", "content")
            yield f"event: {chunk_type}\ndata: {json.dumps(chunk)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/explain", response_model=AIExplainResponse)
async def explain_security_finding(
    request: AIExplainRequest,
    current_user: User = Depends(get_current_user),
) -> AIExplainResponse:
    """Generate in-depth cybersecurity reasoning and remediation analysis."""
    messages = [
        {
            "role": "user",
            "content": (
                f"Analyze this security issue and explain the root cause, business impact, and concrete mitigation steps:\n"
                f"Topic: {request.topic}\n"
                f"Context: {json.dumps(request.context)}\n"
                f"Target Profile: {json.dumps(request.target_profile)}\n"
            ),
        }
    ]

    content, reasoning = await ai_service.generate_chat(
        messages=messages,
        system_prompt=DEFAULT_SYSTEM_PROMPT,
        temperature=0.4,
        enable_thinking=True,
    )

    return AIExplainResponse(
        explanation=content,
        reasoning=reasoning if reasoning else None,
        model=settings.nvidia_nim_model,
    )
