"""Animation sub-router."""

import os
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import raise_api_error
from app.core.rate_limit import limiter
from app.database import get_session
from app.models import GenerationJob
from app.providers.animation import (
    get_animation_provider,
    list_animation_providers,
)
from app.routers._generation_helpers import (
    _extract_asset_id_from_url,
    _update_glb_job,
)
from app.schemas.generation import (
    AnimationGenerateRequest,
    AnimationGenerateResponse,
    AnimationJobStatusResponse,
    AnimationPresetsResponse,
    AnimationProviderInfo,
    AnimationProvidersResponse,
    MotionPresetSchema,
)
from app.services.animation_generation import run_animation

router = APIRouter()


@router.get("/animation/providers", response_model=AnimationProvidersResponse)
async def list_animation_providers_endpoint():
    """Listet alle verfügbaren Animation-Provider."""
    providers = list_animation_providers()
    return AnimationProvidersResponse(
        providers=[
            AnimationProviderInfo(key=p.key, display_name=p.display_name)
            for p in providers
        ]
    )


@router.get(
    "/animation/presets/{provider_key}",
    response_model=AnimationPresetsResponse,
)
async def get_animation_presets(provider_key: str):
    """Liefert die Motion-Presets für einen Provider."""
    try:
        provider = get_animation_provider(provider_key)
    except ValueError:
        raise_api_error(422, f"Unbekannter provider_key: {provider_key}", code="UNKNOWN_PROVIDER")
    presets = provider.get_preset_motions()
    return AnimationPresetsResponse(
        presets=[
            MotionPresetSchema(
                key=p.key,
                display_name=p.display_name,
                prompt=p.prompt,
            )
            for p in presets
        ]
    )


@router.post("/animation", response_model=AnimationGenerateResponse, status_code=202)
@limiter.limit("10/minute")
async def create_animation(
    request: Request,
    body: AnimationGenerateRequest,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
):
    if not os.getenv("HF_TOKEN"):
        raise_api_error(
            503,
            "HF_TOKEN nicht konfiguriert. Animation-Provider (HY-Motion) "
            "benötigt einen Hugging Face Token. Bitte HF_TOKEN in der Umgebung setzen.",
            code="SERVICE_UNAVAILABLE",
        )
    try:
        get_animation_provider(body.provider_key)
    except ValueError:
        raise_api_error(422, f"Unbekannter provider_key: {body.provider_key}", code="UNKNOWN_PROVIDER")

    asset_id: UUID | None = None
    if body.asset_id:
        try:
            asset_id = UUID(body.asset_id)
        except ValueError:
            raise_api_error(
                422, f"Ungültige asset_id: {body.asset_id}",
                code="VALIDATION_ERROR",
            )
    if asset_id is None:
        aid = _extract_asset_id_from_url(body.source_glb_url)
        if aid:
            asset_id = aid

    job = GenerationJob(
        job_type="animation",
        status="pending",
        prompt=body.motion_prompt,
        provider_key=body.provider_key,
        source_image_url=body.source_glb_url,
        asset_id=asset_id,
    )
    session.add(job)
    await session.commit()
    await session.refresh(job)

    background_tasks.add_task(
        run_animation,
        str(job.id),
        body.source_glb_url,
        body.motion_prompt,
        body.provider_key,
        str(asset_id) if asset_id else None,
        _update_glb_job,
    )

    return AnimationGenerateResponse(job_id=job.id, status="pending")


@router.get("/animation/{job_id}", response_model=AnimationJobStatusResponse)
async def get_animation_job_status(
    job_id: UUID,
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(GenerationJob).where(
            GenerationJob.id == job_id,
            GenerationJob.job_type == "animation",
        )
    )
    job = result.scalar_one_or_none()
    if not job:
        raise_api_error(404, "Job nicht gefunden", code="JOB_NOT_FOUND")

    animated_url = None
    if job.status == "done" and job.glb_file_path:
        anim_path = Path(job.glb_file_path)
        if anim_path.exists():
            filename = anim_path.name
            animated_url = f"/static/animations/{filename}"

    return AnimationJobStatusResponse(
        job_id=job.id,
        status=job.status,
        animated_glb_url=animated_url,
        error_msg=job.error_msg,
        error_type=job.error_type,
        error_detail=job.error_detail,
        source_glb_url=job.source_image_url or "",
        provider_key=job.provider_key or "hy-motion",
        motion_prompt=job.prompt or "",
        created_at=job.created_at,
        updated_at=job.updated_at,
        asset_id=job.asset_id,
        failed_at=job.updated_at if job.status == "failed" else None,
    )


@router.post(
    "/animation/retry/{job_id}",
    response_model=AnimationGenerateResponse,
    status_code=202,
)
async def retry_animation_job(
    job_id: UUID,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
):
    """Erstellt neuen Job mit gleichen Parametern wie fehlgeschlagener Job."""
    result = await session.execute(
        select(GenerationJob).where(
            GenerationJob.id == job_id,
            GenerationJob.job_type == "animation",
        )
    )
    job = result.scalar_one_or_none()
    if not job:
        raise_api_error(404, "Job nicht gefunden", code="JOB_NOT_FOUND")
    if job.status != "failed":
        raise_api_error(400, "Nur fehlgeschlagene Jobs können erneut versucht werden", code="INVALID_STATE")

    source_glb_url = job.source_image_url or ""
    if not source_glb_url:
        raise_api_error(400, "Quell-GLB-URL fehlt für Retry", code="MISSING_SOURCE")

    new_job = GenerationJob(
        job_type="animation",
        status="pending",
        prompt=job.prompt or "",
        provider_key=job.provider_key or "hy-motion",
        source_image_url=source_glb_url,
        asset_id=job.asset_id,
    )
    session.add(new_job)
    await session.commit()
    await session.refresh(new_job)

    background_tasks.add_task(
        run_animation,
        str(new_job.id),
        source_glb_url,
        job.prompt or "",
        job.provider_key or "hy-motion",
        str(job.asset_id) if job.asset_id else None,
        _update_glb_job,
    )

    return AnimationGenerateResponse(job_id=new_job.id, status="pending")
