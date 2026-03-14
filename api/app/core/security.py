"""API-Key-Authentifizierung für alle Endpunkte."""

from fastapi import Security, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.core.config import settings

security = HTTPBearer(auto_error=False)


async def verify_api_key(
    credentials: HTTPAuthorizationCredentials | None = Security(security),
) -> None:
    """
    Prüft API-Key. Wenn API_KEY gesetzt: Bearer-Token erforderlich.
    Wenn API_KEY leer: kein Schutz (dev mode).
    """
    if not settings.API_KEY:
        return
    if not credentials or credentials.credentials != settings.API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")
