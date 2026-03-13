"""Unit-Tests für den Replicate Image-Provider."""

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.exceptions import (
    ProviderConfigError,
    ReplicateAPIError,
    ReplicateModelError,
)
from app.services.image_providers.replicate_provider import (
    ReplicateImageProvider,
    _extract_url,
)


class TestReplicateProviderInit:
    def test_raises_config_error_without_token(self, monkeypatch):
        monkeypatch.delenv("REPLICATE_API_TOKEN", raising=False)
        with pytest.raises(ProviderConfigError, match="REPLICATE_API_TOKEN"):
            ReplicateImageProvider()

    def test_creates_provider_with_token(self, monkeypatch):
        monkeypatch.setenv("REPLICATE_API_TOKEN", "r8_testtoken123")
        provider = ReplicateImageProvider()
        assert provider.provider_key == "replicate"
        assert provider.display_name == "Replicate"

    def test_default_params(self, monkeypatch):
        monkeypatch.setenv("REPLICATE_API_TOKEN", "r8_testtoken123")
        provider = ReplicateImageProvider()
        params = provider.default_params()
        assert params["width"] == 1024
        assert params["height"] == 1024
        assert params["model"] == "black-forest-labs/flux-schnell"
        assert params["negative_prompt"] is None

    def test_param_schema(self, monkeypatch):
        monkeypatch.setenv("REPLICATE_API_TOKEN", "r8_testtoken123")
        provider = ReplicateImageProvider()
        schema = provider.param_schema()
        assert "model" in schema["properties"]
        assert "width" in schema["properties"]
        assert "height" in schema["properties"]
        assert "black-forest-labs/flux-schnell" in schema["properties"]["model"]["enum"]


class TestReplicateProviderGenerate:
    def _make_provider(self, monkeypatch):
        monkeypatch.setenv("REPLICATE_API_TOKEN", "r8_testtoken123")
        return ReplicateImageProvider()

    @pytest.mark.asyncio
    async def test_generate_returns_url_from_list(self, monkeypatch):
        provider = self._make_provider(monkeypatch)
        expected_url = "https://replicate.delivery/pbxt/test-image.png"

        with patch("replicate.async_run", new_callable=AsyncMock, return_value=[expected_url]):
            url = await provider.generate("a dog", {"model": "black-forest-labs/flux-schnell"})

        assert url == expected_url

    @pytest.mark.asyncio
    async def test_generate_returns_url_from_string(self, monkeypatch):
        provider = self._make_provider(monkeypatch)
        expected_url = "https://replicate.delivery/pbxt/test-image.png"

        with patch("replicate.async_run", new_callable=AsyncMock, return_value=expected_url):
            url = await provider.generate("a dog", {})

        assert url == expected_url

    @pytest.mark.asyncio
    async def test_generate_returns_url_from_file_output(self, monkeypatch):
        provider = self._make_provider(monkeypatch)
        expected_url = "https://replicate.delivery/pbxt/test-image.png"

        file_output = MagicMock()
        file_output.url = expected_url

        with patch("replicate.async_run", new_callable=AsyncMock, return_value=[file_output]):
            url = await provider.generate("a dog", {})

        assert url == expected_url

    @pytest.mark.asyncio
    async def test_generate_raises_replicate_api_error_on_failure(self, monkeypatch):
        provider = self._make_provider(monkeypatch)

        with patch(
            "replicate.async_run",
            new_callable=AsyncMock,
            side_effect=Exception("API rate limit exceeded"),
        ):
            with pytest.raises(ReplicateAPIError):
                await provider.generate("a dog", {})

    @pytest.mark.asyncio
    async def test_generate_raises_model_error_on_not_found(self, monkeypatch):
        provider = self._make_provider(monkeypatch)

        with patch(
            "replicate.async_run",
            new_callable=AsyncMock,
            side_effect=Exception("Model not found"),
        ):
            with pytest.raises(ReplicateModelError):
                await provider.generate("a dog", {"model": "nonexistent/model"})

    @pytest.mark.asyncio
    async def test_generate_raises_api_error_on_empty_output(self, monkeypatch):
        provider = self._make_provider(monkeypatch)

        with patch("replicate.async_run", new_callable=AsyncMock, return_value=None):
            with pytest.raises(ReplicateAPIError, match="Keine URL"):
                await provider.generate("a dog", {})

    def test_passes_params_correctly(self, monkeypatch):
        """Stellt sicher, dass alle Parameter korrekt an replicate.async_run übergeben werden."""
        provider = self._make_provider(monkeypatch)
        captured = {}

        async def mock_run(model, input):
            captured["model"] = model
            captured["input"] = input
            return ["https://example.com/image.png"]

        with patch("replicate.async_run", side_effect=mock_run):
            import asyncio
            asyncio.run(
                provider.generate(
                    "a cat",
                    {
                        "model": "black-forest-labs/flux-dev",
                        "width": 768,
                        "height": 768,
                        "negative_prompt": "blurry",
                    },
                )
            )

        assert captured["model"] == "black-forest-labs/flux-dev"
        assert captured["input"]["prompt"] == "a cat"
        assert captured["input"]["width"] == 768
        assert captured["input"]["height"] == 768
        assert captured["input"]["negative_prompt"] == "blurry"
        assert captured["input"]["num_outputs"] == 1


class TestExtractUrl:
    def test_from_string(self):
        assert _extract_url("https://example.com/img.png") == "https://example.com/img.png"

    def test_from_list_of_strings(self):
        assert _extract_url(["https://example.com/img.png"]) == "https://example.com/img.png"

    def test_from_list_of_file_outputs(self):
        obj = MagicMock()
        obj.url = "https://example.com/img.png"
        assert _extract_url([obj]) == "https://example.com/img.png"

    def test_from_file_output_with_url(self):
        obj = MagicMock()
        obj.url = "https://example.com/img.png"
        assert _extract_url(obj) == "https://example.com/img.png"

    def test_returns_none_for_none(self):
        assert _extract_url(None) is None

    def test_returns_none_for_empty_list(self):
        assert _extract_url([]) is None
