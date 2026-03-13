"""Hilfsfunktionen für strukturiertes Fehler-Logging."""

import logging
from uuid import UUID


def log_job_error(
    logger: logging.Logger,
    message: str,
    *,
    job_id: str | UUID,
    provider_key: str,
    error_type: str,
    error_detail: str,
    asset_id: str | UUID | None = None,
    exc_info: bool = True,
) -> None:
    """
    Loggt einen Job-Fehler mit allen Pflichtfeldern.
    exc_info=True fügt den aktuellen Exception-Traceback hinzu (wenn in except-Block).
    """
    extra = {
        "job_id": str(job_id),
        "provider_key": provider_key,
        "error_type": error_type,
        "error_detail": (error_detail[:500] if error_detail else ""),
        "asset_id": str(asset_id) if asset_id else None,
    }
    logger.error(message, extra=extra, exc_info=exc_info)
