"""
Pipeline-Preset-Service: JSON-Files in storage/presets/.
Presets speichern Workflow-Sequenzen als wiederverwendbare Vorlagen.
"""

import asyncio
import json
import logging
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.config.storage import PRESETS_STORAGE_PATH
from app.schemas.preset import ExecutionPlanItem, PresetStep
from app.services import asset_service

logger = logging.getLogger(__name__)

SUPPORTED_STEPS = frozenset(
    {
        "image",
        "bgremoval",
        "mesh",
        "clip_floor",
        "remove_components",
        "repair",
        "simplify",
        "rigging",
        "animation",
        "export",
        "sketchfab_upload",
    }
)

# Steps die in asset.steps gespeichert sind
ASSET_STEP_KEYS = frozenset({"image", "bgremoval", "mesh", "rigging", "animation"})

# Steps die in asset.processing gespeichert sind (operation-Feld)
PROCESSING_OPERATIONS = frozenset(
    {"clip_floor", "remove_components", "repair", "simplify"}
)


def _preset_path(preset_id: str) -> Path:
    return PRESETS_STORAGE_PATH / f"{preset_id}.json"


def _validate_preset_id(preset_id: str) -> bool:
    return bool(re.fullmatch(r"[0-9a-f-]{36}", preset_id))


def list_presets() -> list[dict[str, Any]]:
    """Listet alle Presets (liest JSON-Files)."""
    PRESETS_STORAGE_PATH.mkdir(parents=True, exist_ok=True)
    result: list[dict[str, Any]] = []
    for path in PRESETS_STORAGE_PATH.glob("*.json"):
        preset_id = path.stem
        if not _validate_preset_id(preset_id):
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            result.append(data)
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning("Preset %s ungültig: %s", preset_id, e)
    result.sort(key=lambda p: p.get("created_at", ""), reverse=True)
    return result


def get_preset(preset_id: str) -> dict[str, Any] | None:
    """Lädt ein Preset, None wenn nicht vorhanden."""
    if not _validate_preset_id(preset_id):
        return None
    path = _preset_path(preset_id)
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def create_preset(name: str, description: str, steps: list[dict]) -> dict[str, Any]:
    """Erstellt neues Preset als JSON-File."""
    PRESETS_STORAGE_PATH.mkdir(parents=True, exist_ok=True)
    preset_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    data: dict[str, Any] = {
        "id": preset_id,
        "name": name,
        "description": description,
        "created_at": now,
        "updated_at": now,
        "steps": steps,
    }
    path = _preset_path(preset_id)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    logger.info("Preset %s erstellt: %s", preset_id, name)
    return data


def update_preset(
    preset_id: str,
    name: str | None = None,
    description: str | None = None,
    steps: list[dict] | None = None,
) -> dict[str, Any] | None:
    """Aktualisiert Preset. Gibt aktualisiertes Preset zurück oder None."""
    if not _validate_preset_id(preset_id):
        return None
    path = _preset_path(preset_id)
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    if name is not None:
        data["name"] = name
    if description is not None:
        data["description"] = description
    if steps is not None:
        data["steps"] = steps
    data["updated_at"] = datetime.now(timezone.utc).isoformat()
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    logger.info("Preset %s aktualisiert", preset_id)
    return data


def delete_preset(preset_id: str) -> bool:
    """Löscht Preset-File. Gibt True wenn gelöscht."""
    if not _validate_preset_id(preset_id):
        return False
    path = _preset_path(preset_id)
    if not path.exists():
        return False
    path.unlink()
    logger.info("Preset %s gelöscht", preset_id)
    return True


def _asset_has_step(meta: asset_service.AssetMetadata, step_type: str) -> bool:
    """Prüft ob Asset den Step bereits hat."""
    if step_type in ASSET_STEP_KEYS:
        return step_type in meta.steps and meta.steps[step_type].get("file")
    if step_type == "export":
        return len(meta.exports) > 0
    if step_type == "sketchfab_upload":
        return meta.sketchfab_upload is not None
    if step_type in PROCESSING_OPERATIONS:
        for entry in meta.processing:
            if entry.get("operation") == step_type:
                return True
    return False


def _step_matches_asset(
    meta: asset_service.AssetMetadata,
    preset_step: dict,
    step_type: str,
) -> bool:
    """
    Prüft ob der Preset-Step zum Asset-Zustand passt.
    Für skipped: Step muss vorhanden sein UND (wenn provider/params) übereinstimmen.
    Vereinfacht: Wenn Step vorhanden, gilt als erledigt.
    """
    if not _asset_has_step(meta, step_type):
        return False
    # Zusätzliche Prüfung für parametrisierte Steps
    if step_type == "simplify":
        target = preset_step.get("params", {}).get("target_faces")
        if target is not None:
            for entry in meta.processing:
                if entry.get("operation") == "simplify":
                    if entry.get("params", {}).get("target_faces") == target:
                        return True
            return False
    if step_type == "export":
        fmt = preset_step.get("params", {}).get("format")
        if fmt:
            for e in meta.exports:
                if e.get("format") == fmt:
                    return True
            return False
    return True


def compute_execution_plan(
    preset_id: str,
    asset_id: str,
    start_from_step: int = 0,
) -> tuple[list[ExecutionPlanItem], int, int]:
    """
    Berechnet Execution-Plan: welche Steps übersprungen, welche ausgeführt.
    Returns: (execution_plan, steps_applicable, steps_skipped)
    """
    preset = get_preset(preset_id)
    if not preset:
        raise FileNotFoundError(f"Preset {preset_id} nicht gefunden")
    meta = asset_service.get_asset(asset_id)
    if not meta:
        raise FileNotFoundError(f"Asset {asset_id} nicht gefunden")

    steps: list[dict] = preset.get("steps", [])
    plan: list[ExecutionPlanItem] = []
    applicable = 0
    skipped = 0

    for i, s in enumerate(steps):
        if i < start_from_step:
            continue
        step_type = s.get("step", "")
        provider = s.get("provider")
        params = s.get("params", {})

        if step_type not in SUPPORTED_STEPS:
            plan.append(
                ExecutionPlanItem(
                    step_index=i,
                    step=step_type,
                    provider=provider,
                    params=params,
                    status="applicable",
                    reason="Unbekannter Step-Typ",
                )
            )
            applicable += 1
            continue

        if _step_matches_asset(meta, s, step_type):
            plan.append(
                ExecutionPlanItem(
                    step_index=i,
                    step=step_type,
                    provider=provider,
                    params=params,
                    status="skipped",
                    reason="bereits vorhanden",
                )
            )
            skipped += 1
        else:
            plan.append(
                ExecutionPlanItem(
                    step_index=i,
                    step=step_type,
                    provider=provider,
                    params=params,
                    status="applicable",
                    reason=None,
                )
            )
            applicable += 1

    return plan, applicable, skipped


def asset_to_preset_steps(meta: asset_service.AssetMetadata) -> list[dict]:
    """
    Konvertiert Asset-Zustand in Preset-Steps.
    Liest steps, processing, exports, sketchfab_upload.
    """
    result: list[dict] = []

    # image
    if "image" in meta.steps and meta.steps["image"].get("file"):
        step_data = meta.steps["image"]
        result.append(
            {
                "step": "image",
                "provider": step_data.get("provider_key") or "picsart",
                "params": {
                    k: v
                    for k, v in step_data.items()
                    if k in ("prompt", "style") and v is not None
                },
            }
        )

    # bgremoval
    if "bgremoval" in meta.steps and meta.steps["bgremoval"].get("file"):
        step_data = meta.steps["bgremoval"]
        result.append(
            {
                "step": "bgremoval",
                "provider": step_data.get("provider_key") or "rembg",
                "params": {},
            }
        )

    # mesh
    if "mesh" in meta.steps and meta.steps["mesh"].get("file"):
        step_data = meta.steps["mesh"]
        result.append(
            {
                "step": "mesh",
                "provider": step_data.get("provider_key") or "trellis2",
                "params": {},
            }
        )

    # processing (Reihenfolge aus processing-Array)
    for entry in meta.processing:
        op = entry.get("operation")
        if op not in PROCESSING_OPERATIONS:
            continue
        params = entry.get("params", {})
        result.append({"step": op, "provider": None, "params": params})

    # rigging
    if "rigging" in meta.steps and meta.steps["rigging"].get("file"):
        step_data = meta.steps["rigging"]
        result.append(
            {
                "step": "rigging",
                "provider": step_data.get("provider_key") or "unirig",
                "params": {},
            }
        )

    # animation
    if "animation" in meta.steps and meta.steps["animation"].get("file"):
        step_data = meta.steps["animation"]
        result.append(
            {
                "step": "animation",
                "provider": step_data.get("provider_key") or "hymotion",
                "params": {
                    k: v
                    for k, v in step_data.items()
                    if k == "motion_prompt" and v is not None
                },
            }
        )

    # exports (jedes Format einmal)
    seen_formats: set[str] = set()
    for e in meta.exports:
        fmt = e.get("format")
        if fmt and fmt not in seen_formats:
            seen_formats.add(fmt)
            result.append(
                {
                    "step": "export",
                    "provider": None,
                    "params": {"format": fmt},
                }
            )

    # sketchfab_upload
    if meta.sketchfab_upload:
        result.append(
            {
                "step": "sketchfab_upload",
                "provider": None,
                "params": {
                    "is_private": meta.sketchfab_upload.get("is_private", False),
                },
            }
        )

    return result
