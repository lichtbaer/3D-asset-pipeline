"""Mesh generation sub-router."""

import logging
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import raise_api_error
from app.core.rate_limit import limiter
from app.database import get_session
from app.models import GenerationJob
from app.routers._generation_helpers import (
    _extract_asset_id_from_url,
    _update_glb_job,
    _update_mesh_job_bgremoval,
)
from app.schemas.generation import (
    MeshGenerateRequest,
    MeshGenerateResponse,
    MeshJobStatusResponse,
    MeshProviderInfo,
    MeshProvidersResponse,
)
from app.services.bgremoval_providers import (
    get_provider as get_bgremoval_provider,
)
from app.services.mesh_generation import (
    run_mesh_generation,
    run_mesh_generation_with_auto_bgremoval,
)
from app.services.mesh_providers import MESH_PROVIDERS
from app.services.mesh_providers import get_provider as get_mesh_provider

logger = logging.getLogger(__name__)

router = APIRouter()


async def _run_quality_gate_bg(job_id: str, asset_id: str) -> None:
    """Führt Auto-Quality-Gate nach erfolgreichem Mesh-Job aus (Exception-sicher)."""
    try:
        from app.core.config import settings
        if not settings.agent_available:
            return

        from app.routers.agents import _run_quality_assessment_internal
        from app.services.metadata_service import get_metadata_service

        assessment = await _run_quality_assessment_internal(asset_id)
        if assessment is None:
            return

        gate_data = {
            "score": assessment.score,
            "rigging_suitable": assessment.rigging_suitable,
            "issues": [i.model_dump() for i in assessment.issues],
            "recommended_actions": [a.model_dump() for a in assessment.recommended_actions],
            "checked_after_job": job_id,
        }
        await __import__("asyncio").to_thread(
            get_metadata_service().update_quality_gate,
            asset_id,
            gate_data,
        )
        logger.debug("Quality gate completed for asset %s: score=%d", asset_id, assessment.score)
    except Exception as exc:  # noqa: BLE001 — darf nie den Mesh-Job blockieren
        logger.debug("Quality gate failed silently for asset %s: %s", asset_id, exc)


def _make_glb_callback_with_quality_gate(asset_id: str):
    """Erstellt wrapped Callback der nach Mesh-Success das Quality Gate auslöst."""
    async def _callback(
        job_id: str,
        status: str,
        result_path: str | None,
        error_msg: str | None = None,
        *,
        error_type: str | None = None,
        error_detail: str | None = None,
    ) -> None:
        await _update_glb_job(
            job_id, status, result_path, error_msg,
            error_type=error_type, error_detail=error_detail,
        )
        if status == "done":
            await _run_quality_gate_bg(job_id, asset_id)

    return _callback


@router.get("/mesh/providers", response_model=MeshProvidersResponse)
async def list_mesh_providers():
    """Listet alle verfügbaren Mesh-Provider mit Parametern und Schema."""
    providers = [
        MeshProviderInfo(
            key=p.provider_key,
            display_name=p.display_name,
            default_params=p.default_params(),
            param_schema=p.param_schema(),
        )
        for p in MESH_PROVIDERS.values()
    ]
    return MeshProvidersResponse(providers=providers)


@router.post("/mesh", response_model=MeshGenerateResponse, status_code=202)
@limiter.limit("10/minute")
async def create_mesh_generation(
    request: Request,
    body: MeshGenerateRequest,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
):
    try:
        get_mesh_provider(body.provider_key)
    except ValueError as e:
        raise_api_error(422, "Validierungsfehler", detail=str(e), code="VALIDATION_ERROR")

    # Rückwärtskompatibilität: steps → params für hunyuan3d-2
    params = dict(body.params)
    if body.steps is not None and body.provider_key == "hunyuan3d-2":
        params.setdefault("steps", body.steps)

    asset_id: UUID | None = None
    if body.asset_id:
        try:
            asset_id = UUID(body.asset_id)
        except ValueError:
            raise_api_error(
                422, f"Ungültige asset_id: {body.asset_id}",
                code="VALIDATION_ERROR",
            )
    if asset_id is None and body.source_job_id:
        src = await session.execute(
            select(GenerationJob).where(GenerationJob.id == body.source_job_id)
        )
        src_job = src.scalar_one_or_none()
        if src_job and src_job.asset_id:
            asset_id = src_job.asset_id
    if asset_id is None:
        aid = _extract_asset_id_from_url(body.source_image_url)
        if aid:
            asset_id = aid

    job = GenerationJob(
        job_type="mesh",
        status="pending",
        prompt="[mesh from image]",
        provider_key=body.provider_key,
        source_image_url=body.source_image_url,
        source_job_id=body.source_job_id,
        asset_id=asset_id,
    )
    session.add(job)
    await session.commit()
    await session.refresh(job)

    # Wähle Callback: mit Quality Gate wenn gewünscht und asset_id bekannt
    glb_callback = (
        _make_glb_callback_with_quality_gate(str(asset_id))
        if body.auto_quality_check and asset_id
        else _update_glb_job
    )

    if body.auto_bgremoval:
        try:
            get_bgremoval_provider(body.bgremoval_provider_key)
        except ValueError:
            raise_api_error(
                422,
                f"Unbekannter bgremoval provider_key: {body.bgremoval_provider_key}",
                code="UNKNOWN_PROVIDER",
            )
        background_tasks.add_task(
            run_mesh_generation_with_auto_bgremoval,
            str(job.id),
            body.source_image_url,
            body.provider_key,
            params,
            body.auto_bgremoval,
            body.bgremoval_provider_key,
            glb_callback,
            _update_mesh_job_bgremoval,
        )
    else:
        background_tasks.add_task(
            run_mesh_generation,
            str(job.id),
            body.source_image_url,
            body.provider_key,
            params,
            glb_callback,
        )

    return MeshGenerateResponse(job_id=job.id, status="pending")


@router.get("/mesh/{job_id}", response_model=MeshJobStatusResponse)
async def get_mesh_job_status(
    job_id: UUID,
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(GenerationJob).where(
            GenerationJob.id == job_id,
            GenerationJob.job_type == "mesh",
        )
    )
    job = result.scalar_one_or_none()
    if not job:
        raise_api_error(404, "Job nicht gefunden", code="JOB_NOT_FOUND")

    glb_url = None
    if job.status == "done" and job.glb_file_path:
        glb_url = f"/static/meshes/{job.id}.glb"

    # Rückwärtskompatibilität: provider_key NULL → "hunyuan3d-2"
    provider_key = job.provider_key or "hunyuan3d-2"

    return MeshJobStatusResponse(
        job_id=job.id,
        status=job.status,
        glb_url=glb_url,
        error_msg=job.error_msg,
        error_type=job.error_type,
        error_detail=job.error_detail,
        source_image_url=job.source_image_url or "",
        provider_key=provider_key,
        created_at=job.created_at,
        updated_at=job.updated_at,
        asset_id=job.asset_id,
        failed_at=job.updated_at if job.status == "failed" else None,
    )


@router.post("/mesh/retry/{job_id}", response_model=MeshGenerateResponse, status_code=202)
async def retry_mesh_job(
    job_id: UUID,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
):
    """Erstellt neuen Job mit gleichen Parametern wie fehlgeschlagener Job."""
    result = await session.execute(
        select(GenerationJob).where(
            GenerationJob.id == job_id,
            GenerationJob.job_type == "mesh",
        )
    )
    job = result.scalar_one_or_none()
    if not job:
        raise_api_error(404, "Job nicht gefunden", code="JOB_NOT_FOUND")
    if job.status != "failed":
        raise_api_error(400, "Nur fehlgeschlagene Jobs können erneut versucht werden", code="INVALID_STATE")

    source_image_url = job.source_image_url or ""
    if not source_image_url:
        raise_api_error(400, "Quellbild-URL fehlt für Retry", code="MISSING_SOURCE")

    provider_key = job.provider_key or "hunyuan3d-2"
    params = get_mesh_provider(provider_key).default_params()

    new_job = GenerationJob(
        job_type="mesh",
        status="pending",
        prompt="[mesh from image]",
        provider_key=provider_key,
        source_image_url=source_image_url,
        source_job_id=job.source_job_id,
        asset_id=job.asset_id,
    )
    session.add(new_job)
    await session.commit()
    await session.refresh(new_job)

    background_tasks.add_task(
        run_mesh_generation,
        str(new_job.id),
        source_image_url,
        provider_key,
        params,
        _update_glb_job,
    )

    return MeshGenerateResponse(job_id=new_job.id, status="pending")
