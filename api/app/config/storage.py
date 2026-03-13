"""Storage-Konfiguration für generierte Assets."""

import os
from pathlib import Path

# GLB-Mesh-Speicher: im Container /app/storage/meshes, konfigurierbar via MESH_STORAGE_PATH
MESH_STORAGE_PATH = Path(
    os.getenv("MESH_STORAGE_PATH", "/app/storage/meshes")
)

# BG-Removal-Output-Speicher: /app/storage/bgremoval
BGREMOVAL_STORAGE_PATH = Path(
    os.getenv("BGREMOVAL_STORAGE_PATH", "/app/storage/bgremoval")
)

# Asset-Persistenz: /app/storage/assets (Ordnerstruktur mit metadata.json)
ASSETS_STORAGE_PATH = Path(
    os.getenv("ASSETS_STORAGE_PATH", "/app/storage/assets")
)

# Animation-Output (temporär vor Asset-Persistenz)
ANIMATION_STORAGE_PATH = Path(
    os.getenv("ANIMATION_STORAGE_PATH", "/app/storage/animations")
)

# Image-Output (HF Inference, lokal gespeicherte Bilder)
IMAGE_STORAGE_PATH = Path(
    os.getenv("IMAGE_STORAGE_PATH", "/app/storage/images")
)

# Logs: /app/storage/logs (rolling app.log)
LOGS_PATH = Path(os.getenv("LOG_PATH", "/app/storage/logs"))
