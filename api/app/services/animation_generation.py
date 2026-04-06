"""
Orchestrierung der Animation-Generierung: Provider-Aufruf, Speicherung.
"""
import asyncio
import logging
import os

from app.config.storage import ANIMATION_STORAGE_PATH
from app.core.config import settings
from app.logging_utils import log_job_error
from app.models.enums import JobStatus
from app.providers.animation import (
    AnimationParams,
    get_animation_provider,
)
from app.services.job_error_handler import UpdateJobCallback, handle_provider_errors

logger = logging.getLogger(__name__)


async def run_animation(
    job_id: str,
    source_glb_url: str,
    motion_prompt: str,
    provider_key: str,
    asset_id: str | None,
    update_job_callback: UpdateJobCallback,
) -> None:
    """
    Fuehrt die Animation-Generierung ueber den konfigurierten Provider aus.
    update_job_callback(job_id, status, glb_file_path, error_msg, ...)
    """
    try:
        provider = get_animation_provider(provider_key)
    except ValueError as e:
        await update_job_callback(
            job_id, JobStatus.FAILED, None, str(e),
            error_type="ValueError", error_detail=str(e),
        )
        return

    hf_token = os.getenv("HF_TOKEN")
    if not hf_token:
        err = "HF_TOKEN nicht konfiguriert"
        log_job_error(
            logger,
            "Animation: HF_TOKEN fehlt",
            job_id=job_id,
            provider_key=provider_key,
            error_type="ValueError",
            error_detail=err,
        )
        await update_job_callback(
            job_id, JobStatus.FAILED, None, err,
            error_type="ValueError", error_detail=err,
        )
        return

    await update_job_callback(job_id, JobStatus.PROCESSING, None, None)

    result = None
    async with handle_provider_errors(
        logger, job_id, provider_key, update_job_callback, provider.display_name
    ):
        params = AnimationParams(
            source_glb_url=source_glb_url,
            motion_prompt=motion_prompt,
            asset_id=str(asset_id) if asset_id else None,
        )
        result = await asyncio.wait_for(
            provider.animate(params),
            timeout=settings.ANIMATION_TIMEOUT_S,
        )

    if result is None:
        return  # Fehler wurde vom Context Manager behandelt

    # Speichern in ANIMATION_STORAGE_PATH
    ext = "fbx" if result.output_format == "fbx" else "glb"
    filename = f"{job_id}_animated.{ext}"
    ANIMATION_STORAGE_PATH.mkdir(parents=True, exist_ok=True)
    output_path = ANIMATION_STORAGE_PATH / filename
    output_path.write_bytes(result.animated_glb_bytes)

    await update_job_callback(job_id, JobStatus.DONE, str(output_path), None)
