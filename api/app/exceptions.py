"""Provider- und Asset-spezifische Exceptions für strukturiertes Fehlerhandling."""


class ProviderTimeoutError(Exception):
    """Provider-Aufruf hat das Timeout überschritten."""

    pass


class ProviderAPIError(Exception):
    """Provider-API hat einen Fehler zurückgegeben."""

    def __init__(self, status_code: int, body: str):
        self.status_code = status_code
        self.body = body
        super().__init__(f"API-Fehler {status_code}: {body[:200]}")


class ProviderInvalidResponseError(Exception):
    """Provider-Antwort war ungültig oder unvollständig."""

    pass


class Trellis2TimeoutError(ProviderTimeoutError):
    """TRELLIS.2 Provider-Aufruf hat das Timeout überschritten."""

    pass


class Trellis2InvalidImageError(ProviderAPIError):
    """TRELLIS.2: ungültiges oder nicht verarbeitbares Bild."""

    pass


class AssetStorageError(Exception):
    """Fehler beim Speichern oder Lesen von Assets im Filesystem."""

    pass
