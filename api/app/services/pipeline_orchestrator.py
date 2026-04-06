"""
Pipeline-Orchestrator: Automatisierter One-Click Durchlauf durch alle Pipeline-Schritte.

Reihenfolge: Image → (optional BgRemoval) → Mesh → (optional Rigging) → (optional Animation)
"""

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy import select

from app.core.config import settings
from app.database import async_session_factory
from app.models import GenerationJob
from app.models.enums import JobStatus
from app.routers._generation_helpers import (
    _update_bgremoval_job,
    _update_glb_job,
    _update_job,
    _update_mesh_job_bgremoval,
)
from app.schemas.pipeline import (
    PipelineRunRequest,
    PipelineRunResponse,
    PipelineRunStatus,
    PipelineStepStatus,
)
from app.services.animation_generation import run_animation
from app.services.mesh_generation import run_mesh_generation
from app.services.picsart import run_image_generation
from app.services.rigging_generation import run_rigging

logger = logging.getLogger(__name__)

# Poll-Intervall für Job-Warten
_POLL_INTERVAL = 3.0    # Sekunden

# In-memory Store für Pipeline-Run-Status (indexed by pipeline_run_id)
_pipeline_runs: dict[str, PipelineRunStatus] = {}


def get_pipeline_run(pipeline_run_id: str) -> PipelineRunStatus | None:
    """Gibt den Status eines Pipeline-Runs zurück."""
    return _pipeline_runs.get(pipeline_run_id)


async def _wait_for_job(job_id: str) -> dict[str, Any] | None:
    """
    Wartet bis ein Job DONE oder FAILED ist.
    Gibt Job-Daten als Dict zurück oder None bei Timeout.
    """
    elapsed = 0.0
    while elapsed < settings.PIPELINE_JOB_TIMEOUT_S:
        async with async_session_factory() as session:
            result = await session.execute(
                select(GenerationJob).where(GenerationJob.id == UUID(job_id))
            )
            job = result.scalar_one_or_none()

        if job is None:
            logger.error("Job %s nicht gefunden beim Warten", job_id)
            return None

        if job.status in (JobStatus.DONE, JobStatus.FAILED):
            return {
                "id": str(job.id),
                "status": job.status,
                "result_url": job.result_url,
                "glb_file_path": job.glb_file_path,
                "asset_id": str(job.asset_id) if job.asset_id else None,
                "error_msg": job.error_msg,
                "error_type": job.error_type,
                "error_detail": job.error_detail,
            }

        await asyncio.sleep(_POLL_INTERVAL)
        elapsed += _POLL_INTERVAL

    logger.warning("Job %s hat Timeout nach %.0fs erreicht", job_id, settings.PIPELINE_JOB_TIMEOUT_S)
    return None


def _update_run_step(
    run_id: str,
    step: str,
    *,
    status: str,
    job_id: UUID | None = None,
    result_url: str | None = None,
    error: str | None = None,
) -> None:
    """Aktualisiert den Status eines Schritts im Pipeline-Run."""
    run = _pipeline_runs.get(run_id)
    if run is None:
        return
    for s in run.steps:
        if s.step == step:
            s.status = status
            if job_id is not None:
                s.job_id = job_id
            if result_url is not None:
                s.result_url = result_url
            if error is not None:
                s.error = error
            break
    run.updated_at = datetime.now(timezone.utc)


async def _create_image_job(
    session_factory: Any,
    prompt: str,
    provider_key: str,
    params: dict,
    asset_id: UUID | None,
) -> str:
    """Erstellt einen Image-Generierungs-Job und gibt die job_id zurück."""
    async with session_factory() as session:
        job = GenerationJob(
            job_type="image",
            status="pending",
            prompt=prompt,
            provider_key=provider_key,
            asset_id=asset_id,
        )
        session.add(job)
        await session.commit()
        await session.refresh(job)
        return str(job.id)


async def _create_bgremoval_job(
    session_factory: Any,
    source_image_url: str,
    provider_key: str,
    asset_id: UUID | None,
) -> str:
    """Erstellt einen BgRemoval-Job und gibt die job_id zurück."""
    async with session_factory() as session:
        job = GenerationJob(
            job_type="bgremoval",
            status="pending",
            prompt="[bgremoval]",
            provider_key=provider_key,
            source_image_url=source_image_url,
            asset_id=asset_id,
        )
        session.add(job)
        await session.commit()
        await session.refresh(job)
        return str(job.id)


async def _create_mesh_job(
    session_factory: Any,
    source_image_url: str,
    provider_key: str,
    asset_id: UUID | None,
) -> str:
    """Erstellt einen Mesh-Generierungs-Job und gibt die job_id zurück."""
    async with session_factory() as session:
        job = GenerationJob(
            job_type="mesh",
            status="pending",
            prompt="[mesh from image]",
            provider_key=provider_key,
            source_image_url=source_image_url,
            asset_id=asset_id,
        )
        session.add(job)
        await session.commit()
        await session.refresh(job)
        return str(job.id)


async def _create_rigging_job(
    session_factory: Any,
    source_glb_url: str,
    provider_key: str,
    asset_id: UUID | None,
) -> str:
    """Erstellt einen Rigging-Job und gibt die job_id zurück."""
    async with session_factory() as session:
        job = GenerationJob(
            job_type="rigging",
            status="pending",
            prompt="[rigging]",
            provider_key=provider_key,
            source_image_url=source_glb_url,
            asset_id=asset_id,
        )
        session.add(job)
        await session.commit()
        await session.refresh(job)
        return str(job.id)


async def _create_animation_job(
    session_factory: Any,
    source_glb_url: str,
    provider_key: str,
    motion_prompt: str,
    asset_id: UUID | None,
) -> str:
    """Erstellt einen Animations-Job und gibt die job_id zurück."""
    async with session_factory() as session:
        job = GenerationJob(
            job_type="animation",
            status="pending",
            prompt=motion_prompt,
            provider_key=provider_key,
            source_image_url=source_glb_url,
            asset_id=asset_id,
        )
        session.add(job)
        await session.commit()
        await session.refresh(job)
        return str(job.id)


async def run_pipeline(pipeline_run_id: str, request: PipelineRunRequest) -> None:
    """
    Führt den vollständigen Pipeline-Durchlauf asynchron aus.
    Wird als BackgroundTask gestartet.
    """
    run = _pipeline_runs.get(pipeline_run_id)
    if run is None:
        logger.error("Pipeline-Run %s nicht gefunden", pipeline_run_id)
        return

    asset_id: UUID | None = None

    # --- Schritt 1: Bildgenerierung ---
    _update_run_step(pipeline_run_id, "image", status="processing")
    try:
        image_params = dict(request.image_params)
        image_params.setdefault("width", 1024)
        image_params.setdefault("height", 1024)
        image_params.setdefault("count", 1)

        image_job_id = await _create_image_job(
            async_session_factory,
            request.prompt,
            request.image_provider_key,
            image_params,
            asset_id,
        )
        _update_run_step(pipeline_run_id, "image", status="processing", job_id=UUID(image_job_id))

        await run_image_generation(
            image_job_id,
            request.prompt,
            request.image_provider_key,
            image_params,
            _update_job,
        )

        image_data = await _wait_for_job(image_job_id)
        if image_data is None or image_data["status"] != JobStatus.DONE:
            error = image_data["error_detail"] if image_data else "Timeout"
            _update_run_step(pipeline_run_id, "image", status="failed", error=error)
            run.status = "failed"
            run.error = f"Bildgenerierung fehlgeschlagen: {error}"
            return

        image_url = image_data["result_url"]
        if image_data.get("asset_id"):
            asset_id = UUID(image_data["asset_id"])
        _update_run_step(pipeline_run_id, "image", status="done", result_url=image_url)
        run.asset_id = asset_id
        logger.info("Pipeline %s: Bild generiert: %s", pipeline_run_id, image_url)

    except Exception as e:
        logger.exception("Pipeline %s: Fehler in Bildgenerierung", pipeline_run_id)
        _update_run_step(pipeline_run_id, "image", status="failed", error=str(e))
        run.status = "failed"
        run.error = f"Bildgenerierung fehlgeschlagen: {e}"
        return

    # --- Schritt 2: Background-Removal (optional) ---
    mesh_source_url = image_url
    if request.enable_bgremoval:
        _update_run_step(pipeline_run_id, "bgremoval", status="processing")
        try:
            from app.services.bgremoval import run_bgremoval  # noqa: PLC0415

            bgremoval_job_id = await _create_bgremoval_job(
                async_session_factory,
                image_url,
                request.bgremoval_provider_key,
                asset_id,
            )
            _update_run_step(
                pipeline_run_id, "bgremoval",
                status="processing", job_id=UUID(bgremoval_job_id)
            )

            await run_bgremoval(
                bgremoval_job_id,
                image_url,
                request.bgremoval_provider_key,
                _update_bgremoval_job,
            )

            bgremoval_data = await _wait_for_job(bgremoval_job_id)
            if bgremoval_data is None or bgremoval_data["status"] != JobStatus.DONE:
                error = bgremoval_data["error_detail"] if bgremoval_data else "Timeout"
                _update_run_step(pipeline_run_id, "bgremoval", status="failed", error=error)
                # BgRemoval ist nicht kritisch – weiter mit Original
                logger.warning(
                    "Pipeline %s: BgRemoval fehlgeschlagen (%s), nutze Original-Bild",
                    pipeline_run_id, error
                )
            else:
                mesh_source_url = bgremoval_data["result_url"] or image_url
                _update_run_step(
                    pipeline_run_id, "bgremoval",
                    status="done", result_url=mesh_source_url
                )
                logger.info("Pipeline %s: BgRemoval abgeschlossen: %s", pipeline_run_id, mesh_source_url)

        except Exception as e:
            logger.warning("Pipeline %s: BgRemoval-Fehler (%s), nutze Original-Bild", pipeline_run_id, e)
            _update_run_step(pipeline_run_id, "bgremoval", status="failed", error=str(e))

    # --- Schritt 3: Mesh-Generierung ---
    _update_run_step(pipeline_run_id, "mesh", status="processing")
    try:
        mesh_job_id = await _create_mesh_job(
            async_session_factory,
            mesh_source_url,
            request.mesh_provider_key,
            asset_id,
        )
        _update_run_step(pipeline_run_id, "mesh", status="processing", job_id=UUID(mesh_job_id))

        await run_mesh_generation(
            mesh_job_id,
            mesh_source_url,
            request.mesh_provider_key,
            dict(request.mesh_params),
            _update_glb_job,
        )

        mesh_data = await _wait_for_job(mesh_job_id)
        if mesh_data is None or mesh_data["status"] != JobStatus.DONE:
            error = mesh_data["error_detail"] if mesh_data else "Timeout"
            _update_run_step(pipeline_run_id, "mesh", status="failed", error=error)
            run.status = "failed"
            run.error = f"Mesh-Generierung fehlgeschlagen: {error}"
            return

        if mesh_data.get("asset_id"):
            asset_id = UUID(mesh_data["asset_id"])
            run.asset_id = asset_id

        glb_path = mesh_data["glb_file_path"]
        glb_url = f"/static/meshes/{mesh_job_id}.glb" if glb_path else None
        _update_run_step(pipeline_run_id, "mesh", status="done", result_url=glb_url)
        logger.info("Pipeline %s: Mesh generiert: %s", pipeline_run_id, glb_path)

    except Exception as e:
        logger.exception("Pipeline %s: Fehler in Mesh-Generierung", pipeline_run_id)
        _update_run_step(pipeline_run_id, "mesh", status="failed", error=str(e))
        run.status = "failed"
        run.error = f"Mesh-Generierung fehlgeschlagen: {e}"
        return

    # Weiterer GLB-URL für Rigging/Animation
    current_glb_url = glb_url

    # --- Schritt 4: Rigging (optional) ---
    if request.enable_rigging and current_glb_url:
        _update_run_step(pipeline_run_id, "rigging", status="processing")
        try:
            rigging_job_id = await _create_rigging_job(
                async_session_factory,
                current_glb_url,
                request.rigging_provider_key,
                asset_id,
            )
            _update_run_step(
                pipeline_run_id, "rigging",
                status="processing", job_id=UUID(rigging_job_id)
            )

            await run_rigging(
                rigging_job_id,
                current_glb_url,
                request.rigging_provider_key,
                str(asset_id) if asset_id else None,
                _update_glb_job,
            )

            rigging_data = await _wait_for_job(rigging_job_id)
            if rigging_data is None or rigging_data["status"] != JobStatus.DONE:
                error = rigging_data["error_detail"] if rigging_data else "Timeout"
                _update_run_step(pipeline_run_id, "rigging", status="failed", error=error)
                logger.warning("Pipeline %s: Rigging fehlgeschlagen: %s", pipeline_run_id, error)
            else:
                if rigging_data.get("asset_id"):
                    asset_id = UUID(rigging_data["asset_id"])
                    run.asset_id = asset_id
                rigged_glb_url = f"/static/meshes/{rigging_job_id}_rigged.glb"
                _update_run_step(
                    pipeline_run_id, "rigging",
                    status="done", result_url=rigged_glb_url
                )
                current_glb_url = rigged_glb_url
                logger.info("Pipeline %s: Rigging abgeschlossen", pipeline_run_id)

        except Exception as e:
            logger.warning("Pipeline %s: Rigging-Fehler: %s", pipeline_run_id, e)
            _update_run_step(pipeline_run_id, "rigging", status="failed", error=str(e))

    # --- Schritt 5: Animation (optional) ---
    if request.enable_animation and current_glb_url:
        _update_run_step(pipeline_run_id, "animation", status="processing")
        try:
            animation_job_id = await _create_animation_job(
                async_session_factory,
                current_glb_url,
                request.animation_provider_key,
                request.motion_prompt,
                asset_id,
            )
            _update_run_step(
                pipeline_run_id, "animation",
                status="processing", job_id=UUID(animation_job_id)
            )

            await run_animation(
                animation_job_id,
                current_glb_url,
                request.motion_prompt,
                request.animation_provider_key,
                str(asset_id) if asset_id else None,
                _update_glb_job,
            )

            animation_data = await _wait_for_job(animation_job_id)
            if animation_data is None or animation_data["status"] != JobStatus.DONE:
                error = animation_data["error_detail"] if animation_data else "Timeout"
                _update_run_step(pipeline_run_id, "animation", status="failed", error=error)
                logger.warning("Pipeline %s: Animation fehlgeschlagen: %s", pipeline_run_id, error)
            else:
                if animation_data.get("asset_id"):
                    asset_id = UUID(animation_data["asset_id"])
                    run.asset_id = asset_id
                _update_run_step(
                    pipeline_run_id, "animation",
                    status="done", result_url=animation_data.get("glb_file_path")
                )
                logger.info("Pipeline %s: Animation abgeschlossen", pipeline_run_id)

        except Exception as e:
            logger.warning("Pipeline %s: Animations-Fehler: %s", pipeline_run_id, e)
            _update_run_step(pipeline_run_id, "animation", status="failed", error=str(e))

    # Pipeline abgeschlossen
    run.status = "done"
    run.updated_at = datetime.now(timezone.utc)
    logger.info("Pipeline %s abgeschlossen. Asset: %s", pipeline_run_id, run.asset_id)


def create_pipeline_run(request: PipelineRunRequest) -> PipelineRunResponse:
    """
    Erstellt einen neuen Pipeline-Run und registriert ihn im In-Memory-Store.
    Gibt die initiale Antwort zurück. Der eigentliche Durchlauf wird als BackgroundTask gestartet.
    """
    pipeline_run_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)

    # Initiale Schritt-Liste basierend auf aktivierten Optionen
    steps = [
        PipelineStepStatus(step="image", status="pending"),
        PipelineStepStatus(
            step="bgremoval",
            status="pending" if request.enable_bgremoval else "skipped"
        ),
        PipelineStepStatus(step="mesh", status="pending"),
        PipelineStepStatus(
            step="rigging",
            status="pending" if request.enable_rigging else "skipped"
        ),
        PipelineStepStatus(
            step="animation",
            status="pending" if request.enable_animation else "skipped"
        ),
    ]

    run_status = PipelineRunStatus(
        pipeline_run_id=pipeline_run_id,
        status="running",
        asset_id=None,
        steps=steps,
        created_at=now,
        updated_at=now,
    )
    _pipeline_runs[pipeline_run_id] = run_status

    return PipelineRunResponse(
        pipeline_run_id=pipeline_run_id,
        status="running",
        asset_id=None,
        steps=steps,
        created_at=now,
    )
