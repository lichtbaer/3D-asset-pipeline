"""
Asset-Persistenz: persist_*_job Funktionen für Pipeline-Step-Outputs.
Speichert Job-Ergebnisse (Bild, BgRemoval, Mesh, Rigging, Animation) im Asset-Ordner.
"""

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

from app.config.storage import BGREMOVAL_STORAGE_PATH
from app.services.asset_service import update_step

logger = logging.getLogger(__name__)


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
    except (httpx.HTTPStatusError, httpx.RequestError, OSError) as e:
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

    await update_step(
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
        except (httpx.HTTPStatusError, httpx.RequestError, OSError) as e:
            logger.warning("BgRemoval-Download für Asset fehlgeschlagen: %s", e)
            return

    step_data = {
        "job_id": job_id,
        "provider_key": provider_key,
        "source_file": source_file,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

    await update_step(
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

    await update_step(
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

    await update_step(
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

    await update_step(
        asset_id,
        "animation",
        step_data,
        file_bytes=animated_bytes,
        filename=filename,
    )
    logger.info("Asset %s: animation step persisted", asset_id)
