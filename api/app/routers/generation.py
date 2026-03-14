import os
import re
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Response
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session_factory, get_session
from app.models import GenerationJob
from app.schemas.generation import (
    AnimationGenerateRequest,
    AnimationGenerateResponse,
    AnimationJobStatusResponse,
    AnimationProviderInfo,
    AnimationProvidersResponse,
    AnimationPresetsResponse,
    BgRemovalGenerateRequest,
    BgRemovalGenerateResponse,
    BgRemovalJobStatusResponse,
    BgRemovalProviderInfo,
    BgRemovalProvidersResponse,
    ImageGenerateRequest,
    ImageGenerateResponse,
    ImageJobStatusResponse,
    ImageProviderInfo,
    ImageProvidersResponse,
    JobListItem,
    JobListResponse,
    JobStatsResponse,
    JobTypeStats,
    MeshGenerateRequest,
    MeshGenerateResponse,
    MeshJobStatusResponse,
    MeshProviderInfo,
    MeshProvidersResponse,
    ModelsResponse,
    MotionPresetSchema,
    RiggingGenerateRequest,
    RiggingGenerateResponse,
    RiggingJobStatusResponse,
    RiggingProviderInfo,
    RiggingProvidersResponse,
)
from app.services.bgremoval import run_bgremoval
from app.services.bgremoval_providers import (
    get_provider as get_bgremoval_provider,
    list_providers as list_bgremoval_providers,
)
from app.services.image_providers import get_provider as get_image_provider, list_providers
from app.services.mesh_generation import (
    run_mesh_generation,
    run_mesh_generation_with_auto_bgremoval,
)
from app.services.mesh_providers import MESH_PROVIDERS, get_provider as get_mesh_provider
from app.services.picsart import run_image_generation
from app.services import asset_service
from app.services.animation_generation import run_animation
from app.services.rigging_generation import run_rigging
from app.providers.animation import (
    get_animation_provider,
    list_animation_providers,
)
from app.providers.rigging import get_rigging_provider, list_rigging_providers

router = APIRouter(prefix="/generate", tags=["generation"])


def _extract_asset_id_from_url(url: str) -> UUID | None:
    """Extrahiert asset_id aus /assets/{asset_id}/files/... URL."""
    m = re.search(r"/assets/([0-9a-fA-F-]{36})/files/", url)
    if m:
        try:
            return UUID(m.group(1))
        except ValueError:
            pass
    return None


async def _persist_job_completion(job_id: str) -> None:
    """Persistiert abgeschlossenen Job in Asset-Ordner."""
    async with async_session_factory() as session:
        result = await session.execute(
            select(GenerationJob).where(GenerationJob.id == UUID(job_id))
        )
        job = result.scalar_one_or_none()
        if not job or job.status != "done":
            return

        # Asset-ID ermitteln: job.asset_id, source_job_id oder aus source_image_url
        asset_id_str: str | None = str(job.asset_id) if job.asset_id else None
        if not asset_id_str and job.source_job_id:
            src = await session.execute(
                select(GenerationJob).where(GenerationJob.id == job.source_job_id)
            )
            src_job = src.scalar_one_or_none()
            if src_job and src_job.asset_id:
                asset_id_str = str(src_job.asset_id)
        if not asset_id_str and job.source_image_url:
            aid = _extract_asset_id_from_url(job.source_image_url)
            if aid:
                asset_id_str = str(aid)

        asset_id = asset_service.get_or_create_asset_id(asset_id_str)

        if job.asset_id != UUID(asset_id):
            job.asset_id = UUID(asset_id)
            await session.commit()

        if job.job_type == "image" and job.result_url:
            await asset_service.persist_image_job(
                str(job.id),
                asset_id,
                job.provider_key,
                job.prompt,
                job.result_url,
            )
        elif job.job_type == "bgremoval" and (job.result_url or job.bgremoval_result_url):
            url = job.bgremoval_result_url or job.result_url or ""
            source_file = "image_original.png"
            if job.source_image_url and "/assets/" in job.source_image_url:
                # Quelle war Asset-Datei
                pass  # source_file bleibt image_original.png
            await asset_service.persist_bgremoval_job(
                str(job.id),
                asset_id,
                job.provider_key or job.bgremoval_provider_key or "",
                source_file,
                url,
            )
        elif job.job_type == "mesh" and job.glb_file_path:
            # Bei auto_bgremoval zuerst BgRemoval-Step persistieren
            if job.bgremoval_result_url:
                await asset_service.persist_bgremoval_job(
                    str(job.id),
                    asset_id,
                    job.bgremoval_provider_key or "",
                    "image_original.png",
                    job.bgremoval_result_url,
                )
            source_file = "image_bgremoved.png" if job.bgremoval_result_url else "image_original.png"
            await asset_service.persist_mesh_job(
                str(job.id),
                asset_id,
                job.provider_key or "",
                source_file,
                job.glb_file_path,
            )
        elif job.job_type == "rigging" and job.glb_file_path:
            await asset_service.persist_rigging_job(
                str(job.id),
                asset_id,
                job.provider_key or "",
                "mesh.glb",
                job.glb_file_path,
            )
        elif job.job_type == "animation" and job.glb_file_path:
            source_file = "mesh.glb"
            if job.source_image_url and "/files/" in (job.source_image_url or ""):
                parts = (job.source_image_url or "").rstrip("/").split("/")
                if parts:
                    source_file = parts[-1] or "mesh.glb"
            anim_path = Path(job.glb_file_path)
            if not anim_path.exists():
                return
            animated_bytes = anim_path.read_bytes()
            ext = anim_path.suffix.lstrip(".") or "glb"
            filename = f"mesh_animated.{ext}"
            await asset_service.persist_animation_job(
                str(job.id),
                asset_id,
                job.provider_key or "",
                job.prompt or "",
                source_file,
                animated_bytes,
                filename=filename,
            )


async def _update_job(
    job_id: str,
    status: str,
    result_url: str | None,
    error_msg: str | None = None,
    error_type: str | None = None,
    error_detail: str | None = None,
) -> None:
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
            if error_type is not None:
                job.error_type = error_type
            if error_detail is not None:
                job.error_detail = error_detail
            await session.commit()
    if status == "done":
        await _persist_job_completion(job_id)


async def _update_glb_job(
    job_id: str,
    status: str,
    glb_file_path: str | None,
    error_msg: str | None = None,
    error_type: str | None = None,
    error_detail: str | None = None,
) -> None:
    """Generischer Update-Handler für Jobs mit glb_file_path (Mesh, Rigging, Animation)."""
    async with async_session_factory() as session:
        result = await session.execute(
            select(GenerationJob).where(GenerationJob.id == UUID(job_id))
        )
        job = result.scalar_one_or_none()
        if job:
            job.status = status
            job.updated_at = datetime.now(timezone.utc)
            if glb_file_path is not None:
                job.glb_file_path = glb_file_path
            if error_msg is not None:
                job.error_msg = error_msg
            if error_type is not None:
                job.error_type = error_type
            if error_detail is not None:
                job.error_detail = error_detail
            await session.commit()
    if status == "done":
        await _persist_job_completion(job_id)


# Aliase für bestehende Aufrufstellen, delegieren an _update_glb_job
_update_mesh_job = _update_glb_job
_update_rigging_job = _update_glb_job


async def _update_mesh_job_bgremoval(
    job_id: str, bgremoval_provider_key: str, bgremoval_result_url: str
) -> None:
    async with async_session_factory() as session:
        result = await session.execute(
            select(GenerationJob).where(GenerationJob.id == UUID(job_id))
        )
        job = result.scalar_one_or_none()
        if job:
            job.bgremoval_provider_key = bgremoval_provider_key
            job.bgremoval_result_url = bgremoval_result_url
            job.updated_at = datetime.now(timezone.utc)
            await session.commit()


async def _update_bgremoval_job(
    job_id: str,
    status: str,
    result_url: str | None,
    error_msg: str | None = None,
    error_type: str | None = None,
    error_detail: str | None = None,
) -> None:
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
                job.bgremoval_result_url = result_url
            if error_msg is not None:
                job.error_msg = error_msg
            if error_type is not None:
                job.error_type = error_type
            if error_detail is not None:
                job.error_detail = error_detail
            await session.commit()
    if status == "done":
        await _persist_job_completion(job_id)


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
async def create_image_generation(
    body: ImageGenerateRequest,
    background_tasks: BackgroundTasks,
    response: Response,
    session: AsyncSession = Depends(get_session),
):
    provider_key, params = body.resolve_provider_and_params()

    try:
        get_image_provider(provider_key)
    except ValueError:
        raise HTTPException(422, detail=f"Unbekannter provider_key: {provider_key}")

    asset_id: UUID | None = None
    if body.asset_id:
        try:
            asset_id = UUID(body.asset_id)
        except ValueError:
            pass

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
        raise HTTPException(404, detail="Job nicht gefunden")

    provider_key = job.provider_key or job.model_key or ""
    return ImageJobStatusResponse(
        job_id=job.id,
        status=job.status,
        result_url=job.result_url,
        error_msg=job.error_msg,
        error_type=job.error_type,
        error_detail=job.error_detail,
        provider_key=provider_key,
        model_key=provider_key,
        created_at=job.created_at,
        updated_at=job.updated_at,
        asset_id=job.asset_id,
        prompt=job.prompt,
        failed_at=job.updated_at if job.status == "failed" else None,
    )


@router.get("/bgremoval/providers", response_model=BgRemovalProvidersResponse)
async def list_bgremoval_providers_endpoint():
    """Listet alle verfügbaren Background-Removal-Provider."""
    providers = list_bgremoval_providers()
    return BgRemovalProvidersResponse(
        providers=[
            BgRemovalProviderInfo(
                key=p.provider_key,
                display_name=p.display_name,
                default_params=p.default_params(),
                param_schema=p.param_schema(),
            )
            for p in providers
        ]
    )


@router.post("/bgremoval", response_model=BgRemovalGenerateResponse, status_code=202)
async def create_bgremoval(
    body: BgRemovalGenerateRequest,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
):
    try:
        get_bgremoval_provider(body.provider_key)
    except ValueError:
        raise HTTPException(
            422, detail=f"Unbekannter provider_key: {body.provider_key}"
        )

    asset_id: UUID | None = None
    if body.asset_id:
        try:
            asset_id = UUID(body.asset_id)
        except ValueError:
            pass
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
        job_type="bgremoval",
        status="pending",
        prompt="[bgremoval]",
        provider_key=body.provider_key,
        source_image_url=body.source_image_url,
        source_job_id=body.source_job_id,
        bgremoval_provider_key=body.provider_key,
        asset_id=asset_id,
    )
    session.add(job)
    await session.commit()
    await session.refresh(job)

    background_tasks.add_task(
        run_bgremoval,
        str(job.id),
        body.source_image_url,
        body.provider_key,
        _update_bgremoval_job,
    )

    return BgRemovalGenerateResponse(job_id=job.id, status="pending")


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
        raise HTTPException(404, detail="Job nicht gefunden")
    if job.status != "failed":
        raise HTTPException(400, detail="Nur fehlgeschlagene Jobs können erneut versucht werden")

    provider_key = job.provider_key or job.model_key or ""
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


@router.get("/bgremoval/{job_id}", response_model=BgRemovalJobStatusResponse)
async def get_bgremoval_job_status(
    job_id: UUID,
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(GenerationJob).where(
            GenerationJob.id == job_id,
            GenerationJob.job_type == "bgremoval",
        )
    )
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(404, detail="Job nicht gefunden")

    provider_key = job.bgremoval_provider_key or job.provider_key or ""
    return BgRemovalJobStatusResponse(
        job_id=job.id,
        status=job.status,
        result_url=job.bgremoval_result_url or job.result_url,
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


@router.post("/bgremoval/retry/{job_id}", response_model=BgRemovalGenerateResponse, status_code=202)
async def retry_bgremoval_job(
    job_id: UUID,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
):
    """Erstellt neuen Job mit gleichen Parametern wie fehlgeschlagener Job."""
    result = await session.execute(
        select(GenerationJob).where(
            GenerationJob.id == job_id,
            GenerationJob.job_type == "bgremoval",
        )
    )
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(404, detail="Job nicht gefunden")
    if job.status != "failed":
        raise HTTPException(400, detail="Nur fehlgeschlagene Jobs können erneut versucht werden")

    source_image_url = job.source_image_url or ""
    if not source_image_url:
        raise HTTPException(400, detail="Quellbild-URL fehlt für Retry")

    provider_key = job.bgremoval_provider_key or job.provider_key or ""

    new_job = GenerationJob(
        job_type="bgremoval",
        status="pending",
        prompt="[bgremoval]",
        provider_key=provider_key,
        source_image_url=source_image_url,
        source_job_id=job.source_job_id,
        bgremoval_provider_key=provider_key,
        asset_id=job.asset_id,
    )
    session.add(new_job)
    await session.commit()
    await session.refresh(new_job)

    background_tasks.add_task(
        run_bgremoval,
        str(new_job.id),
        source_image_url,
        provider_key,
        _update_bgremoval_job,
    )

    return BgRemovalGenerateResponse(job_id=new_job.id, status="pending")


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
async def create_mesh_generation(
    body: MeshGenerateRequest,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
):
    try:
        get_mesh_provider(body.provider_key)
    except ValueError as e:
        raise HTTPException(422, detail=str(e))

    # Rückwärtskompatibilität: steps → params für hunyuan3d-2
    params = dict(body.params)
    if body.steps is not None and body.provider_key == "hunyuan3d-2":
        params.setdefault("steps", body.steps)

    asset_id: UUID | None = None
    if body.asset_id:
        try:
            asset_id = UUID(body.asset_id)
        except ValueError:
            pass
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

    if body.auto_bgremoval:
        try:
            get_bgremoval_provider(body.bgremoval_provider_key)
        except ValueError:
            raise HTTPException(
                422,
                detail=f"Unbekannter bgremoval provider_key: {body.bgremoval_provider_key}",
            )
        background_tasks.add_task(
            run_mesh_generation_with_auto_bgremoval,
            str(job.id),
            body.source_image_url,
            body.provider_key,
            params,
            body.auto_bgremoval,
            body.bgremoval_provider_key,
            _update_mesh_job,
            _update_mesh_job_bgremoval,
        )
    else:
        background_tasks.add_task(
            run_mesh_generation,
            str(job.id),
            body.source_image_url,
            body.provider_key,
            params,
            _update_mesh_job,
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
        raise HTTPException(404, detail="Job nicht gefunden")

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
        raise HTTPException(404, detail="Job nicht gefunden")
    if job.status != "failed":
        raise HTTPException(400, detail="Nur fehlgeschlagene Jobs können erneut versucht werden")

    source_image_url = job.source_image_url or ""
    if not source_image_url:
        raise HTTPException(400, detail="Quellbild-URL fehlt für Retry")

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
        _update_mesh_job,
    )

    return MeshGenerateResponse(job_id=new_job.id, status="pending")


@router.get("/rigging/providers", response_model=RiggingProvidersResponse)
async def list_rigging_providers_endpoint():
    """Listet alle verfügbaren Rigging-Provider."""
    providers = list_rigging_providers()
    return RiggingProvidersResponse(
        providers=[
            RiggingProviderInfo(
                key=p.key,
                display_name=p.display_name,
            )
            for p in providers
        ]
    )


@router.post("/rigging", response_model=RiggingGenerateResponse, status_code=202)
async def create_rigging(
    body: RiggingGenerateRequest,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
):
    try:
        get_rigging_provider(body.provider_key)
    except ValueError:
        raise HTTPException(
            422, detail=f"Unbekannter provider_key: {body.provider_key}"
        )

    asset_id: UUID | None = None
    if body.asset_id:
        try:
            asset_id = UUID(body.asset_id)
        except ValueError:
            pass
    if asset_id is None:
        aid = _extract_asset_id_from_url(body.source_glb_url)
        if aid:
            asset_id = aid

    job = GenerationJob(
        job_type="rigging",
        status="pending",
        prompt="[rigging]",
        provider_key=body.provider_key,
        source_image_url=body.source_glb_url,
        asset_id=asset_id,
    )
    session.add(job)
    await session.commit()
    await session.refresh(job)

    background_tasks.add_task(
        run_rigging,
        str(job.id),
        body.source_glb_url,
        body.provider_key,
        str(asset_id) if asset_id else None,
        _update_rigging_job,
    )

    return RiggingGenerateResponse(job_id=job.id, status="pending")


@router.get("/rigging/{job_id}", response_model=RiggingJobStatusResponse)
async def get_rigging_job_status(
    job_id: UUID,
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(GenerationJob).where(
            GenerationJob.id == job_id,
            GenerationJob.job_type == "rigging",
        )
    )
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(404, detail="Job nicht gefunden")

    glb_url = None
    if job.status == "done" and job.glb_file_path:
        glb_url = f"/static/meshes/{job.id}_rigged.glb"

    return RiggingJobStatusResponse(
        job_id=job.id,
        status=job.status,
        glb_url=glb_url,
        error_msg=job.error_msg,
        error_type=job.error_type,
        error_detail=job.error_detail,
        source_glb_url=job.source_image_url or "",
        provider_key=job.provider_key or "unirig",
        created_at=job.created_at,
        updated_at=job.updated_at,
        asset_id=job.asset_id,
        failed_at=job.updated_at if job.status == "failed" else None,
    )


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
        raise HTTPException(422, detail=f"Unbekannter provider_key: {provider_key}")
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
async def create_animation(
    body: AnimationGenerateRequest,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
):
    if not os.getenv("HF_TOKEN"):
        raise HTTPException(
            503,
            detail=(
                "HF_TOKEN nicht konfiguriert. Animation-Provider (HY-Motion) "
                "benötigt einen Hugging Face Token. Bitte HF_TOKEN in der Umgebung setzen."
            ),
        )
    try:
        get_animation_provider(body.provider_key)
    except ValueError:
        raise HTTPException(
            422, detail=f"Unbekannter provider_key: {body.provider_key}"
        )

    asset_id: UUID | None = None
    if body.asset_id:
        try:
            asset_id = UUID(body.asset_id)
        except ValueError:
            pass
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
        _update_mesh_job,
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
        raise HTTPException(404, detail="Job nicht gefunden")

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


@router.get("/jobs", response_model=JobListResponse)
async def list_jobs(
    job_type: str | None = Query(default=None, description="Filtert nach Job-Typ: image, bgremoval, mesh, rigging, animation"),
    status: str | None = Query(default=None, description="Filtert nach Status: pending, processing, done, failed"),
    asset_id: UUID | None = Query(default=None, description="Filtert nach Asset-ID"),
    limit: int = Query(default=50, ge=1, le=200, description="Maximale Anzahl Ergebnisse"),
    offset: int = Query(default=0, ge=0, description="Anzahl übersprungener Ergebnisse"),
    session: AsyncSession = Depends(get_session),
):
    """Paginierte Liste aller Jobs mit optionalen Filtern."""
    query = select(GenerationJob)
    count_query = select(func.count()).select_from(GenerationJob)

    if job_type is not None:
        query = query.where(GenerationJob.job_type == job_type)
        count_query = count_query.where(GenerationJob.job_type == job_type)
    if status is not None:
        query = query.where(GenerationJob.status == status)
        count_query = count_query.where(GenerationJob.status == status)
    if asset_id is not None:
        query = query.where(GenerationJob.asset_id == asset_id)
        count_query = count_query.where(GenerationJob.asset_id == asset_id)

    total_result = await session.execute(count_query)
    total = total_result.scalar_one()

    query = query.order_by(GenerationJob.created_at.desc()).offset(offset).limit(limit)
    result = await session.execute(query)
    jobs = result.scalars().all()

    return JobListResponse(
        jobs=[
            JobListItem(
                job_id=j.id,
                job_type=j.job_type,
                status=j.status,
                provider_key=j.provider_key or "",
                prompt=j.prompt if j.job_type == "image" else None,
                asset_id=j.asset_id,
                created_at=j.created_at,
                updated_at=j.updated_at,
                error_type=j.error_type,
            )
            for j in jobs
        ],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/stats", response_model=JobStatsResponse)
async def get_job_stats(session: AsyncSession = Depends(get_session)):
    """Statistiken über alle Jobs, gruppiert nach Typ und Status."""
    result = await session.execute(
        select(
            GenerationJob.job_type,
            GenerationJob.status,
            func.count().label("cnt"),
        ).group_by(GenerationJob.job_type, GenerationJob.status)
    )
    rows = result.all()

    # Aggregation nach job_type
    agg: dict[str, dict[str, int]] = {}
    for job_type, status, cnt in rows:
        if job_type not in agg:
            agg[job_type] = {"total": 0, "pending": 0, "processing": 0, "done": 0, "failed": 0}
        agg[job_type]["total"] += cnt
        if status in agg[job_type]:
            agg[job_type][status] += cnt

    by_type = [
        JobTypeStats(
            job_type=jt,
            total=stats["total"],
            pending=stats["pending"],
            processing=stats["processing"],
            done=stats["done"],
            failed=stats["failed"],
        )
        for jt, stats in sorted(agg.items())
    ]

    return JobStatsResponse(
        total_jobs=sum(s.total for s in by_type),
        by_type=by_type,
    )


@router.get("/models", response_model=ModelsResponse)
async def list_models():
    """Listet alle Provider-Keys (Rückwärtskompatibel mit /generate/image/providers)."""
    return ModelsResponse(models=[p.provider_key for p in list_providers()])


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
        raise HTTPException(404, detail="Job nicht gefunden")
    if job.status != "failed":
        raise HTTPException(
            400,
            detail="Nur fehlgeschlagene Jobs können erneut versucht werden",
        )

    source_glb_url = job.source_image_url or ""
    if not source_glb_url:
        raise HTTPException(
            400, detail="Quell-GLB-URL fehlt für Retry"
        )

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
        _update_mesh_job,
    )

    return AnimationGenerateResponse(job_id=new_job.id, status="pending")
