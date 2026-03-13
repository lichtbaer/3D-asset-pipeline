"""
Orchestrierung der Background-Removal: Provider-Aufruf, DB-Update.
"""
import logging
from typing import Awaitable, Callable

from app.logging_utils import log_job_error
from app.services.bgremoval_providers import get_provider

logger = logging.getLogger(__name__)

# (job_id, status, result_url, error_msg, *, error_type, error_detail)
UpdateBgRemovalJobCallback = Callable[..., Awaitable[None]]


async def run_bgremoval(
    job_id: str,
    source_image_url: str,
    provider_key: str,
    update_job_callback: UpdateBgRemovalJobCallback,
) -> None:
    """
    Führt Background-Removal über den konfigurierten Provider aus.
    """
    try:
        provider = get_provider(provider_key)
    except ValueError as e:
        log_job_error(
            logger,
            "Unbekannter BgRemoval-Provider",
            job_id=job_id,
            provider_key=provider_key,
            error_type="ValueError",
            error_detail=str(e),
        )
        await update_job_callback(job_id, "failed", None, str(e), error_type="ValueError", error_detail=str(e))
        return

    await update_job_callback(job_id, "processing", None, None)

    try:
        result_url = await provider.remove_background(
            source_image_url, job_id=job_id
        )
        await update_job_callback(job_id, "done", result_url, None)
    except RuntimeError as e:
        log_job_error(
            logger,
            "Background-Removal fehlgeschlagen",
            job_id=job_id,
            provider_key=provider_key,
            error_type="RuntimeError",
            error_detail=str(e),
        )
        await update_job_callback(job_id, "failed", None, str(e), error_type="RuntimeError", error_detail=str(e))
    except Exception as e:
        log_job_error(
            logger,
            "Unerwarteter Fehler bei Background-Removal",
            job_id=job_id,
            provider_key=provider_key,
            error_type=type(e).__name__,
            error_detail=str(e),
        )
        await update_job_callback(job_id, "failed", None, str(e), error_type=type(e).__name__, error_detail=str(e))
