import asyncio
import logging
import os
from typing import Any, Callable, Awaitable

import httpx

from app.config.models import MODEL_MAP

logger = logging.getLogger(__name__)

PICSART_BASE_URL = "https://genai-api.picsart.io/v1"
POLL_INTERVAL_SEC = 2
POLL_TIMEOUT_SEC = 60

# (job_id, status, result_url, error_msg)
UpdateJobCallback = Callable[[str, str, str | None, str | None], Awaitable[None]]


async def run_image_generation(
    job_id: str,
    prompt: str,
    model_key: str,
    width: int,
    height: int,
    negative_prompt: str | None,
    update_job_callback: UpdateJobCallback,
) -> None:
    """
    Führt die Bildgenerierung via PicsArt API aus.
    update_job_callback(job_id, status, result_url=None, error_msg=None)
    """
    api_key = os.getenv("PICSART_API_KEY")
    if not api_key:
        await update_job_callback(
            job_id,
            "failed",
            None,
            "PICSART_API_KEY nicht konfiguriert",
        )
        return

    await update_job_callback(job_id, "processing", None, None)

    model_urn = MODEL_MAP.get(model_key)
    if model_key not in MODEL_MAP:
        await update_job_callback(
            job_id,
            "failed",
            None,
            f"Unbekannter model_key: {model_key}",
        )
        return

    request_body: dict[str, Any] = {
        "prompt": prompt,
        "width": width,
        "height": height,
        "count": 1,
    }
    if negative_prompt:
        request_body["negative_prompt"] = negative_prompt
    if model_urn is not None:
        request_body["model"] = model_urn

    headers = {
        "X-Picsart-API-Key": api_key,
        "accept": "application/json",
        "content-type": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{PICSART_BASE_URL}/text2image",
                headers=headers,
                json=request_body,
            )

            if response.status_code != 202:
                error_detail = response.text
                try:
                    err_json = response.json()
                    error_detail = err_json.get("message", str(err_json))
                except Exception:
                    pass
                await update_job_callback(
                    job_id,
                    "failed",
                    None,
                    f"PicsArt API Fehler ({response.status_code}): {error_detail}",
                )
                return

            data = response.json()
            transaction_id = data.get("transaction_id") or data.get("inference_id") or data.get("id")
            if not transaction_id:
                await update_job_callback(
                    job_id,
                    "failed",
                    None,
                    f"PicsArt API: Keine transaction_id in Response: {data}",
                )
                return

            result_url = await _poll_for_result(client, headers, transaction_id, job_id, update_job_callback)
            if result_url:
                await update_job_callback(job_id, "done", result_url, None)
            # Bei Timeout/Fehler wurde update_job_callback bereits in _poll_for_result aufgerufen

    except httpx.RequestError as e:
        logger.exception("PicsArt API Request-Fehler")
        await update_job_callback(
            job_id,
            "failed",
            None,
            f"Netzwerkfehler: {str(e)}",
        )
    except Exception as e:
        logger.exception("Unerwarteter Fehler bei Bildgenerierung")
        await update_job_callback(
            job_id,
            "failed",
            None,
            str(e),
        )


async def _poll_for_result(
    client: httpx.AsyncClient,
    headers: dict[str, str],
    transaction_id: str,
    job_id: str,
    update_job_callback: callable,
) -> str | None:
    """Pollt alle 2s, max 60s. Gibt result_url zurück oder None bei Fehler."""
    poll_url = f"{PICSART_BASE_URL}/text2image/{transaction_id}"
    # Alternative: /text2image/inferences/{id} falls PicsArt das verwendet
    alt_poll_url = f"{PICSART_BASE_URL}/text2image/inferences/{transaction_id}"

    elapsed = 0
    while elapsed < POLL_TIMEOUT_SEC:
        await asyncio.sleep(POLL_INTERVAL_SEC)
        elapsed += POLL_INTERVAL_SEC

        try:
            response = await client.get(poll_url, headers=headers)
            if response.status_code == 404:
                response = await client.get(alt_poll_url, headers=headers)
        except httpx.RequestError:
            try:
                response = await client.get(alt_poll_url, headers=headers)
            except httpx.RequestError as e:
                await update_job_callback(
                    job_id,
                    "failed",
                    None,
                    f"Poll Request-Fehler: {e}",
                )
                return None

        if response.status_code != 200:
            await update_job_callback(
                job_id,
                "failed",
                None,
                f"Poll-Fehler ({response.status_code}): {response.text}",
            )
            return None

        data = response.json()
        status = (data.get("status") or "").lower()

        if status in ("done", "completed", "success"):
            url = _extract_result_url(data)
            if url:
                return url
            await update_job_callback(
                job_id,
                "failed",
                None,
                "PicsArt: Keine result_url in fertiger Response",
            )
            return None

        if status in ("failed", "error"):
            await update_job_callback(
                job_id,
                "failed",
                None,
                data.get("message", data.get("error", "Unbekannter Fehler")),
            )
            return None

    await update_job_callback(
        job_id,
        "failed",
        None,
        f"Timeout nach {POLL_TIMEOUT_SEC}s – Bildgenerierung nicht abgeschlossen",
    )
    return None


def _extract_result_url(data: dict) -> str | None:
    """Extrahiert die Bild-URL aus der PicsArt-Response."""
    if "result_url" in data and data["result_url"]:
        return data["result_url"]
    if "url" in data and data["url"]:
        return data["url"]
    if "image_url" in data and data["image_url"]:
        return data["image_url"]
    if "images" in data and isinstance(data["images"], list) and len(data["images"]) > 0:
        img = data["images"][0]
        if isinstance(img, str):
            return img
        if isinstance(img, dict):
            return img.get("url") or img.get("result_url") or img.get("image_url")
    return None
