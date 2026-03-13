"""
Provider-Registry und Lookup für Mesh-Generierung.
"""
from app.services.mesh_providers.base import MeshProvider
from app.services.mesh_providers.hunyuan3d import Hunyuan3DProvider
from app.services.mesh_providers.trellis2 import Trellis2Provider
from app.services.mesh_providers.triposr import TripoSRProvider

MESH_PROVIDERS: dict[str, MeshProvider] = {
    "hunyuan3d-2": Hunyuan3DProvider(),
    "trellis2": Trellis2Provider(),
    "triposr": TripoSRProvider(),
}


def get_provider(key: str) -> MeshProvider:
    """Liefert den Mesh-Provider für den angegebenen Key."""
    if key not in MESH_PROVIDERS:
        raise ValueError(f"Unknown mesh provider: {key}")
    return MESH_PROVIDERS[key]
