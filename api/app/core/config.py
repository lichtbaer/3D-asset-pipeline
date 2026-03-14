"""Zentrale Konfiguration für Agent-Features (API-Keys, Modelle)."""

import os
from typing import Optional


class Settings:
    """Laufzeit-Konfiguration aus Umgebungsvariablen."""

    ANTHROPIC_API_KEY: Optional[str] = os.getenv("ANTHROPIC_API_KEY")

    # API-Key-Authentifizierung: leer = kein Schutz (dev), gesetzt = Bearer-Auth erforderlich
    _api_key_raw = os.getenv("API_KEY")
    API_KEY: Optional[str] = (_api_key_raw or "").strip() or None

    # CORS: kommagetrennte Origins (ALLOWED_ORIGINS oder CORS_ORIGINS)
    ALLOWED_ORIGINS: str = os.getenv(
        "ALLOWED_ORIGINS", os.getenv("CORS_ORIGINS", "http://localhost:5173")
    )

    @property
    def agent_available(self) -> bool:
        """True, wenn Agent-Features nutzbar sind (API-Key gesetzt)."""
        return bool(self.ANTHROPIC_API_KEY)


settings = Settings()
