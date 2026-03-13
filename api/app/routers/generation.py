from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.models import MODEL_MAP
from app.database import async_session_factory, get_session
from app.models import GenerationJob
from app.schemas.generation import (
    ImageGenerateRequest,
    ImageGenerateResponse,
    ImageJobStatusResponse,
    ModelsResponse,
)
from app.services.picsart import run_image_generation

router = APIRouter(prefix="/generate", tags=["generation"])


async def _update_job(job_id: str, status: str, result_url: str | None, error_msg: str | None) -> None:
    async with async_session_factory() as session:
        result = await session.execute(
            select(GenerationJob).where(GenerationJob.id == UUID(job_id))
        )
        job = result.scalar_one_or_none()
        if job:
            job.status = status
            job.updated_at = datetime.now(timezone.utc)
            if result_url is not None:
                job.result_url = result_url
            if error_msg is not None:
                job.error_msg = error_msg
            await session.commit()


@router.post("/image", response_model=ImageGenerateResponse, status_code=202)
async def create_image_generation(
    body: ImageGenerateRequest,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
):
    if body.model_key not in MODEL_MAP:
        raise HTTPException(400, detail=f"Unbekannter model_key: {body.model_key}")

    job = GenerationJob(
        job_type="image",
        status="pending",
        prompt=body.prompt,
        model_key=body.model_key,
    )
    session.add(job)
    await session.commit()
    await session.refresh(job)

    background_tasks.add_task(
        run_image_generation,
        str(job.id),
        body.prompt,
        body.model_key,
        body.width,
        body.height,
        body.negative_prompt,
        _update_job,
    )

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
        raise HTTPException(404, detail="Job nicht gefunden")

    return ImageJobStatusResponse(
        job_id=job.id,
        status=job.status,
        result_url=job.result_url,
        error_msg=job.error_msg,
        model_key=job.model_key,
        created_at=job.created_at,
    )


@router.get("/models", response_model=ModelsResponse)
async def list_models():
    return ModelsResponse(models=list(MODEL_MAP.keys()))
