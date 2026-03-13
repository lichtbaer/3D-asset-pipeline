"""
Rigging-Provider-Abstraktion: austauschbare Rigging-Backends (UniRig, etc.).
"""
from app.providers.rigging.base import BaseRiggingProvider, RiggingParams, RiggingResult
from app.providers.rigging.registry import (
    RIGGING_PROVIDER_REGISTRY,
    get_rigging_provider,
    list_rigging_providers,
)

__all__ = [
    "BaseRiggingProvider",
    "RiggingParams",
    "RiggingResult",
    "RIGGING_PROVIDER_REGISTRY",
    "get_rigging_provider",
    "list_rigging_providers",
]
