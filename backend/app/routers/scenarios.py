"""Scenario Management Router - PRD Modules 7-9 (Phase 6).

Endpoints:
- GET /api/scenarios/presets: List all 13 built-in preset scenarios
- GET /api/scenarios: List all scenarios (presets + saved custom/AI scenarios for org)
- GET /api/scenarios/{scenario_id}: Get scenario by ID or preset slug
- POST /api/scenarios: Create/save a custom or AI-generated scenario
- POST /api/scenarios/validate: Validate any scenario payload against shared schema
- POST /api/scenarios/generate: AI Scenario Builder natural language generation
- DELETE /api/scenarios/{scenario_id}: Delete a saved custom scenario
"""

import re
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db_session
from app.logging import get_logger
from app.models import Scenario, User
from app.safety.simulation_guard import check_simulation_safety
from app.scenarios.presets import get_all_presets
from app.scenarios.schema import (
    AIGenerateScenarioRequest,
    ScenarioCategory,
    ScenarioCreateRequest,
    ScenarioDefinition,
    ScenarioValidateRequest,
    ScenarioValidationResponse,
)
from app.services.ai_scenario_service import generate_scenario
from app.services.audit_service import log_audit_event
from app.services.auth_service import get_current_user

logger = get_logger(__name__)

router = APIRouter(prefix="/api/scenarios", tags=["scenarios"])


def _slugify(text: str) -> str:
    """Generate a clean URL-friendly slug."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    return re.sub(r"[-\s]+", "-", text)[:255]


def _format_preset_as_response(preset: ScenarioDefinition, index: int) -> dict[str, Any]:
    """Convert a preset ScenarioDefinition into standard scenario response shape."""
    # Deterministic UUID based on preset name
    preset_id = uuid.uuid5(uuid.NAMESPACE_DNS, f"pantheon.preset.{preset.name}")
    slug = _slugify(preset.name)
    return {
        "id": preset_id,
        "org_id": None,
        "name": preset.name,
        "slug": slug,
        "description": preset.description,
        "category": preset.category.value
        if isinstance(preset.category, ScenarioCategory)
        else preset.category,
        "source": "preset",
        "is_preset": True,
        "definition": preset,
        "created_at": "2026-01-01T00:00:00Z",
        "updated_at": "2026-01-01T00:00:00Z",
    }


# ---------------------------------------------------------------------------
# Preset Endpoints
# ---------------------------------------------------------------------------


@router.get("/presets", response_model=list[dict[str, Any]])
async def list_presets() -> list[dict[str, Any]]:
    """Return all 13 built-in preset scenarios.

    Presets are statically defined and do not require DB lookup.
    """
    presets = get_all_presets()
    return [_format_preset_as_response(p, idx) for idx, p in enumerate(presets)]


# ---------------------------------------------------------------------------
# Scenario CRUD & Discovery Endpoints
# ---------------------------------------------------------------------------


@router.get("", response_model=list[dict[str, Any]])
async def list_scenarios(
    category: ScenarioCategory | None = None,
    source: str | None = None,
    search: str | None = None,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> list[dict[str, Any]]:
    """List all available scenarios for the current tenant organization.

    Combines system presets with org-saved custom and AI scenarios.
    """
    results: list[dict[str, Any]] = []

    # 1. Add presets unless source explicitly filters them out
    if source in (None, "preset", "all"):
        for idx, preset in enumerate(get_all_presets()):
            if category and preset.category != category:
                continue
            if search:
                s_lower = search.lower()
                if s_lower not in preset.name.lower() and s_lower not in preset.description.lower():
                    continue
            results.append(_format_preset_as_response(preset, idx))

    # 2. Add saved DB scenarios for the current org
    if source in (None, "custom", "ai", "all") and current_user.org_id:
        query = (
            select(Scenario)
            .where(Scenario.org_id == current_user.org_id)
            .order_by(Scenario.created_at.desc())
        )
        if category:
            query = query.where(Scenario.category == category.value)
        if source and source != "all":
            query = query.where(Scenario.source == source)

        db_res = await db.execute(query)
        db_scenarios = db_res.scalars().all()

        for s in db_scenarios:
            if search:
                s_lower = search.lower()
                if s_lower not in s.name.lower() and s_lower not in s.description.lower():
                    continue
            try:
                def_obj = ScenarioDefinition.model_validate(s.definition)
            except Exception:
                def_obj = s.definition

            results.append(
                {
                    "id": s.id,
                    "org_id": s.org_id,
                    "name": s.name,
                    "slug": s.slug,
                    "description": s.description,
                    "category": s.category,
                    "source": s.source,
                    "is_preset": s.is_preset,
                    "definition": def_obj,
                    "created_at": s.created_at.isoformat(),
                    "updated_at": s.updated_at.isoformat(),
                }
            )

    return results


@router.get("/{scenario_id}", response_model=dict[str, Any])
async def get_scenario(
    scenario_id: str,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Retrieve a scenario by UUID or preset slug."""
    # Check if scenario_id matches a preset slug or deterministic UUID
    for idx, preset in enumerate(get_all_presets()):
        preset_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"pantheon.preset.{preset.name}"))
        preset_slug = _slugify(preset.name)
        if scenario_id in (preset_id, preset_slug):
            return _format_preset_as_response(preset, idx)

    # Check DB by UUID
    try:
        parsed_uuid = uuid.UUID(scenario_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scenario '{scenario_id}' not found",
        )

    res = await db.execute(
        select(Scenario).where(
            Scenario.id == parsed_uuid,
            (Scenario.org_id == current_user.org_id) | (Scenario.is_preset.is_(True)),
        )
    )
    db_scenario = res.scalar_one_or_none()

    if not db_scenario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scenario '{scenario_id}' not found",
        )

    try:
        def_obj = ScenarioDefinition.model_validate(db_scenario.definition)
    except Exception:
        def_obj = db_scenario.definition

    return {
        "id": db_scenario.id,
        "org_id": db_scenario.org_id,
        "name": db_scenario.name,
        "slug": db_scenario.slug,
        "description": db_scenario.description,
        "category": db_scenario.category,
        "source": db_scenario.source,
        "is_preset": db_scenario.is_preset,
        "definition": def_obj,
        "created_at": db_scenario.created_at.isoformat(),
        "updated_at": db_scenario.updated_at.isoformat(),
    }


@router.post("", response_model=dict[str, Any], status_code=status.HTTP_201_CREATED)
async def create_scenario(
    payload: ScenarioCreateRequest,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Create and persist a custom or AI-generated scenario for the current org.

    Validates strictly against ScenarioDefinition schema before inserting into DB.
    """
    if not current_user.org_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must belong to an organization to create scenarios",
        )

    # Validate definition against Pydantic schema
    try:
        validated_def = ScenarioDefinition.model_validate(payload.definition)
    except ValidationError as err:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"message": "Invalid scenario definition schema", "errors": err.errors()},
        )

    # Simulation Guard Safety Gate (PRD §7.6)
    safety_res = await check_simulation_safety(
        definition=validated_def,
        org_id=current_user.org_id,
        db=db,
        user_id=current_user.id,
    )
    if not safety_res.allowed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "message": "Scenario rejected by Simulation Guard",
                "violation_type": safety_res.violation_type.value
                if safety_res.violation_type
                else None,
                "reason": safety_res.reason,
                "violating_elements": safety_res.violating_elements,
            },
        )

    slug = _slugify(payload.name)
    scenario_obj = Scenario(
        org_id=current_user.org_id,
        name=payload.name,
        slug=slug,
        description=payload.description,
        category=payload.category.value,
        source=payload.source.value,
        is_preset=payload.is_preset,
        definition=validated_def.model_dump(mode="json"),
    )

    db.add(scenario_obj)
    await db.commit()
    await db.refresh(scenario_obj)

    # Log audit event
    await log_audit_event(
        db=db,
        org_id=current_user.org_id,
        user_id=current_user.id,
        action="scenario.created",
        resource_type="scenario",
        resource_id=str(scenario_obj.id),
        details={
            "name": scenario_obj.name,
            "category": scenario_obj.category,
            "source": scenario_obj.source,
        },
    )

    logger.info(
        "scenario_created",
        scenario_id=str(scenario_obj.id),
        org_id=str(current_user.org_id),
        name=scenario_obj.name,
    )

    return {
        "id": scenario_obj.id,
        "org_id": scenario_obj.org_id,
        "name": scenario_obj.name,
        "slug": scenario_obj.slug,
        "description": scenario_obj.description,
        "category": scenario_obj.category,
        "source": scenario_obj.source,
        "is_preset": scenario_obj.is_preset,
        "definition": validated_def,
        "created_at": scenario_obj.created_at.isoformat(),
        "updated_at": scenario_obj.updated_at.isoformat(),
    }


@router.delete("/{scenario_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_scenario(
    scenario_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> None:
    """Delete an organization's custom scenario. Built-in presets cannot be deleted."""
    res = await db.execute(
        select(Scenario).where(
            Scenario.id == scenario_id,
            Scenario.org_id == current_user.org_id,
        )
    )
    scenario_obj = res.scalar_one_or_none()

    if not scenario_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scenario not found or access denied",
        )

    if scenario_obj.is_preset:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="System presets cannot be deleted",
        )

    await db.delete(scenario_obj)
    await db.commit()

    if current_user.org_id:
        await log_audit_event(
            db=db,
            org_id=current_user.org_id,
            user_id=current_user.id,
            action="scenario.deleted",
            resource_type="scenario",
            resource_id=str(scenario_id),
            details={"name": scenario_obj.name},
        )

    logger.info("scenario_deleted", scenario_id=str(scenario_id))


# ---------------------------------------------------------------------------
# Validation & AI Generation Endpoints
# ---------------------------------------------------------------------------


@router.post("/validate", response_model=ScenarioValidationResponse)
async def validate_scenario(payload: ScenarioValidateRequest) -> ScenarioValidationResponse:
    """Validate any arbitrary scenario definition JSON without saving.

    Used by the Custom Scenario Authoring UI (PRD Module 9) for real-time validation.
    """
    try:
        validated = ScenarioDefinition.model_validate(payload.definition)
        safety_res = await check_simulation_safety(definition=validated)
        if not safety_res.allowed:
            return ScenarioValidationResponse(
                valid=False,
                errors=[f"Simulation Guard: {safety_res.reason}"],
                normalized_definition=None,
            )
        return ScenarioValidationResponse(
            valid=True,
            errors=[],
            normalized_definition=validated,
        )
    except ValidationError as e:
        error_msgs = [f"{err['loc']}: {err['msg']}" for err in e.errors()]
        return ScenarioValidationResponse(
            valid=False,
            errors=error_msgs,
            normalized_definition=None,
        )


@router.post("/generate", response_model=ScenarioDefinition)
async def generate_ai_scenario(
    payload: AIGenerateScenarioRequest,
    current_user: User = Depends(get_current_user),
) -> ScenarioDefinition:
    """AI Scenario Builder endpoint (PRD Module 8).

    Prompts the AI service with user intent and target app discovery context.
    Strictly re-validates the response through ScenarioDefinition before returning.
    """
    if not current_user.org_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must belong to an organization to generate scenarios",
        )

    scenario_def = await generate_scenario(payload, current_user.org_id)
    return scenario_def
