"""
UniRig Rigging-Provider mit lokalem Inferencing (ohne HF Space).
Läuft nur wenn CUDA verfügbar ist und Checkpoints unter UNIRIG_MODEL_PATH existieren.
"""
import asyncio
import logging
import os
import subprocess
import tempfile
from pathlib import Path

import httpx

from app.exceptions import UniRigInvalidMeshError, UniRigTimeoutError
from app.providers.rigging.base import BaseRiggingProvider, RiggingParams, RiggingResult

logger = logging.getLogger(__name__)

UNIRIG_TIMEOUT_SEC = 300
UNIRIG_MODEL_PATH_ENV = "UNIRIG_MODEL_PATH"
UNIRIG_REPO_PATH_ENV = "UNIRIG_REPO_PATH"

# Checkpoint-Struktur (HF VAST-AI/UniRig)
SKELETON_CKPT = "skeleton/articulation-xl_quantization_256/model.ckpt"
SKIN_CKPT = "skin/articulation-xl/model.ckpt"


def _cuda_available() -> bool:
    """Prüft ob CUDA verfügbar ist."""
    try:
        import torch
        return bool(torch.cuda.is_available())
    except ImportError:
        return False


def _checkpoints_exist(model_path: Path) -> bool:
    """Prüft ob beide Checkpoint-Dateien existieren."""
    return (
        (model_path / SKELETON_CKPT).exists()
        and (model_path / SKIN_CKPT).exists()
    )


def _repo_ready(repo_path: Path) -> bool:
    """Prüft ob das UniRig-Repo mit den benötigten Skripten existiert."""
    return (
        (repo_path / "run.py").exists()
        and (repo_path / "launch" / "inference" / "generate_skeleton.sh").exists()
        and (repo_path / "launch" / "inference" / "generate_skin.sh").exists()
        and (repo_path / "launch" / "inference" / "merge.sh").exists()
    )


def _ensure_experiments_symlink(repo_path: Path, model_path: Path) -> None:
    """Erstellt experiments-Symlink im Repo, falls nötig."""
    experiments = repo_path / "experiments"
    if experiments.exists():
        if experiments.is_symlink() and experiments.resolve() == model_path.resolve():
            return
        if experiments.is_dir() and not experiments.is_symlink():
            return
    if experiments.exists():
        experiments.unlink()
    experiments.symlink_to(model_path.resolve(), target_is_directory=True)


class UniRigLocalProvider(BaseRiggingProvider):
    """UniRig-Provider mit lokalem Inferencing (ohne HF Space)."""

    key = "unirig-local"
    display_name = "UniRig (Lokal)"

    def __init__(self) -> None:
        model_path_str = os.getenv(UNIRIG_MODEL_PATH_ENV, "./models/unirig/")
        repo_path_str = os.getenv(UNIRIG_REPO_PATH_ENV, "./unirig/")
        self._model_path = Path(model_path_str).resolve()
        self._repo_path = Path(repo_path_str).resolve()

    def _run_shell(
        self,
        script: str,
        args: list[str],
        cwd: Path,
        timeout: int,
    ) -> subprocess.CompletedProcess[bytes]:
        """Führt ein Shell-Skript im UniRig-Repo aus."""
        cmd = ["bash", script] + args
        return subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            timeout=timeout,
            env={**os.environ, "PYTHONPATH": str(cwd)},
        )

    async def rig(self, params: RiggingParams) -> RiggingResult:
        # 1. GLB von URL laden → temp file
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.get(params.source_glb_url)
            response.raise_for_status()
            glb_bytes = response.content

        if len(glb_bytes) == 0:
            raise UniRigInvalidMeshError("Leere GLB-Datei")

        with tempfile.TemporaryDirectory(prefix="unirig_") as tmpdir:
            tmp = Path(tmpdir)
            input_glb = tmp / "input.glb"
            input_glb.write_bytes(glb_bytes)

            # UniRig erwartet: npz_dir/input/raw_data.npz, skeleton.fbx, predict_skeleton.npz, result_fbx.fbx
            npz_dir = tmp / "npz"
            npz_dir.mkdir()

            _ensure_experiments_symlink(self._repo_path, self._model_path)

            def _run() -> None:
                # Schritt 1: Skeleton (output_dir=npz_dir → npz_dir/input/skeleton.fbx + predict_skeleton.npz)
                proc = self._run_shell(
                    "launch/inference/generate_skeleton.sh",
                    [
                        "--input", str(input_glb),
                        "--output_dir", str(npz_dir),
                        "--npz_dir", str(npz_dir),
                    ],
                    self._repo_path,
                    timeout=UNIRIG_TIMEOUT_SEC,
                )
                if proc.returncode != 0:
                    stderr = proc.stderr.decode() if proc.stderr else ""
                    raise RuntimeError(f"UniRig Skeleton failed: {stderr}")

                # Skeleton schreibt nach npz_dir/input/skeleton.fbx
                skeleton_fbx = npz_dir / "input" / "skeleton.fbx"
                if not skeleton_fbx.exists():
                    raise UniRigInvalidMeshError(
                        "UniRig lieferte keine Skeleton-FBX; Mesh evtl. nicht riggbar"
                    )

                # Schritt 2: Skin (input_dir=npz_dir, nutzt predict_skeleton.npz)
                proc = self._run_shell(
                    "launch/inference/generate_skin.sh",
                    [
                        "--input_dir", str(npz_dir),
                        "--output_dir", str(npz_dir),
                        "--npz_dir", str(npz_dir),
                        "--data_name", "predict_skeleton.npz",
                    ],
                    self._repo_path,
                    timeout=UNIRIG_TIMEOUT_SEC,
                )
                if proc.returncode != 0:
                    stderr = proc.stderr.decode() if proc.stderr else ""
                    raise RuntimeError(f"UniRig Skin failed: {stderr}")

                # Skin schreibt nach npz_dir/input/result_fbx.fbx
                skin_fbx = npz_dir / "input" / "result_fbx.fbx"
                if not skin_fbx.exists():
                    raise UniRigInvalidMeshError(
                        "UniRig lieferte keine Skin-FBX; Mesh evtl. nicht riggbar"
                    )

                # Schritt 3: Merge zu GLB
                proc = self._run_shell(
                    "launch/inference/merge.sh",
                    [
                        "--source", str(skin_fbx),
                        "--target", str(input_glb),
                        "--output", str(tmp / "rigged.glb"),
                    ],
                    self._repo_path,
                    timeout=UNIRIG_TIMEOUT_SEC,
                )
                if proc.returncode != 0:
                    stderr = proc.stderr.decode() if proc.stderr else ""
                    raise RuntimeError(f"UniRig Merge failed: {stderr}")

            output_glb = tmp / "rigged.glb"

            try:
                await asyncio.wait_for(
                    asyncio.to_thread(_run),
                    timeout=UNIRIG_TIMEOUT_SEC,
                )
            except asyncio.TimeoutError:
                raise UniRigTimeoutError(
                    f"UniRig predict() timed out after {UNIRIG_TIMEOUT_SEC}s"
                )

            if not output_glb.exists():
                raise UniRigInvalidMeshError(
                    "UniRig lieferte keine rigged GLB; Mesh evtl. nicht riggbar"
                )

            rigged_bytes = output_glb.read_bytes()
            return RiggingResult(
                rigged_glb_bytes=rigged_bytes,
                provider_key=self.key,
            )
