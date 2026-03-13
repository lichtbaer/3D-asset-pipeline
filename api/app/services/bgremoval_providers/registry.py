"""Provider-Registry für Background-Removal-Provider."""

from app.services.bgremoval_providers.base import BgRemovalProvider
from app.services.bgremoval_providers.picsart import PicsArtBgRemovalProvider

BGREMOVAL_PROVIDERS: dict[str, BgRemovalProvider] = {
    "picsart": PicsArtBgRemovalProvider(),
}


def get_provider(key: str) -> BgRemovalProvider:
    """
    Liefert den Provider für den gegebenen Key.

    Raises:
        ValueError: Bei unbekanntem provider_key
    """
    if key not in BGREMOVAL_PROVIDERS:
        raise ValueError(f"Unbekannter bgremoval provider_key: {key}")
    return BGREMOVAL_PROVIDERS[key]


def list_providers() -> list[BgRemovalProvider]:
    """Liefert alle registrierten Background-Removal-Provider."""
    return list(BGREMOVAL_PROVIDERS.values())
