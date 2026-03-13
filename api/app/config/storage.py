"""Storage-Konfiguration für generierte Assets."""

import os
from pathlib import Path

# GLB-Mesh-Speicher: im Container /app/storage/meshes, konfigurierbar via MESH_STORAGE_PATH
MESH_STORAGE_PATH = Path(
    os.getenv("MESH_STORAGE_PATH", "/app/storage/meshes")
)
