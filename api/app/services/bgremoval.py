"""
Orchestrierung der Background-Removal: Provider-Aufruf, DB-Update.
"""
import logging

from app.logging_utils import log_job_error
from app.models.enums import JobStatus
from app.services.bgremoval_providers import get_provider
from app.services.job_error_handler import UpdateJobCallback, handle_provider_errors

logger = logging.getLogger(__name__)


async def run_bgremoval(
    job_id: str,
    source_image_url: str,
    provider_key: str,
    update_job_callback: UpdateJobCallback,
) -> None:
    """
    Fuehrt Background-Removal ueber den konfigurierten Provider aus.
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
        await update_job_callback(
            job_id, JobStatus.FAILED, None, str(e),
            error_type="ValueError", error_detail=str(e),
        )
        return

    await update_job_callback(job_id, JobStatus.PROCESSING, None, None)

    async with handle_provider_errors(
        logger, job_id, provider_key, update_job_callback, "Background-Removal"
    ):
        result_url = await provider.remove_background(
            source_image_url, job_id=job_id
        )
        await update_job_callback(job_id, JobStatus.DONE, result_url, None)
