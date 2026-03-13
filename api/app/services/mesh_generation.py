"""
Orchestrierung der Mesh-Generierung: Download, Provider-Aufruf, Speicherung.
"""
import asyncio
import logging
import os
import shutil
import tempfile
from pathlib import Path
from typing import Callable, Awaitable

import httpx

from app.config.storage import MESH_STORAGE_PATH
from app.services.mesh_providers import get_provider

logger = logging.getLogger(__name__)

# (job_id, status, glb_file_path, error_msg)
UpdateMeshJobCallback = Callable[[str, str, str | None, str | None], Awaitable[None]]


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

    hf_token = os.getenv("HF_TOKEN")
    if not hf_token:
        await update_job_callback(
            job_id,
            "failed",
            None,
            "HF_TOKEN nicht konfiguriert",
        )
        return

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
            await update_job_callback(
                job_id,
                "failed",
                None,
                "Timeout nach 300s – Mesh-Generierung nicht abgeschlossen",
            )
            return
        except ValueError as e:
            await update_job_callback(job_id, "failed", None, str(e))
            return
        except RuntimeError as e:
            await update_job_callback(job_id, "failed", None, str(e))
            return
        except Exception as e:
            logger.exception("%s Fehler", provider.display_name)
            await update_job_callback(job_id, "failed", None, str(e))
            return

        if not glb_path or not Path(glb_path).exists():
            await update_job_callback(
                job_id,
                "failed",
                None,
                f"{provider.display_name} lieferte keine GLB-Datei",
            )
            return

        # 4. GLB nach Storage kopieren
        shutil.copy2(glb_path, target_glb)
        stored_path = str(target_glb)

        # 5. DB aktualisieren
        await update_job_callback(job_id, "done", stored_path, None)

    except httpx.HTTPError as e:
        logger.exception("Bild-Download fehlgeschlagen")
        await update_job_callback(
            job_id,
            "failed",
            None,
            f"Bild-Download fehlgeschlagen: {str(e)}",
        )
    except Exception as e:
        logger.exception("Unerwarteter Fehler bei Mesh-Generierung")
        await update_job_callback(
            job_id,
            "failed",
            None,
            str(e),
        )
    finally:
        if temp_image_path and os.path.exists(temp_image_path):
            try:
                os.unlink(temp_image_path)
            except OSError:
                pass
