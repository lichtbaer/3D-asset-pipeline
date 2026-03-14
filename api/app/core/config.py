"""Zentrale Konfiguration für Agent-Features (API-Keys, Modelle)."""

import os
from typing import Optional


class Settings:
    """Laufzeit-Konfiguration aus Umgebungsvariablen."""

    ANTHROPIC_API_KEY: Optional[str] = os.getenv("ANTHROPIC_API_KEY")

    @property
    def agent_available(self) -> bool:
        """True, wenn Agent-Features nutzbar sind (API-Key gesetzt)."""
        return bool(self.ANTHROPIC_API_KEY)


settings = Settings()
