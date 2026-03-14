"""
Texture-Baking-Service: PBR-Texturen vom High-Poly auf Low-Poly via Blender headless.
Nach Mesh-Simplification gehen UVs verloren – dieser Service rebaked die Texturen.
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
TEXTURE_BAKING_TIMEOUT_SEC = 300
SCRIPT_NAME = "blender_bake_textures.py"

_SCRIPT_PATH: Path | None = None


def _get_script_path() -> Path:
    """Liefert den absoluten Pfad zum Blender-Bake-Script."""
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


def _target_stem_to_output_filename(target_mesh: str) -> str:
    """mesh_simplified_10000.glb -> mesh_baked_mesh_simplified_10000.glb"""
    stem = Path(target_mesh).stem
    return f"mesh_baked_{stem}.glb"


class TextureBakingService:
    """Service für Texture-Baking via Blender headless."""

    def bake(
        self,
        asset_id: str,
        source_mesh: str,
        target_mesh: str,
        resolution: int = 1024,
        bake_types: list[str] | None = None,
    ) -> str:
        """
        Baked PBR-Texturen vom Source- auf den Target-Mesh.
        Speichert mesh_baked_{target_stem}.glb im Asset-Ordner.
        Gibt den Output-Dateinamen zurück.
        """
        if not _check_blender_available():
            raise BlenderNotAvailableError(
                "Blender nicht gefunden oder nicht ausführbar"
            )

        script_path = _get_script_path()
        if not script_path.exists():
            raise TextureBakingError(f"Blender-Bake-Script nicht gefunden: {script_path}")

        source_path = asset_service.get_file_path(asset_id, source_mesh)
        target_path = asset_service.get_file_path(asset_id, target_mesh)
        if not source_path or not source_path.is_file():
            raise FileNotFoundError(f"Source-Mesh {source_mesh} nicht in Asset {asset_id}")
        if not target_path or not target_path.is_file():
            raise FileNotFoundError(f"Target-Mesh {target_mesh} nicht in Asset {asset_id}")

        output_filename = _target_stem_to_output_filename(target_mesh)
        output_path = asset_service.get_asset_dir(asset_id) / output_filename

        resolution = max(256, min(4096, resolution))
        types = bake_types or ["diffuse", "roughness", "metallic"]
        bake_types_str = ",".join(t for t in types if t in ("diffuse", "roughness", "metallic"))
        if not bake_types_str:
            bake_types_str = "diffuse,roughness,metallic"

        cmd = [
            os.getenv(BLENDER_EXECUTABLE_ENV, "blender"),
            "--background",
            "--python",
            str(script_path),
            "--",
            str(source_path),
            str(target_path),
            str(output_path),
            str(resolution),
            bake_types_str,
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                timeout=TEXTURE_BAKING_TIMEOUT_SEC,
                cwd=str(Path(script_path).parent.parent),
            )
        except subprocess.TimeoutExpired:
            raise TextureBakingTimeoutError(
                f"Texture-Baking timed out nach {TEXTURE_BAKING_TIMEOUT_SEC}s"
            )

        if result.returncode != 0:
            err = result.stderr.decode("utf-8", errors="replace").strip()
            logger.warning("Blender bake stderr: %s", err)
            raise TextureBakingError(
                f"Blender Texture-Baking fehlgeschlagen: {err or 'Unbekannter Fehler'}"
            )

        if not output_path.is_file():
            raise TextureBakingError("Blender lieferte keine Output-GLB")

        return output_filename


def run_bake_sync(
    asset_id: str,
    source_mesh: str,
    target_mesh: str,
    resolution: int = 1024,
    bake_types: list[str] | None = None,
) -> str:
    """
    Synchrone Ausführung des Bakes (für Background-Task).
    Gibt output_filename zurück.
    """
    svc = TextureBakingService()
    return svc.bake(
        asset_id=asset_id,
        source_mesh=source_mesh,
        target_mesh=target_mesh,
        resolution=resolution,
        bake_types=bake_types,
    )
