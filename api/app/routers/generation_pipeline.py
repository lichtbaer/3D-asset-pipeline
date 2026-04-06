"""Pipeline-Automatisierung: One-Click Full Pipeline Sub-Router."""

import asyncio
import json
from collections.abc import AsyncGenerator
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks
from fastapi.responses import StreamingResponse

from app.core.errors import raise_api_error
from app.schemas.pipeline import PipelineRunRequest, PipelineRunResponse, PipelineRunStatus
from app.services.pipeline_orchestrator import (
    create_pipeline_run,
    get_pipeline_run,
    run_pipeline,
)

router = APIRouter()


@router.post("/pipeline/run", response_model=PipelineRunResponse, status_code=202)
async def start_pipeline(
    body: PipelineRunRequest,
    background_tasks: BackgroundTasks,
) -> PipelineRunResponse:
    """
    Startet einen automatisierten Pipeline-Durchlauf.

    Führt alle aktivierten Schritte sequenziell aus:
    Image → (optional BgRemoval) → Mesh → (optional Rigging) → (optional Animation)

    Gibt sofort eine pipeline_run_id zurück. Status kann per GET /pipeline/{run_id}
    oder per SSE-Stream GET /pipeline/{run_id}/stream abgefragt werden.
    """
    run_response = await create_pipeline_run(body)
    background_tasks.add_task(run_pipeline, run_response.pipeline_run_id, body)
    return run_response


@router.get("/pipeline/{pipeline_run_id}", response_model=PipelineRunStatus)
async def get_pipeline_status(pipeline_run_id: str) -> PipelineRunStatus:
    """Gibt den aktuellen Status eines Pipeline-Runs zurück."""
    run = await get_pipeline_run(pipeline_run_id)
    if run is None:
        raise_api_error(404, f"Pipeline-Run {pipeline_run_id} nicht gefunden", code="NOT_FOUND")
    return run


_PIPELINE_POLL_INTERVAL = 2.0
_PIPELINE_STREAM_TIMEOUT = 3600.0  # 1 Stunde (Pipeline kann lange dauern)


async def _stream_pipeline_events(pipeline_run_id: str) -> AsyncGenerator[str, None]:
    """Generiert SSE-Events für Pipeline-Status bis zum Abschluss oder Timeout."""
    elapsed = 0.0
    last_payload: str | None = None

    while elapsed < _PIPELINE_STREAM_TIMEOUT:
        run = await get_pipeline_run(pipeline_run_id)

        if run is None:
            payload = json.dumps({"error": "Pipeline-Run nicht gefunden", "pipeline_run_id": pipeline_run_id})
            yield f"event: error\ndata: {payload}\n\n"
            return

        # Serialisiere Run-Status
        data = {
            "pipeline_run_id": run.pipeline_run_id,
            "status": run.status,
            "asset_id": str(run.asset_id) if run.asset_id else None,
            "error": run.error,
            "steps": [
                {
                    "step": s.step,
                    "job_id": str(s.job_id) if s.job_id else None,
                    "status": s.status,
                    "result_url": s.result_url,
                    "error": s.error,
                }
                for s in run.steps
            ],
            "updated_at": run.updated_at.isoformat() if run.updated_at else None,
        }
        payload = json.dumps(data)

        # Nur senden wenn sich etwas geändert hat
        if payload != last_payload:
            yield f"data: {payload}\n\n"
            last_payload = payload

        if run.status in ("done", "failed"):
            yield "event: done\ndata: {}\n\n"
            return

        await asyncio.sleep(_PIPELINE_POLL_INTERVAL)
        elapsed += _PIPELINE_POLL_INTERVAL

    yield "event: timeout\ndata: {\"reason\": \"stream_timeout\"}\n\n"


@router.get("/pipeline/{pipeline_run_id}/stream")
async def stream_pipeline_status(pipeline_run_id: str):
    """
    Server-Sent Events (SSE) Stream für Pipeline-Status-Updates.

    Sendet bei jeder Änderung ein Event bis die Pipeline abgeschlossen ist.
    """
    run = await get_pipeline_run(pipeline_run_id)
    if run is None:
        raise_api_error(404, f"Pipeline-Run {pipeline_run_id} nicht gefunden", code="NOT_FOUND")

    return StreamingResponse(
        _stream_pipeline_events(pipeline_run_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
