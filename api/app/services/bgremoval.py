"""
Orchestrierung der Background-Removal: Provider-Aufruf, DB-Update.
"""
import logging
from typing import Callable, Awaitable

from app.services.bgremoval_providers import get_provider

logger = logging.getLogger(__name__)

# (job_id, status, result_url, error_msg)
UpdateBgRemovalJobCallback = Callable[
    [str, str, str | None, str | None], Awaitable[None]
]


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
        await update_job_callback(job_id, "failed", None, str(e))
        return

    await update_job_callback(job_id, "processing", None, None)

    try:
        result_url = await provider.remove_background(source_image_url)
        await update_job_callback(job_id, "done", result_url, None)
    except RuntimeError as e:
        logger.warning("Background-Removal fehlgeschlagen: %s", e)
        await update_job_callback(job_id, "failed", None, str(e))
    except Exception as e:
        logger.exception("Unerwarteter Fehler bei Background-Removal")
        await update_job_callback(job_id, "failed", None, str(e))
