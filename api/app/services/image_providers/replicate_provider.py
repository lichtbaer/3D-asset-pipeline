"""Replicate — Image-Provider."""

import logging
import os
from typing import Any

from app.exceptions import (
    ProviderConfigError,
    ReplicateAPIError,
    ReplicateModelError,
)
from app.services.image_providers.base import ImageProvider

logger = logging.getLogger(__name__)

AVAILABLE_MODELS: list[tuple[str, str]] = [
    ("black-forest-labs/flux-dev", "FLUX Dev"),
    ("black-forest-labs/flux-schnell", "FLUX Schnell"),
    ("stability-ai/sdxl", "SDXL"),
    ("ideogram-ai/ideogram-v2", "Ideogram v2"),
]

DEFAULT_MODEL = "black-forest-labs/flux-schnell"

PARAM_SCHEMA: dict = {
    "type": "object",
    "properties": {
        "model": {
            "type": "string",
            "default": DEFAULT_MODEL,
            "enum": [m[0] for m in AVAILABLE_MODELS],
            "enumLabels": {m[0]: m[1] for m in AVAILABLE_MODELS},
        },
        "width": {"type": "integer", "default": 1024, "minimum": 256, "maximum": 2048},
        "height": {"type": "integer", "default": 1024, "minimum": 256, "maximum": 2048},
        "negative_prompt": {"type": ["string", "null"], "default": None},
    },
    "required": ["model", "width", "height"],
}


class ReplicateImageProvider(ImageProvider):
    """Replicate — Zugriff auf hunderte kuratierte Modelle per owner/model-String."""

    provider_key = "replicate"
    display_name = "Replicate"

    def __init__(self) -> None:
        if not os.getenv("REPLICATE_API_TOKEN"):
            raise ProviderConfigError(
                "REPLICATE_API_TOKEN nicht konfiguriert — replicate Provider nicht verfügbar"
            )

    def default_params(self) -> dict:
        return {
            "model": DEFAULT_MODEL,
            "width": 1024,
            "height": 1024,
            "negative_prompt": None,
        }

    def param_schema(self) -> dict:
        return PARAM_SCHEMA.copy()

    async def generate(self, prompt: str, params: dict) -> str:
        """
        Generiert ein Bild via Replicate API.

        replicate.async_run() unterstützt async nativ — kein to_thread() nötig.
        Gibt die URL des generierten Bildes zurück.

        Raises:
            ReplicateModelError: Modell nicht gefunden
            ReplicateAPIError: Sonstiger API-Fehler
        """
        import replicate

        model = str(params.get("model", DEFAULT_MODEL))
        width = int(params.get("width", 1024))
        height = int(params.get("height", 1024))
        negative_prompt = params.get("negative_prompt") or None

        input_params: dict[str, Any] = {
            "prompt": prompt,
            "width": width,
            "height": height,
            "num_outputs": 1,
        }
        if negative_prompt:
            input_params["negative_prompt"] = negative_prompt

        try:
            output = await replicate.async_run(model, input=input_params)
        except Exception as e:
            err_lower = str(e).lower()
            if any(
                kw in err_lower
                for kw in ("not found", "does not exist", "404", "no such model", "invalid version")
            ):
                raise ReplicateModelError(status_code=404, body=str(e)) from e
            raise ReplicateAPIError(status_code=500, body=str(e)) from e

        url = _extract_url(output)
        if not url:
            raise ReplicateAPIError(
                status_code=500,
                body=f"Keine URL in Replicate-Ausgabe: {output!r}",
            )

        return url


def _extract_url(output: Any) -> str | None:
    """Extrahiert Bild-URL aus Replicate-Output (URL-String, Liste oder FileOutput)."""
    if output is None:
        return None

    if isinstance(output, str) and output.startswith("http"):
        return output

    if isinstance(output, (list, tuple)) and output:
        first = output[0]
        if isinstance(first, str) and first.startswith("http"):
            return first
        if hasattr(first, "url"):
            url = first.url
            return str(url) if url else None
        return str(first) if first else None

    if hasattr(output, "url"):
        url = output.url
        return str(url) if url else None

    return None
