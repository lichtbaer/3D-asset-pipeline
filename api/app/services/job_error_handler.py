"""Zentrales Error-Handling und Callback-Protokoll fuer Provider-Orchestrierung."""

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator, Protocol

from app.logging_utils import log_job_error
from app.models.enums import JobStatus


class UpdateJobCallback(Protocol):
    """Typsicheres Callback-Protokoll fuer Job-Status-Updates."""

    async def __call__(
        self,
        job_id: str,
        status: str,
        result_path: str | None,
        error_msg: str | None,
        *,
        error_type: str | None = None,
        error_detail: str | None = None,
    ) -> None: ...


async def _fail_job(
    logger: logging.Logger,
    message: str,
    job_id: str,
    provider_key: str,
    error_type: str,
    error: BaseException,
    update_job_callback: UpdateJobCallback,
) -> None:
    """Loggt Fehler und setzt Job-Status auf failed."""
    detail = str(error)
    log_job_error(
        logger,
        message,
        job_id=job_id,
        provider_key=provider_key,
        error_type=error_type,
        error_detail=detail,
    )
    await update_job_callback(
        job_id,
        JobStatus.FAILED,
        None,
        detail,
        error_type=error_type,
        error_detail=detail,
    )


@asynccontextmanager
async def handle_provider_errors(
    logger: logging.Logger,
    job_id: str,
    provider_key: str,
    update_job_callback: UpdateJobCallback,
    operation_name: str,
) -> AsyncIterator[None]:
    """Context Manager der Provider-Fehler einheitlich behandelt.

    Verwendung:
        async with handle_provider_errors(logger, job_id, pk, cb, "Mesh-Generierung"):
            result = await provider.generate(...)
    """
    try:
        yield
    except asyncio.TimeoutError as e:
        await _fail_job(
            logger,
            f"{operation_name} Timeout",
            job_id, provider_key,
            "ProviderTimeoutError", e,
            update_job_callback,
        )
    except ValueError as e:
        await _fail_job(
            logger,
            f"{operation_name}: ungueltige Parameter",
            job_id, provider_key,
            "ValueError", e,
            update_job_callback,
        )
    except RuntimeError as e:
        await _fail_job(
            logger,
            f"{operation_name} fehlgeschlagen",
            job_id, provider_key,
            "RuntimeError", e,
            update_job_callback,
        )
    except Exception as e:
        await _fail_job(
            logger,
            f"{operation_name} Fehler",
            job_id, provider_key,
            type(e).__name__, e,
            update_job_callback,
        )
