"""Unit-Tests für with_retry in job_error_handler."""

import asyncio
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from app.services.job_error_handler import with_retry


# ---------------------------------------------------------------------------
# Hilfsfunktionen
# ---------------------------------------------------------------------------


def _make_httpx_status_error(status_code: int) -> httpx.HTTPStatusError:
    request = httpx.Request("GET", "http://example.com")
    response = httpx.Response(status_code, request=request)
    return httpx.HTTPStatusError("error", request=request, response=response)


# ---------------------------------------------------------------------------
# Erfolgreiche Ausführung
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_with_retry_returns_result_on_success():
    """Gibt Rückgabewert der Coroutine zurück wenn kein Fehler auftritt."""
    mock_fn = AsyncMock(return_value="ok")
    result = await with_retry(mock_fn, max_attempts=3)
    assert result == "ok"
    mock_fn.assert_called_once()


# ---------------------------------------------------------------------------
# Retry bei transienten Fehlern
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_with_retry_retries_on_timeout():
    """Wiederholt den Aufruf bei asyncio.TimeoutError (transient)."""
    call_count = 0

    async def flaky():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise asyncio.TimeoutError()
        return "done"

    with patch("asyncio.sleep", new_callable=AsyncMock):
        result = await with_retry(flaky, max_attempts=3, base_delay_s=0.0)

    assert result == "done"
    assert call_count == 3


@pytest.mark.asyncio
async def test_with_retry_retries_on_httpx_timeout():
    """Wiederholt bei httpx.TimeoutException."""
    call_count = 0

    async def flaky():
        nonlocal call_count
        call_count += 1
        if call_count < 2:
            raise httpx.TimeoutException("timeout")
        return "done"

    with patch("asyncio.sleep", new_callable=AsyncMock):
        result = await with_retry(flaky, max_attempts=3, base_delay_s=0.0)

    assert result == "done"
    assert call_count == 2


@pytest.mark.asyncio
async def test_with_retry_retries_on_5xx():
    """Wiederholt bei HTTP 5xx-Fehler."""
    call_count = 0

    async def flaky():
        nonlocal call_count
        call_count += 1
        if call_count < 2:
            raise _make_httpx_status_error(503)
        return "done"

    with patch("asyncio.sleep", new_callable=AsyncMock):
        result = await with_retry(flaky, max_attempts=3, base_delay_s=0.0)

    assert result == "done"
    assert call_count == 2


# ---------------------------------------------------------------------------
# Kein Retry bei nicht-transienten Fehlern
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_with_retry_no_retry_on_value_error():
    """Kein Retry bei ValueError (nicht transient)."""
    call_count = 0

    async def always_invalid():
        nonlocal call_count
        call_count += 1
        raise ValueError("bad params")

    with pytest.raises(ValueError, match="bad params"):
        await with_retry(always_invalid, max_attempts=3)

    assert call_count == 1


@pytest.mark.asyncio
async def test_with_retry_no_retry_on_4xx():
    """Kein Retry bei HTTP 4xx (Client-Fehler)."""
    call_count = 0

    async def client_error():
        nonlocal call_count
        call_count += 1
        raise _make_httpx_status_error(400)

    with pytest.raises(httpx.HTTPStatusError):
        await with_retry(client_error, max_attempts=3)

    assert call_count == 1


# ---------------------------------------------------------------------------
# Erschöpfung aller Versuche
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_with_retry_raises_after_max_attempts():
    """Wirft Fehler nach Erschöpfung aller Versuche."""
    call_count = 0

    async def always_timeout():
        nonlocal call_count
        call_count += 1
        raise asyncio.TimeoutError()

    with patch("asyncio.sleep", new_callable=AsyncMock):
        with pytest.raises(asyncio.TimeoutError):
            await with_retry(always_timeout, max_attempts=3, base_delay_s=0.0)

    assert call_count == 3


# ---------------------------------------------------------------------------
# Exponential Backoff
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_with_retry_exponential_backoff():
    """Wartezeit verdoppelt sich pro Versuch."""
    sleep_calls: list[float] = []

    async def fake_sleep(delay: float) -> None:
        sleep_calls.append(delay)

    async def always_timeout():
        raise asyncio.TimeoutError()

    with patch("asyncio.sleep", side_effect=fake_sleep):
        with pytest.raises(asyncio.TimeoutError):
            await with_retry(always_timeout, max_attempts=3, base_delay_s=5.0)

    # 2 Sleeps (nach Versuch 1 und 2; nach Versuch 3 kein Sleep)
    assert len(sleep_calls) == 2
    assert sleep_calls[0] == 5.0   # base_delay * 2^0
    assert sleep_calls[1] == 10.0  # base_delay * 2^1


# ---------------------------------------------------------------------------
# max_attempts=1 (kein Retry)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_with_retry_max_attempts_1_no_retry():
    """Mit max_attempts=1 wird kein Retry durchgeführt."""
    call_count = 0

    async def always_timeout():
        nonlocal call_count
        call_count += 1
        raise asyncio.TimeoutError()

    with pytest.raises(asyncio.TimeoutError):
        await with_retry(always_timeout, max_attempts=1)

    assert call_count == 1
