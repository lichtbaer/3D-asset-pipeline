"""Unit-Tests für die Image-Provider-Registry mit den neuen Providern."""

import importlib
import os
from unittest.mock import MagicMock, patch

import pytest

from app.exceptions import ProviderConfigError


class TestRegistryWithTokens:
    def test_registry_contains_hf_and_replicate_when_tokens_set(self, monkeypatch):
        monkeypatch.setenv("HF_TOKEN", "hf_testtoken")
        monkeypatch.setenv("REPLICATE_API_TOKEN", "r8_testtoken")

        with patch("huggingface_hub.InferenceClient"):
            import app.services.image_providers.registry as reg
            importlib.reload(reg)

        keys = [p.provider_key for p in reg.list_providers()]
        assert "hf-inference" in keys
        assert "replicate" in keys

    def test_registry_excludes_hf_without_token(self, monkeypatch):
        monkeypatch.delenv("HF_TOKEN", raising=False)
        monkeypatch.setenv("REPLICATE_API_TOKEN", "r8_testtoken")

        import app.services.image_providers.registry as reg
        importlib.reload(reg)

        keys = [p.provider_key for p in reg.list_providers()]
        assert "hf-inference" not in keys
        assert "replicate" in keys

    def test_registry_excludes_replicate_without_token(self, monkeypatch):
        monkeypatch.setenv("HF_TOKEN", "hf_testtoken")
        monkeypatch.delenv("REPLICATE_API_TOKEN", raising=False)

        with patch("huggingface_hub.InferenceClient"):
            import app.services.image_providers.registry as reg
            importlib.reload(reg)

        keys = [p.provider_key for p in reg.list_providers()]
        assert "hf-inference" in keys
        assert "replicate" not in keys

    def test_registry_always_contains_picsart_providers(self, monkeypatch):
        monkeypatch.delenv("HF_TOKEN", raising=False)
        monkeypatch.delenv("REPLICATE_API_TOKEN", raising=False)

        import app.services.image_providers.registry as reg
        importlib.reload(reg)

        keys = [p.provider_key for p in reg.list_providers()]
        assert "picsart-default" in keys
        assert "picsart-flux-dev" in keys

    def test_get_provider_raises_for_unknown_key(self, monkeypatch):
        import app.services.image_providers.registry as reg
        importlib.reload(reg)

        with pytest.raises(ValueError, match="Unbekannter provider_key"):
            reg.get_provider("completely-unknown-provider")

    def test_server_starts_without_tokens(self, monkeypatch):
        """Server soll trotz fehlender Tokens starten (kein Crash)."""
        monkeypatch.delenv("HF_TOKEN", raising=False)
        monkeypatch.delenv("REPLICATE_API_TOKEN", raising=False)

        import app.services.image_providers.registry as reg
        importlib.reload(reg)

        providers = reg.list_providers()
        assert len(providers) >= 5  # mindestens PicsArt-Provider
