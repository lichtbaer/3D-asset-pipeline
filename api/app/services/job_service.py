"""
Zentraler Job-Service für GenerationJob-Status-Updates.
Konsolidiert pending → running → done/failed Logik.
"""

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy import select

from app.database import async_session_factory
from app.models import GenerationJob
from app.models.enums import JobStatus
from app.services import asset_service

# Job-Typen die result_url nutzen (Image, BgRemoval, Sketchfab)
_RESULT_URL_JOB_TYPES = frozenset({"image", "bgremoval", "sketchfab_upload"})

# Job-Typen die glb_file_path nutzen
_GLB_JOB_TYPES = frozenset({"mesh", "rigging", "animation"})


def extract_asset_id_from_url(url: str) -> UUID | None:
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
        if not job or job.status != JobStatus.DONE:
            return

        asset_id_str: str | None = str(job.asset_id) if job.asset_id else None
        if not asset_id_str and job.source_job_id:
            src = await session.execute(
                select(GenerationJob).where(GenerationJob.id == job.source_job_id)
            )
            src_job = src.scalar_one_or_none()
            if src_job and src_job.asset_id:
                asset_id_str = str(src_job.asset_id)
        if not asset_id_str and job.source_image_url:
            aid = extract_asset_id_from_url(job.source_image_url or "")
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
        elif job.job_type == "bgremoval" and (
            job.result_url or job.bgremoval_result_url
        ):
            url = job.bgremoval_result_url or job.result_url or ""
            await asset_service.persist_bgremoval_job(
                str(job.id),
                asset_id,
                job.provider_key or job.bgremoval_provider_key or "",
                "image_original.png",
                url,
            )
        elif job.job_type == "mesh" and job.glb_file_path:
            if job.bgremoval_result_url:
                await asset_service.persist_bgremoval_job(
                    str(job.id),
                    asset_id,
                    job.bgremoval_provider_key or "",
                    "image_original.png",
                    job.bgremoval_result_url,
                )
            source_file = (
                "image_bgremoved.png"
                if job.bgremoval_result_url
                else "image_original.png"
            )
            await asset_service.persist_mesh_job(
                str(job.id),
                asset_id,
                job.provider_key or "",
                source_file,
                job.glb_file_path,
            )
            # Auto-Tagging: Best-Effort, darf Fehler nicht weiterwerfen
            from app.services.auto_tag_service import auto_tag_asset_after_mesh  # noqa: PLC0415
            await auto_tag_asset_after_mesh(asset_id)
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


class JobService:
    """Zentralisierte Job-Status-Updates für GenerationJob."""

    async def start(self, job_id: str) -> None:
        """Setzt Job-Status auf processing."""
        await self._update_status(job_id, JobStatus.PROCESSING)

    async def complete(
        self,
        job_id: str,
        *,
        result_url: str | None = None,
        glb_file_path: str | None = None,
        bgremoval_result_url: str | None = None,
    ) -> None:
        """Setzt Job-Status auf done. result_url für Image/BgRemoval, glb_file_path für Mesh/Rigging/Animation."""
        async with async_session_factory() as session:
            result = await session.execute(
                select(GenerationJob).where(GenerationJob.id == UUID(job_id))
            )
            job = result.scalar_one_or_none()
            if job:
                job.status = JobStatus.DONE
                job.updated_at = datetime.now(timezone.utc)
                if result_url is not None:
                    job.result_url = result_url
                if glb_file_path is not None:
                    job.glb_file_path = glb_file_path
                if bgremoval_result_url is not None:
                    job.bgremoval_result_url = bgremoval_result_url
                await session.commit()
        await _persist_job_completion(job_id)

    async def update_bgremoval_fields(
        self,
        job_id: str,
        bgremoval_provider_key: str,
        bgremoval_result_url: str,
    ) -> None:
        """Aktualisiert BgRemoval-Felder bei Mesh-Jobs mit auto_bgremoval."""
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

    async def fail(
        self,
        job_id: str,
        error: str,
        *,
        error_type: str | None = None,
        error_detail: str | None = None,
    ) -> None:
        """Setzt Job-Status auf failed."""
        await self._update_status(
            job_id,
            JobStatus.FAILED,
            error_msg=error,
            error_type=error_type or type(error).__name__,
            error_detail=error_detail or error,
        )

    async def get(self, job_id: str) -> dict[str, Any] | None:
        """Gibt Job-Daten als Dict zurück oder None wenn nicht gefunden."""
        async with async_session_factory() as session:
            result = await session.execute(
                select(GenerationJob).where(GenerationJob.id == UUID(job_id))
            )
            job = result.scalar_one_or_none()
            if not job:
                return None
            return {
                "id": str(job.id),
                "job_type": job.job_type,
                "status": job.status,
                "prompt": job.prompt,
                "provider_key": job.provider_key,
                "result_url": job.result_url,
                "glb_file_path": job.glb_file_path,
                "asset_id": str(job.asset_id) if job.asset_id else None,
                "error_msg": job.error_msg,
                "error_type": job.error_type,
                "error_detail": job.error_detail,
                "created_at": job.created_at,
                "updated_at": job.updated_at,
            }

    async def _update_status(
        self,
        job_id: str,
        status: str,
        *,
        result_url: str | None = None,
        glb_file_path: str | None = None,
        error_msg: str | None = None,
        error_type: str | None = None,
        error_detail: str | None = None,
    ) -> None:
        """Interner Status-Update für alle Felder."""
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
                if glb_file_path is not None:
                    job.glb_file_path = glb_file_path
                if error_msg is not None:
                    job.error_msg = error_msg
                if error_type is not None:
                    job.error_type = error_type
                if error_detail is not None:
                    job.error_detail = error_detail
                await session.commit()
        if status == JobStatus.DONE:
            await _persist_job_completion(job_id)


_job_service: JobService | None = None


def get_job_service() -> JobService:
    """Singleton-Instanz des JobService."""
    global _job_service
    if _job_service is None:
        _job_service = JobService()
    return _job_service
