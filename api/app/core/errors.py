"""Einheitliches API-Fehlerformat für alle HTTP-Responses."""

from typing import NoReturn

from fastapi import HTTPException
from pydantic import BaseModel


class APIError(BaseModel):
    """Strukturiertes Fehler-Format für alle API-Responses."""

    error: str
    detail: str | None = None
    code: str | None = None

    def to_detail(self) -> dict[str, str | None]:
        """Gibt das dict für HTTPException(detail=...) zurück."""
        return self.model_dump()


def raise_api_error(
    status_code: int,
    error: str,
    *,
    detail: str | None = None,
    code: str | None = None,
    chain: BaseException | None = None,
) -> NoReturn:
    """Hebt HTTPException mit einheitlichem APIError-Format aus."""
    exc = HTTPException(
        status_code=status_code,
        detail=APIError(error=error, detail=detail, code=code).model_dump(),
    )
    if chain is not None:
        raise exc from chain
    raise exc
