"""
Blender Rigify Rigging-Provider (lokal, headless).
Nutzt Blender 4.2 LTS headless als Subprocess — keine GPU, keine externe API.
"""
import asyncio
import json
import logging
import os
import subprocess
import tempfile
from pathlib import Path

import httpx

from app.exceptions import BlenderNotAvailableError, BlenderRigifyError, BlenderRigifyTimeoutError
from app.providers.rigging.base import BaseRiggingProvider, RiggingParams, RiggingResult

logger = logging.getLogger(__name__)

BLENDER_EXECUTABLE_ENV = "BLENDER_EXECUTABLE"
BLENDER_RIGIFY_TIMEOUT_SEC = 120
SCRIPT_NAME = "blender_rig_human.py"

# Script-Pfad relativ zu Projektroot (api/ ist WORKDIR im Container)
_SCRIPT_PATH: Path | None = None


def _get_script_path() -> Path:
    """Liefert den absoluten Pfad zum Blender-Rig-Script."""
    global _SCRIPT_PATH
    if _SCRIPT_PATH is not None:
        return _SCRIPT_PATH
    # Im Container: /app mit Volume scripts -> /app/scripts/
    # Lokal: scripts/ ist Sibling von api/ (Projektroot/scripts/)
    api_dir = Path(__file__).resolve().parent.parent.parent  # .../api/app/providers/rigging -> api
    project_root = api_dir.parent  # Sibling von api
    candidates = [
        Path("/app/scripts") / SCRIPT_NAME,  # Docker mit Volume ./scripts:/app/scripts
        project_root / "scripts" / SCRIPT_NAME,
        api_dir / "scripts" / SCRIPT_NAME,
    ]
    for candidate in candidates:
        if candidate.exists():
            _SCRIPT_PATH = candidate.resolve()
            return _SCRIPT_PATH
    _SCRIPT_PATH = candidates[0]  # Fallback für Fehlermeldung
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


def _log_blender_output(stdout: bytes, stderr: bytes) -> None:
    """Loggt Blender stdout/stderr als strukturierte JSON-Logs."""
    if stdout:
        for line in stdout.decode("utf-8", errors="replace").strip().splitlines():
            logger.info("blender_rigify: %s", json.dumps({"source": "stdout", "line": line}))
    if stderr:
        for line in stderr.decode("utf-8", errors="replace").strip().splitlines():
            logger.info("blender_rigify: %s", json.dumps({"source": "stderr", "line": line}))


class BlenderRigifyProvider(BaseRiggingProvider):
    """Blender Rigify-Provider (lokal, headless)."""

    key = "blender-rigify"
    display_name = "Blender Rigify (Lokal)"

    def __init__(self) -> None:
        if not _check_blender_available():
            raise BlenderNotAvailableError("Blender nicht gefunden oder nicht ausführbar")

    async def rig(self, params: RiggingParams) -> RiggingResult:
        executable = os.getenv(BLENDER_EXECUTABLE_ENV, "blender")
        script_path = _get_script_path()
        if not script_path.exists():
            raise BlenderRigifyError(f"Blender-Rig-Script nicht gefunden: {script_path}")

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.get(params.source_glb_url)
            response.raise_for_status()
            glb_bytes = response.content

        if len(glb_bytes) == 0:
            raise BlenderRigifyError("Leere GLB-Datei")

        with tempfile.TemporaryDirectory(prefix="blender_rigify_") as tmpdir:
            tmp = Path(tmpdir)
            source_glb = tmp / "input.glb"
            output_glb = tmp / "output.glb"
            source_glb.write_bytes(glb_bytes)

            cmd = [
                executable,
                "--background",
                "--python",
                str(script_path),
                "--",
                str(source_glb),
                str(output_glb),
            ]

            def _run() -> tuple[int, bytes, bytes]:
                proc = subprocess.run(
                    cmd,
                    capture_output=True,
                    timeout=BLENDER_RIGIFY_TIMEOUT_SEC,
                )
                return proc.returncode, proc.stdout, proc.stderr

            try:
                returncode, stdout, stderr = await asyncio.wait_for(
                    asyncio.to_thread(_run),
                    timeout=BLENDER_RIGIFY_TIMEOUT_SEC,
                )
            except asyncio.TimeoutError:
                raise BlenderRigifyTimeoutError(
                    f"Blender Rigify Subprocess timed out after {BLENDER_RIGIFY_TIMEOUT_SEC}s"
                )

            _log_blender_output(stdout, stderr)

            if returncode != 0:
                err_msg = stderr.decode("utf-8", errors="replace").strip()
                raise BlenderRigifyError(f"Blender Rigify fehlgeschlagen: {err_msg or 'Unbekannter Fehler'}")

            if not output_glb.exists():
                raise BlenderRigifyError("Blender lieferte keine Output-GLB")

            rigged_bytes = output_glb.read_bytes()
            return RiggingResult(
                rigged_glb_bytes=rigged_bytes,
                provider_key=self.key,
            )
