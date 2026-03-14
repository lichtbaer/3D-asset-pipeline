"""
Orchestrierung der Animation-Generierung: Provider-Aufruf, Speicherung.
"""
import asyncio
import logging
import os
from typing import Awaitable, Callable

from app.config.storage import ANIMATION_STORAGE_PATH
from app.logging_utils import log_job_error
from app.providers.animation import (
    AnimationParams,
    get_animation_provider,
)

logger = logging.getLogger(__name__)

# (job_id, status, glb_file_path, error_msg, *, error_type, error_detail)
UpdateAnimationJobCallback = Callable[..., Awaitable[None]]


async def run_animation(
    job_id: str,
    source_glb_url: str,
    motion_prompt: str,
    provider_key: str,
    asset_id: str | None,
    update_job_callback: UpdateAnimationJobCallback,
) -> None:
    """
    Führt die Animation-Generierung über den konfigurierten Provider aus.
    update_job_callback(job_id, status, glb_file_path, error_msg, ...)
    """
    try:
        provider = get_animation_provider(provider_key)
    except ValueError as e:
        await update_job_callback(
                job_id,
                "failed",
                None,
                str(e),
                error_type="ValueError",
                error_detail=str(e),
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
                job_id,
                "failed",
                None,
                err,
                error_type="ValueError",
                error_detail=err,
            )
        return

    await update_job_callback(job_id, "processing", None, None)

    try:
        params = AnimationParams(
            source_glb_url=source_glb_url,
            motion_prompt=motion_prompt,
            asset_id=str(asset_id) if asset_id else None,
        )
        result = await asyncio.wait_for(
            provider.animate(params),
            timeout=300,
        )
    except asyncio.TimeoutError:
        err = "Animation predict() timed out after 300s"
        log_job_error(
            logger,
            "Animation Timeout",
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
            "Animation: ungültige Parameter",
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
    except RuntimeError as e:
        log_job_error(
            logger,
            "Animation fehlgeschlagen",
            job_id=job_id,
            provider_key=provider_key,
            error_type="RuntimeError",
            error_detail=str(e),
        )
        await update_job_callback(
                job_id,
                "failed",
                None,
                str(e),
                error_type="RuntimeError",
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

    # Speichern in ANIMATION_STORAGE_PATH (für _persist_job_completion)
    ext = "fbx" if result.output_format == "fbx" else "glb"
    filename = f"{job_id}_animated.{ext}"
    ANIMATION_STORAGE_PATH.mkdir(parents=True, exist_ok=True)
    output_path = ANIMATION_STORAGE_PATH / filename
    output_path.write_bytes(result.animated_glb_bytes)

    await update_job_callback(job_id, "done", str(output_path), None)
