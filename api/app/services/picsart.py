"""PicsArt Bildgenerierung — nutzt Image-Provider-Abstraktion."""

import logging
from typing import Callable, Awaitable

from app.services.image_providers import get_provider

logger = logging.getLogger(__name__)

# (job_id, status, result_url, error_msg)
UpdateJobCallback = Callable[[str, str, str | None, str | None], Awaitable[None]]


async def run_image_generation(
    job_id: str,
    prompt: str,
    provider_key: str,
    params: dict,
    update_job_callback: UpdateJobCallback,
) -> None:
    """
    Führt die Bildgenerierung via Image-Provider aus.
    update_job_callback(job_id, status, result_url=None, error_msg=None)
    """
    try:
        provider = get_provider(provider_key)
    except ValueError as e:
        await update_job_callback(
            job_id,
            "failed",
            None,
            str(e),
        )
        return

    await update_job_callback(job_id, "processing", None, None)

    try:
        result_url = await provider.generate(prompt, params)
        await update_job_callback(job_id, "done", result_url, None)
    except RuntimeError as e:
        logger.exception("Bildgenerierung fehlgeschlagen")
        await update_job_callback(job_id, "failed", None, str(e))
    except Exception as e:
        logger.exception("Unerwarteter Fehler bei Bildgenerierung")
        await update_job_callback(job_id, "failed", None, str(e))
