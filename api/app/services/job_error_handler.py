"""Zentrales Error-Handling und Callback-Protokoll fuer Provider-Orchestrierung."""

import asyncio
import logging
from collections.abc import Callable, Coroutine
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator, Protocol, TypeVar

import httpx

from app.logging_utils import log_job_error
from app.models.enums import JobStatus

T = TypeVar("T")

# Transiente Fehler-Typen, bei denen ein Retry sinnvoll ist
_TRANSIENT_EXCEPTIONS = (
    asyncio.TimeoutError,
    httpx.TimeoutException,
    httpx.NetworkError,
    httpx.RemoteProtocolError,
)


def _is_transient_http_error(exc: BaseException) -> bool:
    """True für 5xx-Antworten (Server-seitige Fehler, potenziell transient)."""
    return (
        isinstance(exc, httpx.HTTPStatusError)
        and exc.response.status_code >= 500
    )


async def with_retry(
    coro_fn: Callable[[], Coroutine[Any, Any, T]],
    *,
    max_attempts: int = 3,
    base_delay_s: float = 5.0,
    logger: logging.Logger | None = None,
    operation_name: str = "Operation",
) -> T:
    """Führt coro_fn mit Exponential Backoff bei transienten Fehlern aus.

    Wird nur bei transienten Fehlern wiederholt (Timeout, Netzwerk, HTTP 5xx).
    Nicht-transiente Fehler (ValueError, HTTP 4xx) werden sofort weitergegeben.

    Args:
        coro_fn: Aufrufbare, die eine neue Coroutine erzeugt (z.B. ``lambda: provider.generate(...)``).
        max_attempts: Maximale Anzahl Versuche (1 = kein Retry).
        base_delay_s: Wartezeit in Sekunden nach dem ersten Fehler; verdoppelt sich pro Versuch.
        logger: Logger für Retry-Meldungen (optional).
        operation_name: Beschreibender Name für Log-Meldungen.

    Returns:
        Rückgabewert der Coroutine.

    Raises:
        Letzter aufgetretener Fehler nach Erschöpfung aller Versuche.
    """
    _logger = logger or logging.getLogger(__name__)
    last_exc: BaseException | None = None

    for attempt in range(1, max_attempts + 1):
        try:
            return await coro_fn()
        except BaseException as exc:
            is_transient = isinstance(exc, _TRANSIENT_EXCEPTIONS) or _is_transient_http_error(exc)

            if not is_transient or attempt == max_attempts:
                raise

            delay = base_delay_s * (2 ** (attempt - 1))
            _logger.warning(
                "%s: transienter Fehler (Versuch %d/%d), Retry in %.1fs — %s: %s",
                operation_name,
                attempt,
                max_attempts,
                delay,
                type(exc).__name__,
                exc,
            )
            last_exc = exc
            await asyncio.sleep(delay)

    # Wird nur erreicht wenn max_attempts == 0 (defensiv)
    raise last_exc or RuntimeError("with_retry: keine Versuche konfiguriert")


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
    except Exception as e:  # Intentional catch-all: final safety net for unexpected errors
        await _fail_job(
            logger,
            f"{operation_name} Fehler",
            job_id, provider_key,
            type(e).__name__, e,
            update_job_callback,
        )
