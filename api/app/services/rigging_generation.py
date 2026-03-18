"""
Orchestrierung der Rigging-Generierung: Download, Provider-Aufruf, Speicherung.
"""
import asyncio
import logging

from app.config.storage import MESH_STORAGE_PATH
from app.models.enums import JobStatus
from app.providers.rigging import get_rigging_provider
from app.providers.rigging.base import RiggingParams
from app.services.job_error_handler import UpdateJobCallback, handle_provider_errors

logger = logging.getLogger(__name__)

RIGGING_TIMEOUT_SEC = 300


async def run_rigging(
    job_id: str,
    source_glb_url: str,
    provider_key: str,
    asset_id: str | None,
    update_job_callback: UpdateJobCallback,
) -> None:
    """
    Fuehrt das Rigging ueber den konfigurierten Provider aus.
    """
    provider = get_rigging_provider(provider_key)
    params = RiggingParams(source_glb_url=source_glb_url, asset_id=asset_id)

    await update_job_callback(job_id, JobStatus.PROCESSING, None, None)

    result = None
    async with handle_provider_errors(
        logger, job_id, provider_key, update_job_callback, provider.display_name
    ):
        result = await asyncio.wait_for(
            provider.rig(params),
            timeout=RIGGING_TIMEOUT_SEC,
        )

    if result is None:
        return  # Fehler wurde vom Context Manager behandelt

    # Speichere rigged GLB in MESH_STORAGE_PATH (analog zu mesh jobs)
    MESH_STORAGE_PATH.mkdir(parents=True, exist_ok=True)
    target_glb = MESH_STORAGE_PATH / f"{job_id}_rigged.glb"
    target_glb.write_bytes(result.rigged_glb_bytes)
    stored_path = str(target_glb)

    await update_job_callback(job_id, JobStatus.DONE, stored_path, None)
