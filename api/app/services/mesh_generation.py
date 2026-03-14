"""
Orchestrierung der Mesh-Generierung: Download, Provider-Aufruf, Speicherung.
Optional: Background-Removal vor Mesh-Generierung (auto_bgremoval).
"""
import asyncio
import logging
import os
import shutil
import tempfile
from pathlib import Path
from typing import Awaitable, Callable

import httpx

from app.config.storage import MESH_STORAGE_PATH
from app.logging_utils import log_job_error
from app.services.mesh_providers import get_provider

logger = logging.getLogger(__name__)

# (job_id, status, glb_file_path, error_msg, *, error_type, error_detail)
UpdateMeshJobCallback = Callable[..., Awaitable[None]]

# (job_id, bgremoval_provider_key, bgremoval_result_url)
UpdateMeshJobBgRemovalCallback = Callable[
    [str, str, str], Awaitable[None]
]


async def run_mesh_generation(
    job_id: str,
    source_image_url: str,
    provider_key: str,
    params: dict,
    update_job_callback: UpdateMeshJobCallback,
) -> None:
    """
    Führt die 3D-Mesh-Generierung über den konfigurierten Provider aus.
    provider_key: z.B. "hunyuan3d-2", "triposr"
    params: provider-spezifische Parameter (werden mit default_params gemerged)
    """
    provider = get_provider(provider_key)
    merged_params = {**provider.default_params(), **params}

    await update_job_callback(job_id, "processing", None, None)

    temp_image_path: str | None = None

    try:
        # 1. Bild herunterladen
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.get(source_image_url)
            response.raise_for_status()
            image_bytes = response.content

        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            f.write(image_bytes)
            temp_image_path = f.name

        # 2. Storage-Verzeichnis anlegen
        MESH_STORAGE_PATH.mkdir(parents=True, exist_ok=True)
        target_glb = MESH_STORAGE_PATH / f"{job_id}.glb"

        # 3. Provider aufrufen (mit Timeout)
        try:
            glb_path = await asyncio.wait_for(
                provider.generate(temp_image_path, merged_params),
                timeout=300,
            )
        except asyncio.TimeoutError:
            err = "predict() timed out after 300s"
            log_job_error(
                logger,
                "Mesh-Generierung Timeout",
                job_id=job_id,
                provider_key=provider_key,
                error_type="ProviderTimeoutError",
                error_detail=err,
            )
            await update_job_callback(
                job_id,
                "failed",
                None,
                err,
                error_type="ProviderTimeoutError",
                error_detail=err,
            )
            return
        except ValueError as e:
            log_job_error(
                logger,
                "Mesh-Generierung: ungültige Parameter",
                job_id=job_id,
                provider_key=provider_key,
                error_type="ValueError",
                error_detail=str(e),
            )
            await update_job_callback(job_id, "failed", None, str(e), error_type="ValueError", error_detail=str(e))
            return
        except RuntimeError as e:
            log_job_error(
                logger,
                "Mesh-Generierung fehlgeschlagen",
                job_id=job_id,
                provider_key=provider_key,
                error_type="RuntimeError",
                error_detail=str(e),
            )
            await update_job_callback(job_id, "failed", None, str(e), error_type="RuntimeError", error_detail=str(e))
            return
        except Exception as e:
            log_job_error(
                logger,
                f"{provider.display_name} Fehler",
                job_id=job_id,
                provider_key=provider_key,
                error_type=type(e).__name__,
                error_detail=str(e),
            )
            await update_job_callback(job_id, "failed", None, str(e), error_type=type(e).__name__, error_detail=str(e))
            return

        if not glb_path or not Path(glb_path).exists():
            err = f"{provider.display_name} lieferte keine GLB-Datei"
            log_job_error(
                logger,
                "Mesh-Generierung: ungültige Provider-Antwort",
                job_id=job_id,
                provider_key=provider_key,
                error_type="ProviderInvalidResponseError",
                error_detail=err,
            )
            await update_job_callback(
                job_id,
                "failed",
                None,
                err,
                error_type="ProviderInvalidResponseError",
                error_detail=err,
            )
            return

        # 4. GLB nach Storage kopieren
        shutil.copy2(glb_path, target_glb)
        stored_path = str(target_glb)

        # 5. DB aktualisieren
        await update_job_callback(job_id, "done", stored_path, None)

    except httpx.HTTPError as e:
        err = f"Bild-Download fehlgeschlagen: {str(e)}"
        log_job_error(
            logger,
            "Mesh-Generierung: Bild-Download fehlgeschlagen",
            job_id=job_id,
            provider_key=provider_key,
            error_type=type(e).__name__,
            error_detail=err,
        )
        await update_job_callback(
            job_id,
            "failed",
            None,
            err,
            error_type=type(e).__name__,
            error_detail=err,
        )
    except Exception as e:
        log_job_error(
            logger,
            "Unerwarteter Fehler bei Mesh-Generierung",
            job_id=job_id,
            provider_key=provider_key,
            error_type=type(e).__name__,
            error_detail=str(e),
        )
        await update_job_callback(
            job_id,
            "failed",
            None,
            str(e),
            error_type=type(e).__name__,
            error_detail=str(e),
        )
    finally:
        if temp_image_path and os.path.exists(temp_image_path):
            try:
                os.unlink(temp_image_path)
            except OSError:
                pass


async def run_mesh_generation_with_auto_bgremoval(
    job_id: str,
    source_image_url: str,
    provider_key: str,
    params: dict,
    auto_bgremoval: bool,
    bgremoval_provider_key: str,
    update_job_callback: UpdateMeshJobCallback,
    update_bgremoval_callback: UpdateMeshJobBgRemovalCallback | None,
) -> None:
    """
    Führt optional Background-Removal durch, dann Mesh-Generierung.
    Wenn auto_bgremoval=True: zuerst BG-Removal, freigestelltes Bild für Mesh nutzen.
    """
    image_url_for_mesh = source_image_url

    if auto_bgremoval and update_bgremoval_callback:
        try:
            from app.services.bgremoval_providers import get_provider as get_bgremoval_provider

            provider = get_bgremoval_provider(bgremoval_provider_key)
            result_url = await provider.remove_background(
                source_image_url, job_id=job_id
            )
            await update_bgremoval_callback(job_id, bgremoval_provider_key, result_url)
            image_url_for_mesh = result_url
        except (ValueError, RuntimeError) as e:
            log_job_error(
                logger,
                "Background-Removal vor Mesh fehlgeschlagen",
                job_id=job_id,
                provider_key=bgremoval_provider_key,
                error_type=type(e).__name__,
                error_detail=str(e),
            )
            await update_job_callback(job_id, "failed", None, str(e), error_type=type(e).__name__, error_detail=str(e))
            return
        except Exception as e:
            log_job_error(
                logger,
                "Background-Removal vor Mesh fehlgeschlagen",
                job_id=job_id,
                provider_key=bgremoval_provider_key,
                error_type=type(e).__name__,
                error_detail=str(e),
            )
            await update_job_callback(job_id, "failed", None, str(e), error_type=type(e).__name__, error_detail=str(e))
            return

    await run_mesh_generation(
        job_id, image_url_for_mesh, provider_key, params, update_job_callback
    )
