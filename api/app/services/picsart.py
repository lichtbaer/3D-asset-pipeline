"""PicsArt Bildgenerierung — nutzt Image-Provider-Abstraktion."""

import logging
from typing import Any, Awaitable, Callable

from app.logging_utils import log_job_error
from app.services.image_providers import get_provider

logger = logging.getLogger(__name__)

# (job_id, status, result_url, error_msg, *, error_type, error_detail)
UpdateJobCallback = Callable[..., Awaitable[None]]


async def run_image_generation(
    job_id: str,
    prompt: str,
    provider_key: str,
    params: dict[str, Any],
    update_job_callback: UpdateJobCallback,
) -> None:
    """
    Führt die Bildgenerierung via Image-Provider aus.
    update_job_callback(job_id, status, result_url=None, error_msg=None, error_type=..., error_detail=...)
    """
    try:
        provider = get_provider(provider_key)
    except ValueError as e:
        log_job_error(
            logger,
            "Unbekannter Image-Provider",
            job_id=job_id,
            provider_key=provider_key,
            error_type="ValueError",
            error_detail=str(e),
        )
        await update_job_callback(job_id, "failed", None, str(e), error_type="ValueError", error_detail=str(e))
        return

    await update_job_callback(job_id, "processing", None, None)

    try:
        result_url = await provider.generate(prompt, params)
        await update_job_callback(job_id, "done", result_url, None)
    except RuntimeError as e:
        log_job_error(
            logger,
            "Bildgenerierung fehlgeschlagen",
            job_id=job_id,
            provider_key=provider_key,
            error_type="RuntimeError",
            error_detail=str(e),
        )
        await update_job_callback(job_id, "failed", None, str(e), error_type="RuntimeError", error_detail=str(e))
    except Exception as e:
        log_job_error(
            logger,
            "Unerwarteter Fehler bei Bildgenerierung",
            job_id=job_id,
            provider_key=provider_key,
            error_type=type(e).__name__,
            error_detail=str(e),
        )
        await update_job_callback(job_id, "failed", None, str(e), error_type=type(e).__name__, error_detail=str(e))
