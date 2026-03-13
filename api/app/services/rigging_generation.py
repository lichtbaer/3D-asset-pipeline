"""
Orchestrierung der Rigging-Generierung: Download, Provider-Aufruf, Speicherung.
"""
import asyncio
import logging
from pathlib import Path
from typing import Awaitable, Callable

from app.config.storage import MESH_STORAGE_PATH
from app.exceptions import UniRigInvalidMeshError, UniRigTimeoutError
from app.logging_utils import log_job_error
from app.providers.rigging import get_rigging_provider
from app.providers.rigging.base import RiggingParams

logger = logging.getLogger(__name__)

# (job_id, status, glb_file_path, error_msg, *, error_type, error_detail)
UpdateRiggingJobCallback = Callable[..., Awaitable[None]]

RIGGING_TIMEOUT_SEC = 300


async def run_rigging(
    job_id: str,
    source_glb_url: str,
    provider_key: str,
    asset_id: str | None,
    update_job_callback: UpdateRiggingJobCallback,
) -> None:
    """
    Führt das Rigging über den konfigurierten Provider aus.
    """
    provider = get_rigging_provider(provider_key)
    params = RiggingParams(source_glb_url=source_glb_url, asset_id=asset_id)

    await update_job_callback(job_id, "processing", None, None)

    try:
        result = await asyncio.wait_for(
            provider.rig(params),
            timeout=RIGGING_TIMEOUT_SEC,
        )
    except asyncio.TimeoutError:
        err = f"Rigging timed out after {RIGGING_TIMEOUT_SEC}s"
        log_job_error(
            logger,
            "Rigging Timeout",
            job_id=job_id,
            provider_key=provider_key,
            error_type="UniRigTimeoutError",
            error_detail=err,
        )
        await update_job_callback(
            job_id,
            "failed",
            None,
            err,
            error_type="UniRigTimeoutError",
            error_detail=err,
        )
        return
    except UniRigTimeoutError as e:
        err = str(e)
        log_job_error(
            logger,
            "Rigging Timeout",
            job_id=job_id,
            provider_key=provider_key,
            error_type="UniRigTimeoutError",
            error_detail=err,
        )
        await update_job_callback(
            job_id,
            "failed",
            None,
            err,
            error_type="UniRigTimeoutError",
            error_detail=err,
        )
        return
    except UniRigInvalidMeshError as e:
        err = str(e)
        log_job_error(
            logger,
            "Rigging: Mesh nicht riggbar",
            job_id=job_id,
            provider_key=provider_key,
            error_type="UniRigInvalidMeshError",
            error_detail=err,
        )
        await update_job_callback(
            job_id,
            "failed",
            None,
            err,
            error_type="UniRigInvalidMeshError",
            error_detail=err,
        )
        return
    except ValueError as e:
        log_job_error(
            logger,
            "Rigging: ungültige Parameter",
            job_id=job_id,
            provider_key=provider_key,
            error_type="ValueError",
            error_detail=str(e),
        )
        await update_job_callback(
            job_id,
            "failed",
            None,
            str(e),
            error_type="ValueError",
            error_detail=str(e),
        )
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
        await update_job_callback(
            job_id,
            "failed",
            None,
            str(e),
            error_type=type(e).__name__,
            error_detail=str(e),
        )
        return

    # Speichere rigged GLB in MESH_STORAGE_PATH (analog zu mesh jobs)
    MESH_STORAGE_PATH.mkdir(parents=True, exist_ok=True)
    target_glb = MESH_STORAGE_PATH / f"{job_id}_rigged.glb"
    target_glb.write_bytes(result.rigged_glb_bytes)
    stored_path = str(target_glb)

    await update_job_callback(job_id, "done", stored_path, None)
