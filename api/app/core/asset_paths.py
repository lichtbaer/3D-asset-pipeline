"""Zentrale Asset-Path-Utilities. Alle Services nutzen diese Klasse statt manueller Pfad-Berechnung."""

from pathlib import Path

from app.config.storage import ASSETS_STORAGE_PATH


class AssetPaths:
    """Zentralisierte Pfad-Berechnung für Asset-Dateien."""

    def __init__(self, asset_id: str) -> None:
        self.asset_id = asset_id
        self.base = ASSETS_STORAGE_PATH / asset_id

    @property
    def mesh(self) -> Path:
        return self.base / "mesh.glb"

    @property
    def image(self) -> Path:
        """Bild nach Image-Step (PicsArt/Upload)."""
        return self.base / "image_original.png"

    @property
    def bgremoval(self) -> Path:
        return self.base / "image_bgremoved.png"

    @property
    def rigging(self) -> Path:
        return self.base / "mesh_rigged.glb"

    @property
    def animation(self) -> Path:
        return self.base / "mesh_animated.glb"

    @property
    def metadata(self) -> Path:
        return self.base / "metadata.json"

    def processing_file(self, filename: str) -> Path:
        return self.base / filename

    def export_file(self, format: str, stem: str = "mesh") -> Path:
        return self.base / f"{stem}.{format}"
