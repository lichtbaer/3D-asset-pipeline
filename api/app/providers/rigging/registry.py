"""
Provider-Registry und Lookup für Rigging.
HF_TOKEN fehlt → UniRig wird nicht registriert, Server startet trotzdem.
"""
import logging
import os

from app.providers.rigging.base import BaseRiggingProvider

logger = logging.getLogger(__name__)


def _build_registry() -> dict[str, BaseRiggingProvider]:
    """Baut die Registry; UniRig nur wenn HF_TOKEN gesetzt."""
    registry: dict[str, BaseRiggingProvider] = {}
    if os.getenv("HF_TOKEN"):
        try:
            from app.providers.rigging.unirig_provider import UniRigProvider

            registry["unirig"] = UniRigProvider()
        except Exception as e:
            logger.warning(
                "UniRig-Provider nicht geladen: %s — Provider aus Registry ausgeschlossen",
                e,
            )
    else:
        logger.info(
            "HF_TOKEN fehlt — UniRig-Provider aus Registry ausgeschlossen"
        )
    return registry


RIGGING_PROVIDER_REGISTRY: dict[str, BaseRiggingProvider] = _build_registry()


def get_rigging_provider(key: str) -> BaseRiggingProvider:
    """Liefert den Rigging-Provider für den angegebenen Key."""
    if key not in RIGGING_PROVIDER_REGISTRY:
        raise ValueError(f"Unknown rigging provider: {key}")
    return RIGGING_PROVIDER_REGISTRY[key]


def list_rigging_providers() -> list[BaseRiggingProvider]:
    """Listet alle registrierten Rigging-Provider."""
    return list(RIGGING_PROVIDER_REGISTRY.values())
