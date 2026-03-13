"""Hugging Face Inference API — Image-Provider."""

import asyncio
import io
import logging
import os
import uuid

from app.config.storage import IMAGE_STORAGE_PATH
from app.exceptions import (
    HFInferenceError,
    HFModelNotAvailableError,
    ProviderConfigError,
)
from app.services.image_providers.base import ImageProvider

logger = logging.getLogger(__name__)

AVAILABLE_MODELS: list[tuple[str, str]] = [
    ("black-forest-labs/FLUX.1-dev", "FLUX.1-dev"),
    ("black-forest-labs/FLUX.1-schnell", "FLUX.1-schnell"),
    ("stabilityai/stable-diffusion-3.5-large", "SD 3.5 Large"),
    ("stabilityai/stable-diffusion-xl-base-1.0", "SDXL 1.0"),
]

DEFAULT_MODEL = "black-forest-labs/FLUX.1-schnell"

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


class HFInferenceImageProvider(ImageProvider):
    """Hugging Face Inference API — breites Modell-Angebot (FLUX, SD3, SDXL)."""

    provider_key = "hf-inference"
    display_name = "Hugging Face Inference API"

    def __init__(self) -> None:
        token = os.getenv("HF_TOKEN")
        if not token:
            raise ProviderConfigError(
                "HF_TOKEN nicht konfiguriert — hf-inference Provider nicht verfügbar"
            )
        from huggingface_hub import InferenceClient

        self._client = InferenceClient(token=token)

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
        Generiert ein Bild via HF Inference API.

        InferenceClient.text_to_image() ist synchron → asyncio.to_thread().
        Gibt statische URL des lokal gespeicherten PNG zurück.

        Raises:
            HFModelNotAvailableError: Modell nicht vorhanden / nicht verfügbar
            HFInferenceError: Sonstiger API-Fehler
        """
        model = str(params.get("model", DEFAULT_MODEL))
        width = int(params.get("width", 1024))
        height = int(params.get("height", 1024))
        negative_prompt = params.get("negative_prompt") or None

        try:
            pil_image = await asyncio.to_thread(
                self._call_api,
                prompt,
                model,
                negative_prompt,
                width,
                height,
            )
        except (HFModelNotAvailableError, HFInferenceError):
            raise
        except Exception as e:
            raise HFInferenceError(status_code=500, body=str(e)) from e

        IMAGE_STORAGE_PATH.mkdir(parents=True, exist_ok=True)
        file_id = str(uuid.uuid4())
        output_path = IMAGE_STORAGE_PATH / f"{file_id}.png"

        buf = io.BytesIO()
        pil_image.save(buf, format="PNG")
        output_path.write_bytes(buf.getvalue())

        base_url = os.getenv("API_BASE_URL", "http://localhost:8000")
        return f"{base_url.rstrip('/')}/static/images/{file_id}.png"

    def _call_api(
        self,
        prompt: str,
        model: str,
        negative_prompt: str | None,
        width: int,
        height: int,
    ) -> object:
        """
        Synchroner HF Inference API-Aufruf.
        Wird via asyncio.to_thread() aufgerufen um Event-Loop nicht zu blockieren.
        """
        try:
            return self._client.text_to_image(
                prompt=prompt,
                model=model,
                negative_prompt=negative_prompt,
                width=width,
                height=height,
            )
        except Exception as e:
            err_lower = str(e).lower()
            if any(
                kw in err_lower
                for kw in ("not found", "does not exist", "unavailable", "404", "no such model")
            ):
                raise HFModelNotAvailableError(status_code=404, body=str(e)) from e
            raise HFInferenceError(status_code=500, body=str(e)) from e
