import re
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session_factory, get_session
from app.models import GenerationJob
from app.schemas.generation import (
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
    MeshGenerateRequest,
    MeshGenerateResponse,
    MeshJobStatusResponse,
    MeshProviderInfo,
    MeshProvidersResponse,
    ModelsResponse,
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
    if status == "done":
        await _persist_job_completion(job_id)


async def _update_mesh_job(
    job_id: str, status: str, glb_file_path: str | None, error_msg: str | None
) -> None:
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
            await session.commit()
    if status == "done":
        await _persist_job_completion(job_id)


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
    job_id: str, status: str, result_url: str | None, error_msg: str | None
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

    return ImageJobStatusResponse(
        job_id=job.id,
        status=job.status,
        result_url=job.result_url,
        error_msg=job.error_msg,
        model_key=job.provider_key or job.model_key or "",
        created_at=job.created_at,
        asset_id=job.asset_id,
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

    return BgRemovalJobStatusResponse(
        job_id=job.id,
        status=job.status,
        result_url=job.bgremoval_result_url or job.result_url,
        error_msg=job.error_msg,
        source_image_url=job.source_image_url or "",
        provider_key=job.bgremoval_provider_key or job.provider_key or "",
        created_at=job.created_at,
        asset_id=job.asset_id,
    )


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
        source_image_url=job.source_image_url or "",
        provider_key=provider_key,
        created_at=job.created_at,
        asset_id=job.asset_id,
    )


@router.get("/models", response_model=ModelsResponse)
async def list_models():
    """Listet alle Provider-Keys (Rückwärtskompatibel mit /generate/image/providers)."""
    return ModelsResponse(models=[p.provider_key for p in list_providers()])
