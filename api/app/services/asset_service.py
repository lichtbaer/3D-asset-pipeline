"""
Asset-Persistenz: Ordnerstruktur mit Metadaten für alle Pipeline-Outputs.
Jeder generierte Output wird auf dem Filesystem abgelegt.
"""

import json
import logging
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

from app.config.storage import (
    ASSETS_STORAGE_PATH,
    BGREMOVAL_STORAGE_PATH,
    MESH_STORAGE_PATH,
)

logger = logging.getLogger(__name__)

# Step-Typen für metadata.json
StepType = str  # "image" | "bgremoval" | "mesh"


class AssetMetadata:
    """Repräsentation der metadata.json eines Assets."""

    def __init__(
        self,
        asset_id: str,
        created_at: str,
        updated_at: str,
        steps: dict[str, dict[str, Any]],
        processing: list[dict[str, Any]] | None = None,
    ):
        self.asset_id = asset_id
        self.created_at = created_at
        self.updated_at = updated_at
        self.steps = steps
        self.processing = processing or []

    def to_dict(self) -> dict[str, Any]:
        return {
            "asset_id": self.asset_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "steps": self.steps,
            "processing": self.processing,
        }


def _asset_dir(asset_id: str) -> Path:
    return ASSETS_STORAGE_PATH / asset_id


def _metadata_path(asset_id: str) -> Path:
    return _asset_dir(asset_id) / "metadata.json"


def create_asset() -> str:
    """
    Legt Ordner + leere metadata.json an, gibt asset_id zurück.
    """
    asset_id = str(uuid.uuid4())
    asset_path = _asset_dir(asset_id)
    asset_path.mkdir(parents=True, exist_ok=True)

    now = datetime.now(timezone.utc).isoformat()
    metadata = {
        "asset_id": asset_id,
        "created_at": now,
        "updated_at": now,
        "steps": {},
    }
    _metadata_path(asset_id).write_text(
        json.dumps(metadata, indent=2), encoding="utf-8"
    )
    return asset_id


def update_step(
    asset_id: str,
    step: StepType,
    data: dict[str, Any],
    file_bytes: bytes | None = None,
    filename: str | None = None,
) -> None:
    """
    Schreibt Datei (falls file_bytes) und aktualisiert metadata.json.
    data enthält: job_id, provider_key, prompt/negative_prompt/source_file, etc.
    """
    asset_path = _asset_dir(asset_id)
    if not asset_path.exists():
        raise FileNotFoundError(f"Asset {asset_id} existiert nicht")

    if file_bytes is not None and filename:
        target = asset_path / filename
        target.write_bytes(file_bytes)
        data["file"] = filename

    meta_path = _metadata_path(asset_id)
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    meta["steps"][step] = data
    meta["updated_at"] = datetime.now(timezone.utc).isoformat()
    meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")


def get_asset(asset_id: str) -> AssetMetadata | None:
    """Liest metadata.json, gibt None wenn nicht vorhanden."""
    meta_path = _metadata_path(asset_id)
    if not meta_path.exists():
        return None
    data = json.loads(meta_path.read_text(encoding="utf-8"))
    return AssetMetadata(
        asset_id=data["asset_id"],
        created_at=data["created_at"],
        updated_at=data["updated_at"],
        steps=data.get("steps", {}),
        processing=data.get("processing", []),
    )


def list_assets() -> list[AssetMetadata]:
    """Alle Assets sortiert nach created_at desc."""
    ASSETS_STORAGE_PATH.mkdir(parents=True, exist_ok=True)
    assets: list[AssetMetadata] = []
    for path in ASSETS_STORAGE_PATH.iterdir():
        if path.is_dir():
            meta = get_asset(path.name)
            if meta:
                assets.append(meta)
    assets.sort(key=lambda a: a.created_at, reverse=True)
    return assets


def get_file_path(asset_id: str, filename: str) -> Path | None:
    """Pfad zur Datei, None wenn nicht vorhanden."""
    target = _asset_dir(asset_id) / filename
    if target.exists() and target.is_file():
        return target
    return None


def get_asset_dir(asset_id: str) -> Path:
    """Asset-Ordner-Pfad. Erstellt nicht automatisch."""
    return _asset_dir(asset_id)


def write_asset_file(asset_id: str, filename: str, data: bytes) -> None:
    """Schreibt Datei in Asset-Ordner."""
    asset_path = _asset_dir(asset_id)
    if not asset_path.exists():
        raise FileNotFoundError(f"Asset {asset_id} existiert nicht")
    (asset_path / filename).write_bytes(data)


def list_mesh_files(asset_id: str) -> list[str]:
    """Listet alle GLB-Dateien im Asset-Ordner (für Mesh-Processing-Quelle)."""
    asset_path = _asset_dir(asset_id)
    if not asset_path.exists():
        return []
    return sorted(
        f.name for f in asset_path.iterdir()
        if f.is_file() and f.suffix.lower() == ".glb"
    )


def append_processing_entry(asset_id: str, entry: dict[str, Any]) -> None:
    """Fügt Eintrag zum processing-Array in metadata.json hinzu."""
    meta_path = _metadata_path(asset_id)
    if not meta_path.exists():
        raise FileNotFoundError(f"Asset {asset_id} existiert nicht")
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    if "processing" not in meta:
        meta["processing"] = []
    meta["processing"].append(entry)
    meta["updated_at"] = datetime.now(timezone.utc).isoformat()
    meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")


async def _download_bytes(url: str) -> bytes:
    """Lädt URL herunter, gibt Bytes zurück."""
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.get(url)
        response.raise_for_status()
        return response.content


def _resolve_local_path_from_url(url: str) -> Path | None:
    """
    Prüft ob URL auf lokale Static-Datei zeigt (z.B. /static/bgremoval/X.png).
    Gibt lokalen Pfad zurück oder None.
    """
    if "/static/bgremoval/" in url:
        # http://localhost:8000/static/bgremoval/{job_id}.png oder /static/bgremoval/...
        parts = url.rstrip("/").split("/")
        if parts:
            filename = parts[-1]
            if filename:
                path = BGREMOVAL_STORAGE_PATH / filename
                if path.exists():
                    return path
    return None


async def persist_image_job(
    job_id: str,
    asset_id: str,
    provider_key: str,
    prompt: str,
    result_url: str,
    negative_prompt: str | None = None,
    width: int | None = None,
    height: int | None = None,
) -> None:
    """
    Speichert Bild-Job-Output im Asset-Ordner.
    Lädt Bild von result_url herunter (PicsArt/extern).
    """
    try:
        image_bytes = await _download_bytes(result_url)
    except Exception as e:
        logger.warning("Bild-Download für Asset fehlgeschlagen: %s", e)
        return

    step_data: dict[str, Any] = {
        "job_id": job_id,
        "provider_key": provider_key,
        "prompt": prompt,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    if negative_prompt:
        step_data["negative_prompt"] = negative_prompt
    if width is not None:
        step_data["width"] = width
    if height is not None:
        step_data["height"] = height

    update_step(
        asset_id,
        "image",
        step_data,
        file_bytes=image_bytes,
        filename="image_original.png",
    )
    logger.info("Asset %s: image step persisted", asset_id)


async def persist_bgremoval_job(
    job_id: str,
    asset_id: str,
    provider_key: str,
    source_file: str,
    result_url: str,
) -> None:
    """
    Speichert BgRemoval-Job-Output im Asset-Ordner.
    Nutzt lokale Datei falls URL auf /static/bgremoval zeigt, sonst Download.
    """
    local_path = _resolve_local_path_from_url(result_url)
    if local_path:
        file_bytes = local_path.read_bytes()
    else:
        try:
            file_bytes = await _download_bytes(result_url)
        except Exception as e:
            logger.warning("BgRemoval-Download für Asset fehlgeschlagen: %s", e)
            return

    step_data = {
        "job_id": job_id,
        "provider_key": provider_key,
        "source_file": source_file,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

    update_step(
        asset_id,
        "bgremoval",
        step_data,
        file_bytes=file_bytes,
        filename="image_bgremoved.png",
    )
    logger.info("Asset %s: bgremoval step persisted", asset_id)


async def persist_mesh_job(
    job_id: str,
    asset_id: str,
    provider_key: str,
    source_file: str,
    glb_file_path: str,
) -> None:
    """
    Speichert Mesh-Job-Output im Asset-Ordner.
    Kopiert GLB von MESH_STORAGE_PATH.
    """
    src = Path(glb_file_path)
    if not src.exists():
        logger.warning("GLB-Datei nicht gefunden: %s", glb_file_path)
        return

    file_bytes = src.read_bytes()
    step_data = {
        "job_id": job_id,
        "provider_key": provider_key,
        "source_file": source_file,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

    update_step(
        asset_id,
        "mesh",
        step_data,
        file_bytes=file_bytes,
        filename="mesh.glb",
    )
    logger.info("Asset %s: mesh step persisted", asset_id)


async def persist_rigging_job(
    job_id: str,
    asset_id: str,
    provider_key: str,
    source_file: str,
    glb_file_path: str,
) -> None:
    """
    Speichert Rigging-Job-Output im Asset-Ordner.
    Kopiert rigged GLB nach mesh_rigged.glb.
    """
    src = Path(glb_file_path)
    if not src.exists():
        logger.warning("Rigged GLB nicht gefunden: %s", glb_file_path)
        return

    file_bytes = src.read_bytes()
    step_data = {
        "job_id": job_id,
        "provider_key": provider_key,
        "source_file": source_file,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

    update_step(
        asset_id,
        "rigging",
        step_data,
        file_bytes=file_bytes,
        filename="mesh_rigged.glb",
    )
    logger.info("Asset %s: rigging step persisted", asset_id)


async def persist_animation_job(
    job_id: str,
    asset_id: str,
    provider_key: str,
    motion_prompt: str,
    source_file: str,
    animated_bytes: bytes,
    filename: str = "mesh_animated.glb",
) -> None:
    """
    Speichert Animation-Job-Output im Asset-Ordner.
    filename: mesh_animated.glb oder mesh_animated.fbx (je nach Provider-Ausgabe).
    """
    step_data: dict[str, Any] = {
        "job_id": job_id,
        "provider_key": provider_key,
        "motion_prompt": motion_prompt,
        "source_file": source_file,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

    update_step(
        asset_id,
        "animation",
        step_data,
        file_bytes=animated_bytes,
        filename=filename,
    )
    logger.info("Asset %s: animation step persisted", asset_id)


def get_or_create_asset_id(existing_asset_id: str | None) -> str:
    """Gibt existing_asset_id zurück oder erstellt neues Asset."""
    if existing_asset_id and get_asset(existing_asset_id):
        return existing_asset_id
    return create_asset()
