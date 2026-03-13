"""
Provider-Registry und Lookup für Rigging.
HF_TOKEN fehlt → UniRig (HF Space) wird nicht registriert.
CUDA/Checkpoint fehlt → UniRig (Lokal) wird nicht registriert.
Server startet trotzdem.
"""
import logging
import os
from pathlib import Path

from app.providers.rigging.base import BaseRiggingProvider

logger = logging.getLogger(__name__)


def _build_registry() -> dict[str, BaseRiggingProvider]:
    """Baut die Registry; UniRig HF nur wenn HF_TOKEN; UniRig Local nur wenn CUDA + Checkpoint."""
    registry: dict[str, BaseRiggingProvider] = {}

    # UniRig via HF Space
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

    # UniRig Lokal (nur wenn CUDA + Checkpoint vorhanden)
    try:
        from app.providers.rigging.unirig_local import (
            _checkpoints_exist,
            _cuda_available,
            _repo_ready,
            UniRigLocalProvider,
        )

        if not _cuda_available():
            logger.warning(
                "CUDA nicht verfügbar — UniRig (Lokal) aus Registry ausgeschlossen"
            )
        else:
            model_path = Path(
                os.getenv("UNIRIG_MODEL_PATH", "./models/unirig/")
            ).resolve()
            if not _checkpoints_exist(model_path):
                logger.warning(
                    "UNIRIG_MODEL_PATH oder Checkpoint fehlt (%s) — UniRig (Lokal) aus Registry ausgeschlossen",
                    model_path,
                )
            else:
                repo_path = Path(
                    os.getenv("UNIRIG_REPO_PATH", "./unirig/")
                ).resolve()
                if not _repo_ready(repo_path):
                    logger.warning(
                        "UNIRIG_REPO_PATH oder UniRig-Repo fehlt (%s) — UniRig (Lokal) aus Registry ausgeschlossen",
                        repo_path,
                    )
                else:
                    registry["unirig-local"] = UniRigLocalProvider()
    except Exception as e:
        logger.warning(
            "UniRig (Lokal) nicht geladen: %s — Provider aus Registry ausgeschlossen",
            e,
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
