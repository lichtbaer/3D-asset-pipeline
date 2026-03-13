"""
Hunyuan3D-2 Mesh-Generierung via Hugging Face Space (gradio_client).
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

logger = logging.getLogger(__name__)

HUNYUAN_SPACE = "tencent/Hunyuan3D-2"
MESH_TIMEOUT_SEC = 300
STORAGE_MESHES = MESH_STORAGE_PATH

# (job_id, status, glb_file_path, error_msg)
UpdateMeshJobCallback = Callable[[str, str, str | None, str | None], Awaitable[None]]


def _run_hunyuan_predict(image_path: str, steps: int, hf_token: str) -> str | None:
    """
    Synchroner Aufruf von gradio_client (blockiert).
    Gibt den Pfad zur GLB-Datei zurück oder None bei Fehler.
    """
    from gradio_client import Client, handle_file

    client = Client(HUNYUAN_SPACE, hf_token=hf_token)
    result = client.predict(
        image=handle_file(image_path),
        steps=steps,
        api_name="/generation_all",
    )
    # /generation_all returns (file, file, output, mesh_stats, seed) — erste Datei ist GLB
    if result is None:
        return None
    if isinstance(result, (list, tuple)):
        for item in result:
            if item and isinstance(item, str) and (item.endswith(".glb") or item.endswith(".obj")):
                return item
        if result and result[0]:
            return str(result[0])
        return None
    return str(result) if result else None


async def run_mesh_generation(
    job_id: str,
    source_image_url: str,
    steps: int,
    update_job_callback: UpdateMeshJobCallback,
) -> None:
    """
    Führt die 3D-Mesh-Generierung via Hunyuan3D-2 HF Space aus.
    update_job_callback(job_id, status, glb_file_path=None, error_msg=None)
    """
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
        STORAGE_MESHES.mkdir(parents=True, exist_ok=True)
        target_glb = STORAGE_MESHES / f"{job_id}.glb"

        # 3. gradio_client (sync) in Thread mit Timeout ausführen
        try:
            glb_path = await asyncio.wait_for(
                asyncio.to_thread(_run_hunyuan_predict, temp_image_path, steps, hf_token),
                timeout=MESH_TIMEOUT_SEC,
            )
        except asyncio.TimeoutError:
            await update_job_callback(
                job_id,
                "failed",
                None,
                f"Timeout nach {MESH_TIMEOUT_SEC}s – Mesh-Generierung nicht abgeschlossen",
            )
            return
        except Exception as e:
            logger.exception("Hunyuan3D-2 Fehler")
            await update_job_callback(
                job_id,
                "failed",
                None,
                str(e),
            )
            return

        if not glb_path or not Path(glb_path).exists():
            await update_job_callback(
                job_id,
                "failed",
                None,
                "Hunyuan3D-2 lieferte keine GLB-Datei",
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
