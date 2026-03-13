"""Unit-Tests für den HF Inference Image-Provider."""

import io
import os
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.exceptions import (
    HFInferenceError,
    HFModelNotAvailableError,
    ProviderConfigError,
)


class TestHFInferenceProviderInit:
    def test_raises_config_error_without_token(self, monkeypatch):
        monkeypatch.delenv("HF_TOKEN", raising=False)
        # Modul-Cache leeren, damit Import-Zeitlogik neu ausgeführt wird
        import importlib
        import app.services.image_providers.hf_inference as mod
        importlib.reload(mod)
        with pytest.raises(ProviderConfigError, match="HF_TOKEN"):
            mod.HFInferenceImageProvider()

    def test_creates_provider_with_token(self, monkeypatch):
        monkeypatch.setenv("HF_TOKEN", "hf_testtoken123")
        with patch("huggingface_hub.InferenceClient"):
            import importlib
            import app.services.image_providers.hf_inference as mod
            importlib.reload(mod)
            provider = mod.HFInferenceImageProvider()
            assert provider.provider_key == "hf-inference"
            assert provider.display_name == "Hugging Face Inference API"

    def test_default_params(self, monkeypatch):
        monkeypatch.setenv("HF_TOKEN", "hf_testtoken123")
        with patch("huggingface_hub.InferenceClient"):
            import importlib
            import app.services.image_providers.hf_inference as mod
            importlib.reload(mod)
            provider = mod.HFInferenceImageProvider()
            params = provider.default_params()
            assert params["width"] == 1024
            assert params["height"] == 1024
            assert params["model"] == "black-forest-labs/FLUX.1-schnell"
            assert params["negative_prompt"] is None

    def test_param_schema(self, monkeypatch):
        monkeypatch.setenv("HF_TOKEN", "hf_testtoken123")
        with patch("huggingface_hub.InferenceClient"):
            import importlib
            import app.services.image_providers.hf_inference as mod
            importlib.reload(mod)
            provider = mod.HFInferenceImageProvider()
            schema = provider.param_schema()
            assert "model" in schema["properties"]
            assert "width" in schema["properties"]
            assert "height" in schema["properties"]
            assert "negative_prompt" in schema["properties"]
            assert "black-forest-labs/FLUX.1-schnell" in schema["properties"]["model"]["enum"]


class TestHFInferenceProviderGenerate:
    def _make_provider(self, monkeypatch):
        monkeypatch.setenv("HF_TOKEN", "hf_testtoken123")
        monkeypatch.setenv("API_BASE_URL", "http://testserver")
        with patch("huggingface_hub.InferenceClient"):
            import importlib
            import app.services.image_providers.hf_inference as mod
            importlib.reload(mod)
            provider = mod.HFInferenceImageProvider()
        return provider

    @pytest.mark.asyncio
    async def test_generate_returns_static_url(self, monkeypatch, tmp_path):
        provider = self._make_provider(monkeypatch)
        monkeypatch.setenv("API_BASE_URL", "http://testserver")

        fake_image = MagicMock()
        buf_holder = {}

        def fake_save(buf, format):
            buf.write(b"PNG_DATA")
            buf_holder["written"] = True

        fake_image.save = fake_save

        with (
            patch(
                "app.services.image_providers.hf_inference.IMAGE_STORAGE_PATH",
                tmp_path,
            ),
            patch(
                "app.services.image_providers.hf_inference.asyncio.to_thread",
                new_callable=AsyncMock,
                return_value=fake_image,
            ),
        ):
            url = await provider.generate(
                "a cat",
                {"model": "black-forest-labs/FLUX.1-schnell", "width": 512, "height": 512},
            )

        assert url.startswith("http://testserver/static/images/")
        assert url.endswith(".png")

    @pytest.mark.asyncio
    async def test_generate_raises_hf_inference_error_on_api_failure(
        self, monkeypatch, tmp_path
    ):
        provider = self._make_provider(monkeypatch)

        async def raise_error(*args, **kwargs):
            raise RuntimeError("Internal server error")

        with (
            patch(
                "app.services.image_providers.hf_inference.IMAGE_STORAGE_PATH",
                tmp_path,
            ),
            patch(
                "app.services.image_providers.hf_inference.asyncio.to_thread",
                side_effect=HFInferenceError(status_code=500, body="Internal server error"),
            ),
        ):
            with pytest.raises(HFInferenceError):
                await provider.generate("a cat", {})

    @pytest.mark.asyncio
    async def test_generate_raises_model_not_available(self, monkeypatch, tmp_path):
        provider = self._make_provider(monkeypatch)

        with (
            patch(
                "app.services.image_providers.hf_inference.IMAGE_STORAGE_PATH",
                tmp_path,
            ),
            patch(
                "app.services.image_providers.hf_inference.asyncio.to_thread",
                side_effect=HFModelNotAvailableError(status_code=404, body="Model not found"),
            ),
        ):
            with pytest.raises(HFModelNotAvailableError):
                await provider.generate("a cat", {"model": "nonexistent/model"})

    def test_call_api_raises_model_not_available_on_404(self, monkeypatch):
        provider = self._make_provider(monkeypatch)
        provider._client.text_to_image = MagicMock(
            side_effect=Exception("Model not found 404")
        )
        with pytest.raises(HFModelNotAvailableError):
            provider._call_api("a cat", "nonexistent/model", None, 512, 512)

    def test_call_api_raises_hf_inference_error_on_generic_failure(self, monkeypatch):
        provider = self._make_provider(monkeypatch)
        provider._client.text_to_image = MagicMock(
            side_effect=Exception("Connection refused")
        )
        with pytest.raises(HFInferenceError):
            provider._call_api("a cat", "black-forest-labs/FLUX.1-schnell", None, 512, 512)
