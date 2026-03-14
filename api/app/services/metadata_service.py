"""
Zentraler Metadata-Service für metadata.json.
Atomares Schreiben, einheitliche Fehlerbehandlung.
"""

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.core.asset_paths import AssetPaths


class MetadataService:
    """Zentralisierter Zugriff auf metadata.json mit atomarem Schreiben."""

    def read(self, asset_id: str) -> dict[str, Any]:
        """Liest metadata.json, gibt {} zurück wenn nicht vorhanden."""
        path = AssetPaths(asset_id).metadata
        if not path.exists():
            return {}
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}
        except (json.JSONDecodeError, OSError):
            return {}

    def write(self, asset_id: str, data: dict[str, Any]) -> None:
        """Schreibt metadata.json atomar (write to tmp, then rename)."""
        paths = AssetPaths(asset_id)
        path = paths.metadata
        paths.base.mkdir(parents=True, exist_ok=True)

        with tempfile.NamedTemporaryFile(
            mode="w",
            dir=path.parent,
            delete=False,
            suffix=".tmp",
            encoding="utf-8",
        ) as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            tmp_path = Path(f.name)
        try:
            os.replace(tmp_path, path)
        except OSError:
            tmp_path.unlink(missing_ok=True)
            raise

    def update(self, asset_id: str, **kwargs: Any) -> None:
        """Partial update — liest, merged, schreibt."""
        path = AssetPaths(asset_id).metadata
        if not path.exists():
            raise FileNotFoundError(f"Asset {asset_id} existiert nicht")
        data = self.read(asset_id)
        data.update(kwargs)
        data["updated_at"] = datetime.now(timezone.utc).isoformat()
        self.write(asset_id, data)

    def add_processing_entry(self, asset_id: str, entry: dict[str, Any]) -> None:
        """Fügt Eintrag zu metadata.processing hinzu."""
        path = AssetPaths(asset_id).metadata
        if not path.exists():
            raise FileNotFoundError(f"Asset {asset_id} existiert nicht")
        data = self.read(asset_id)
        if "processing" not in data:
            data["processing"] = []
        data["processing"].append(entry)
        data["updated_at"] = datetime.now(timezone.utc).isoformat()
        self.write(asset_id, data)

    def add_image_processing_entry(
        self, asset_id: str, entry: dict[str, Any]
    ) -> None:
        """Fügt Eintrag zu metadata.image_processing hinzu."""
        path = AssetPaths(asset_id).metadata
        if not path.exists():
            raise FileNotFoundError(f"Asset {asset_id} existiert nicht")
        data = self.read(asset_id)
        if "image_processing" not in data:
            data["image_processing"] = []
        data["image_processing"].append(entry)
        data["updated_at"] = datetime.now(timezone.utc).isoformat()
        self.write(asset_id, data)

    def add_texture_baking_entry(
        self, asset_id: str, entry: dict[str, Any]
    ) -> None:
        """Fügt Eintrag zu metadata.texture_baking hinzu."""
        path = AssetPaths(asset_id).metadata
        if not path.exists():
            raise FileNotFoundError(f"Asset {asset_id} existiert nicht")
        data = self.read(asset_id)
        if "texture_baking" not in data:
            data["texture_baking"] = []
        data["texture_baking"].append(entry)
        data["updated_at"] = datetime.now(timezone.utc).isoformat()
        self.write(asset_id, data)

    def add_export_entry(self, asset_id: str, entry: dict[str, Any]) -> None:
        """Fügt Eintrag zu metadata.exports hinzu."""
        path = AssetPaths(asset_id).metadata
        if not path.exists():
            raise FileNotFoundError(f"Asset {asset_id} existiert nicht")
        data = self.read(asset_id)
        if "exports" not in data:
            data["exports"] = []
        data["exports"].append(entry)
        data["updated_at"] = datetime.now(timezone.utc).isoformat()
        self.write(asset_id, data)

    def mark_step_done(self, asset_id: str, step: str, data: dict[str, Any]) -> None:
        """Setzt metadata.steps.{step} = data."""
        meta = self.read(asset_id)
        if "steps" not in meta:
            meta["steps"] = {}
        meta["steps"][step] = data
        meta["updated_at"] = datetime.now(timezone.utc).isoformat()
        self.write(asset_id, meta)


_metadata_service: MetadataService | None = None


def get_metadata_service() -> MetadataService:
    """Singleton-Instanz des MetadataService."""
    global _metadata_service
    if _metadata_service is None:
        _metadata_service = MetadataService()
    return _metadata_service
