"""PicsArt Bildgenerierung — nutzt Image-Provider-Abstraktion."""

import logging
from typing import Any

from app.logging_utils import log_job_error
from app.models.enums import JobStatus
from app.services.image_providers import get_provider
from app.services.job_error_handler import UpdateJobCallback, handle_provider_errors

logger = logging.getLogger(__name__)


async def run_image_generation(
    job_id: str,
    prompt: str,
    provider_key: str,
    params: dict[str, Any],
    update_job_callback: UpdateJobCallback,
) -> None:
    """
    Fuehrt die Bildgenerierung via Image-Provider aus.
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
        await update_job_callback(
            job_id, JobStatus.FAILED, None, str(e),
            error_type="ValueError", error_detail=str(e),
        )
        return

    await update_job_callback(job_id, JobStatus.PROCESSING, None, None)

    async with handle_provider_errors(
        logger, job_id, provider_key, update_job_callback, "Bildgenerierung"
    ):
        result_url = await provider.generate(prompt, params)
        await update_job_callback(job_id, JobStatus.DONE, result_url, None)
