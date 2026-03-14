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


class UniRigTimeoutError(ProviderTimeoutError):
    """UniRig-Aufruf hat das Timeout überschritten."""

    pass


class UniRigInvalidMeshError(ProviderAPIError):
    """Mesh ist nicht riggbar (z.B. ungültige Geometrie)."""

    def __init__(self, message: str) -> None:
        super().__init__(status_code=400, body=message)


class ProviderConfigError(Exception):
    """Provider-Konfiguration fehlt oder ist ungültig (z.B. fehlender API-Token)."""

    pass


class HFInferenceError(ProviderAPIError):
    """Fehler beim Aufruf der Hugging Face Inference API."""

    pass


class HFModelNotAvailableError(ProviderAPIError):
    """Das angeforderte HF-Modell ist nicht verfügbar oder existiert nicht."""

    pass


class ReplicateAPIError(ProviderAPIError):
    """Fehler beim Aufruf der Replicate API."""

    pass


class ReplicateModelError(ProviderAPIError):
    """Das angeforderte Replicate-Modell ist nicht verfügbar oder existiert nicht."""

    pass


class BlenderRigifyError(Exception):
    """Blender Rigify-Provider hat einen Fehler zurückgegeben."""

    pass


class BlenderRigifyTimeoutError(ProviderTimeoutError):
    """Blender Rigify Subprocess hat das Timeout überschritten."""

    pass


class BlenderNotAvailableError(ProviderConfigError):
    """Blender ist nicht installiert oder nicht ausführbar."""

    pass


class TextureBakingError(Exception):
    """Texture-Baking-Service hat einen Fehler zurückgegeben."""

    pass


class TextureBakingTimeoutError(ProviderTimeoutError):
    """Texture-Baking Subprocess hat das Timeout überschritten."""

    pass
