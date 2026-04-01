"""
Render-Preview-Service: Vorschau-PNG für Assets via Blender EEVEE headless.
Analog zu TextureBakingService.
"""
import logging
import os
import subprocess
from pathlib import Path

from app.exceptions import (
    BlenderNotAvailableError,
    TextureBakingError,
    TextureBakingTimeoutError,
)
from app.services import asset_service

logger = logging.getLogger(__name__)

BLENDER_EXECUTABLE_ENV = "BLENDER_EXECUTABLE"
RENDER_PREVIEW_TIMEOUT_SEC = 120
SCRIPT_NAME = "blender_render_preview.py"
OUTPUT_FILENAME = "preview_render.png"

_SCRIPT_PATH: Path | None = None


def _get_script_path() -> Path:
    """Liefert den absoluten Pfad zum Blender-Render-Script."""
    global _SCRIPT_PATH
    if _SCRIPT_PATH is not None:
        return _SCRIPT_PATH
    api_dir = Path(__file__).resolve().parent.parent
    project_root = api_dir.parent
    candidates = [
        Path("/app/scripts") / SCRIPT_NAME,
        api_dir / "scripts" / SCRIPT_NAME,
        project_root / "scripts" / SCRIPT_NAME,
    ]
    for candidate in candidates:
        if candidate.exists():
            _SCRIPT_PATH = candidate.resolve()
            return _SCRIPT_PATH
    _SCRIPT_PATH = candidates[0]
    return _SCRIPT_PATH


def _check_blender_available() -> bool:
    """Prüft ob Blender ausführbar ist."""
    executable = os.getenv(BLENDER_EXECUTABLE_ENV, "blender")
    try:
        result = subprocess.run(
            [executable, "--version"],
            capture_output=True,
            timeout=10,
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def render_preview_sync(
    asset_id: str,
    source_file: str = "mesh.glb",
    width: int = 512,
    height: int = 512,
) -> str:
    """
    Rendert Vorschau-PNG für ein Asset-Mesh.
    Gibt OUTPUT_FILENAME zurück.

    Raises:
        BlenderNotAvailableError: Blender nicht verfügbar
        TextureBakingError: Render fehlgeschlagen (wiederverwendete Exception-Klasse)
        FileNotFoundError: Source-Mesh nicht gefunden
    """
    if not _check_blender_available():
        raise BlenderNotAvailableError("Blender nicht gefunden oder nicht ausführbar")

    script_path = _get_script_path()
    if not script_path.exists():
        raise TextureBakingError(f"Render-Script nicht gefunden: {script_path}")

    source_path = asset_service.get_file_path(asset_id, source_file)
    if not source_path or not source_path.is_file():
        raise FileNotFoundError(f"Source-Mesh '{source_file}' nicht in Asset {asset_id}")

    output_path = asset_service.get_asset_dir(asset_id) / OUTPUT_FILENAME
    width = max(64, min(2048, width))
    height = max(64, min(2048, height))

    cmd = [
        os.getenv(BLENDER_EXECUTABLE_ENV, "blender"),
        "--background",
        "--python",
        str(script_path),
        "--",
        str(source_path),
        str(output_path),
        str(width),
        str(height),
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            timeout=RENDER_PREVIEW_TIMEOUT_SEC,
            cwd=str(Path(script_path).parent.parent),
        )
    except subprocess.TimeoutExpired:
        raise TextureBakingTimeoutError(
            f"Render-Preview timed out nach {RENDER_PREVIEW_TIMEOUT_SEC}s"
        )

    if result.returncode != 0:
        err = result.stderr.decode("utf-8", errors="replace").strip()
        logger.warning("Blender render stderr: %s", err)
        raise TextureBakingError(
            f"Blender Render-Preview fehlgeschlagen: {err or 'Unbekannter Fehler'}"
        )

    if not output_path.is_file():
        raise TextureBakingError("Blender lieferte keine Output-PNG")

    return OUTPUT_FILENAME
