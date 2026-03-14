"""Basis-Konfiguration und gemeinsame Modelle für alle KI-Agenten."""

from pydantic_ai.models.anthropic import AnthropicModel
from pydantic_ai.providers.anthropic import AnthropicProvider

from app.core.config import settings


def get_model() -> AnthropicModel:
    """Liefert eine konfigurierte AnthropicModel-Instanz.

    Erfordert ANTHROPIC_API_KEY. Vor dem Aufruf sollte settings.agent_available
    geprüft werden (Graceful Degradation).
    """
    api_key = settings.ANTHROPIC_API_KEY
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY ist nicht gesetzt")
    provider = AnthropicProvider(api_key=api_key)
    return AnthropicModel("claude-sonnet-4-20250514", provider=provider)
