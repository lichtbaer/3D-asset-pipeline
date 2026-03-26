"""Image generation and models sub-router."""

from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, Request, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import raise_api_error
from app.core.rate_limit import limiter
from app.database import get_session
from app.models import GenerationJob
from app.routers._generation_helpers import _update_job
from app.schemas.generation import (
    ImageGenerateRequest,
    ImageGenerateResponse,
    ImageJobStatusResponse,
    ImageProviderInfo,
    ImageProvidersResponse,
    ModelsResponse,
)
from app.services.image_providers import get_provider as get_image_provider
from app.services.image_providers import list_providers
from app.services.picsart import run_image_generation

router = APIRouter()


@router.get("/image/providers", response_model=ImageProvidersResponse)
async def list_image_providers():
    """Listet alle konfigurierten Image-Provider mit param_schema."""
    providers = list_providers()
    return ImageProvidersResponse(
        providers=[
            ImageProviderInfo(
                key=p.provider_key,
                display_name=p.display_name,
                default_params=p.default_params(),
                param_schema=p.param_schema(),
            )
            for p in providers
        ]
    )


@router.post("/image", response_model=ImageGenerateResponse, status_code=202)
@limiter.limit("10/minute")
async def create_image_generation(
    request: Request,
    body: ImageGenerateRequest,
    background_tasks: BackgroundTasks,
    response: Response,
    session: AsyncSession = Depends(get_session),
):
    provider_key, params = body.resolve_provider_and_params()

    try:
        get_image_provider(provider_key)
    except ValueError:
        raise_api_error(422, f"Unbekannter provider_key: {provider_key}", code="UNKNOWN_PROVIDER")

    asset_id: UUID | None = None
    if body.asset_id:
        try:
            asset_id = UUID(body.asset_id)
        except ValueError:
            raise_api_error(
                422, f"Ungültige asset_id: {body.asset_id}",
                code="VALIDATION_ERROR",
            )

    job = GenerationJob(
        job_type="image",
        status="pending",
        prompt=body.prompt,
        provider_key=provider_key,
        asset_id=asset_id,
    )
    session.add(job)
    await session.commit()
    await session.refresh(job)

    background_tasks.add_task(
        run_image_generation,
        str(job.id),
        body.prompt,
        provider_key,
        params,
        _update_job,
    )

    if body.model_key is not None:
        response.headers["X-Deprecated"] = "model_key"
    return ImageGenerateResponse(job_id=job.id, status="pending")


@router.get("/image/{job_id}", response_model=ImageJobStatusResponse)
async def get_image_job_status(
    job_id: UUID,
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(GenerationJob).where(
            GenerationJob.id == job_id,
            GenerationJob.job_type == "image",
        )
    )
    job = result.scalar_one_or_none()
    if not job:
        raise_api_error(404, "Job nicht gefunden", code="JOB_NOT_FOUND")

    provider_key = job.provider_key or ""
    return ImageJobStatusResponse(
        job_id=job.id,
        status=job.status,
        result_url=job.result_url,
        error_msg=job.error_msg,
        error_type=job.error_type,
        error_detail=job.error_detail,
        provider_key=provider_key,
        created_at=job.created_at,
        updated_at=job.updated_at,
        asset_id=job.asset_id,
        prompt=job.prompt,
        failed_at=job.updated_at if job.status == "failed" else None,
    )


@router.post("/image/retry/{job_id}", response_model=ImageGenerateResponse, status_code=202)
async def retry_image_job(
    job_id: UUID,
    background_tasks: BackgroundTasks,
    response: Response,
    session: AsyncSession = Depends(get_session),
):
    """Erstellt neuen Job mit gleichen Parametern wie fehlgeschlagener Job."""
    result = await session.execute(
        select(GenerationJob).where(
            GenerationJob.id == job_id,
            GenerationJob.job_type == "image",
        )
    )
    job = result.scalar_one_or_none()
    if not job:
        raise_api_error(404, "Job nicht gefunden", code="JOB_NOT_FOUND")
    if job.status != "failed":
        raise_api_error(400, "Nur fehlgeschlagene Jobs können erneut versucht werden", code="INVALID_STATE")

    provider_key = job.provider_key or ""
    params = {"width": 1024, "height": 1024, "count": 1}

    new_job = GenerationJob(
        job_type="image",
        status="pending",
        prompt=job.prompt,
        provider_key=provider_key,
        asset_id=job.asset_id,
    )
    session.add(new_job)
    await session.commit()
    await session.refresh(new_job)

    background_tasks.add_task(
        run_image_generation,
        str(new_job.id),
        job.prompt,
        provider_key,
        params,
        _update_job,
    )

    return ImageGenerateResponse(job_id=new_job.id, status="pending")


@router.get("/models", response_model=ModelsResponse)
async def list_models():
    """Listet alle Provider-Keys (Rückwärtskompatibel mit /generate/image/providers)."""
    return ModelsResponse(models=[p.provider_key for p in list_providers()])
