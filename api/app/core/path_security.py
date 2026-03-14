"""Path-Traversal-Schutz für Asset-Dateizugriffe."""

import re
from pathlib import Path

from fastapi import HTTPException

from app.core.asset_paths import AssetPaths


def safe_asset_path(asset_id: str, filename: str) -> Path:
    """
    Validiert asset_id und filename gegen Path-Traversal.
    Raises HTTPException(400) bei ungültigem filename.
    Gibt den sicheren Pfad zurück (prüft nicht ob Datei existiert).
    """
    if not re.fullmatch(r"[0-9a-f-]{36}", asset_id):
        raise HTTPException(status_code=400, detail="Invalid asset_id")
    paths = AssetPaths(asset_id)
    base = paths.base.resolve()
    target = paths.processing_file(filename).resolve()
    try:
        target.relative_to(base)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid filename")
    return target
