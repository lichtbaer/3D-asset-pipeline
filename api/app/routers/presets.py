"""Preset-API: Pipeline-Presets verwalten und anwenden."""

import asyncio

from fastapi import APIRouter, HTTPException

from app.schemas.preset import (
    PresetApplyRequest,
    PresetApplyResponse,
    PresetCreate,
    PresetResponse,
    PresetStep,
    PresetUpdate,
)
from app.services import preset_service

router = APIRouter(prefix="/presets", tags=["presets"])


def _to_response(data: dict) -> PresetResponse:
    return PresetResponse(
        id=data["id"],
        name=data["name"],
        description=data.get("description", ""),
        created_at=data["created_at"],
        updated_at=data["updated_at"],
        steps=[PresetStep(**s) for s in data.get("steps", [])],
    )


@router.get("", response_model=list[PresetResponse])
async def list_presets():
    """Alle Presets auflisten."""
    items = await asyncio.to_thread(preset_service.list_presets)
    return [_to_response(p) for p in items]


@router.post("", response_model=PresetResponse)
async def create_preset(body: PresetCreate):
    """Neues Preset erstellen."""
    steps = [s.model_dump() for s in body.steps]
    data = await asyncio.to_thread(
        preset_service.create_preset,
        body.name,
        body.description,
        steps,
    )
    return _to_response(data)


@router.get("/{preset_id}", response_model=PresetResponse)
async def get_preset(preset_id: str):
    """Preset laden."""
    data = await asyncio.to_thread(preset_service.get_preset, preset_id)
    if not data:
        raise HTTPException(404, detail="Preset nicht gefunden")
    return _to_response(data)


@router.put("/{preset_id}", response_model=PresetResponse)
async def update_preset(preset_id: str, body: PresetUpdate):
    """Preset aktualisieren."""
    steps = [s.model_dump() for s in body.steps] if body.steps is not None else None
    data = await asyncio.to_thread(
        preset_service.update_preset,
        preset_id,
        name=body.name,
        description=body.description,
        steps=steps,
    )
    if not data:
        raise HTTPException(404, detail="Preset nicht gefunden")
    return _to_response(data)


@router.delete("/{preset_id}", status_code=204)
async def delete_preset(preset_id: str):
    """Preset löschen."""
    deleted = await asyncio.to_thread(preset_service.delete_preset, preset_id)
    if not deleted:
        raise HTTPException(404, detail="Preset nicht gefunden")


@router.post("/{preset_id}/apply", response_model=PresetApplyResponse)
async def apply_preset(preset_id: str, body: PresetApplyRequest):
    """
    Preset auf Asset anwenden — gibt Execution-Plan zurück.
    Führt keine Steps aus; Nutzer bestätigt und führt manuell aus.
    """
    try:
        plan, applicable, skipped = await asyncio.to_thread(
            preset_service.compute_execution_plan,
            preset_id,
            body.asset_id,
            body.start_from_step,
        )
    except FileNotFoundError as e:
        raise HTTPException(404, detail=str(e)) from e

    preset = await asyncio.to_thread(preset_service.get_preset, preset_id)
    steps_total = len(preset.get("steps", [])) if preset else 0

    return PresetApplyResponse(
        preset_id=preset_id,
        asset_id=body.asset_id,
        steps_total=steps_total,
        steps_applicable=applicable,
        steps_skipped=skipped,
        execution_plan=plan,
    )
