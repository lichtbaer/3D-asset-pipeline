"""Zentrale Konfiguration (API-Keys, CORS, Auth)."""

from __future__ import annotations

from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Laufzeit-Konfiguration aus Umgebungsvariablen."""

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}

    ANTHROPIC_API_KEY: str | None = None

    # API-Key-Authentifizierung: leer = kein Schutz (dev), gesetzt = Bearer-Auth erforderlich
    API_KEY: str | None = None

    # CORS: kommagetrennte Origins (ALLOWED_ORIGINS oder CORS_ORIGINS)
    ALLOWED_ORIGINS: str = "http://localhost:5173"
    CORS_ORIGINS: str | None = None

    # Timeouts (Sekunden)
    IMAGE_DOWNLOAD_TIMEOUT_S: int = 60
    MESH_GENERATION_TIMEOUT_S: int = 300

    # Max. Dateigröße für heruntergeladene Bilder (Bytes)
    IMAGE_DOWNLOAD_MAX_SIZE: int = 50 * 1024 * 1024  # 50 MB

    # Datenbank-Query-Timeout (Millisekunden)
    DB_STATEMENT_TIMEOUT_MS: int = 30000

    @field_validator("API_KEY", mode="before")
    @classmethod
    def _strip_api_key(cls, v: str | None) -> str | None:
        if v is None:
            return None
        stripped = v.strip()
        return stripped or None

    @property
    def resolved_origins(self) -> str:
        """ALLOWED_ORIGINS hat Vorrang; CORS_ORIGINS als Fallback."""
        return self.ALLOWED_ORIGINS or self.CORS_ORIGINS or "http://localhost:5173"

    @property
    def agent_available(self) -> bool:
        """True, wenn Agent-Features nutzbar sind (API-Key gesetzt)."""
        return bool(self.ANTHROPIC_API_KEY)


settings = Settings()
