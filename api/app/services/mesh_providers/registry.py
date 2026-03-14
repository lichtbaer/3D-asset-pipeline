"""
Provider-Registry und Lookup für Mesh-Generierung.
trellis-piapi nur registriert wenn PIAPI_API_KEY gesetzt.
"""
import os

from app.services.mesh_providers.base import MeshProvider
from app.services.mesh_providers.hunyuan3d import Hunyuan3DProvider
from app.services.mesh_providers.trellis2 import Trellis2Provider
from app.services.mesh_providers.trellis_piapi import TrellisPiAPIProvider
from app.services.mesh_providers.triposr import TripoSRProvider


def _build_mesh_providers() -> dict[str, MeshProvider]:
    providers: dict[str, MeshProvider] = {
        "hunyuan3d-2": Hunyuan3DProvider(),
        "trellis2": Trellis2Provider(),
        "triposr": TripoSRProvider(),
    }
    if os.getenv("PIAPI_API_KEY", "").strip():
        providers["trellis-piapi"] = TrellisPiAPIProvider()
    return providers


MESH_PROVIDERS: dict[str, MeshProvider] = _build_mesh_providers()


def get_provider(key: str) -> MeshProvider:
    """Liefert den Mesh-Provider für den angegebenen Key."""
    if key not in MESH_PROVIDERS:
        raise ValueError(f"Unknown mesh provider: {key}")
    return MESH_PROVIDERS[key]
