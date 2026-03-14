"""Agent-API: Prompt-Assistent, Auto-Tagging, Qualitätsbewertung, Workflow-Empfehlung."""

import asyncio
from pathlib import Path
from typing import NoReturn

from fastapi import APIRouter, HTTPException
from pydantic_ai import BinaryContent

from app.agents.models import AgentError, PromptSuggestion, TagSuggestion
from app.agents.prompt_agent import get_prompt_agent
from app.agents.tagging_agent import get_tagging_agent
from app.core.config import settings
from app.schemas.agents import (
    PromptOptimizeRequest,
    QualityAssessRequest,
    TagsSuggestRequest,
    WorkflowRecommendRequest,
)
from app.services import asset_service

router = APIRouter(prefix="/agents", tags=["agents"])


def _agent_not_available_error(agent: str) -> AgentError:
    """Strukturierter Fehler wenn Agent nicht verfügbar (kein API-Key)."""
    return AgentError(
        agent=agent,
        error_type="not_available",
        message="Agent not available: ANTHROPIC_API_KEY nicht gesetzt",
        fallback_available=False,
    )


def _raise_503(agent: str) -> None:
    """Wirft 503 mit strukturiertem AgentError."""
    err = _agent_not_available_error(agent)
    raise HTTPException(
        status_code=503,
        detail=err.model_dump(),
    )


def _build_prompt_message(body: PromptOptimizeRequest) -> str:
    """Baut die User-Nachricht für den Prompt-Agenten."""
    parts: list[str] = []
    if body.existing_prompt:
        parts.append(f"Bestehender Prompt zur Verbesserung:\n{body.existing_prompt}\n")
    parts.append(f"Charakter-Beschreibung: {body.description}")
    if body.style:
        parts.append(f"Gewünschter Stil: {body.style}")
    parts.append(f"Verwendung: {body.intended_use}")
    return "\n".join(parts)


@router.post(
    "/prompt/optimize",
    response_model=PromptSuggestion,
    responses={
        503: {"description": "Agent not available", "model": AgentError},
    },
)
async def optimize_prompt(body: PromptOptimizeRequest) -> PromptSuggestion:
    """Prompt optimieren oder aus Beschreibung generieren (PURZEL-037)."""
    if not settings.agent_available:
        _raise_503("prompt")
    agent = get_prompt_agent()
    try:
        result = await agent.run(_build_prompt_message(body))
    except Exception as e:
        raise HTTPException(
            status_code=502,
            detail={
                "agent": "prompt",
                "error_type": "model_error",
                "message": str(e),
                "fallback_available": False,
            },
        ) from e
    output = result.output
    if output is None:
        raise HTTPException(
            status_code=502,
            detail={
                "agent": "prompt",
                "error_type": "model_error",
                "message": "Agent returned no output",
                "fallback_available": False,
            },
        )
    return output


def _build_tag_suggest_message(body: TagsSuggestRequest) -> str:
    """Baut die User-Nachricht für den Tagging-Agenten."""
    parts: list[str] = [f"Asset-ID: {body.asset_id}"]
    if body.prompt:
        parts.append(f"Generierungs-Prompt: {body.prompt}")
    if body.original_filename:
        parts.append(f"Original-Dateiname: {body.original_filename}")
    if body.pipeline_steps:
        parts.append(f"Pipeline-Stand: {', '.join(body.pipeline_steps)}")
    return "\n".join(parts)


def _get_preview_image_path(asset_id: str) -> tuple[Path | None, str | None]:
    """Erstes verfügbares Bild (image oder bgremoval) für Vision-Analyse."""
    meta = asset_service.get_asset(asset_id)
    if not meta:
        return None, None
    for step in ("image", "bgremoval"):
        if step in meta.steps and meta.steps[step].get("file"):
            filename = meta.steps[step]["file"]
            path = asset_service.get_file_path(asset_id, filename)
            if path and path.is_file():
                suffix = Path(filename).suffix.lower()
                media = "image/png" if suffix == ".png" else "image/jpeg"
                return path, media
    return None, None


@router.post(
    "/tags/suggest",
    response_model=TagSuggestion,
    responses={
        503: {"description": "Agent not available", "model": AgentError},
    },
)
async def suggest_tags(body: TagsSuggestRequest) -> TagSuggestion:
    """Tags vorschlagen basierend auf Prompt, Dateiname, Pipeline-Stand und optional Bild."""
    if not settings.agent_available:
        _raise_503("tagging")
    meta = asset_service.get_asset(body.asset_id)
    if not meta:
        raise HTTPException(404, detail="Asset nicht gefunden")
    pipeline_steps = body.pipeline_steps or list(meta.steps.keys())
    prompt = body.prompt
    if not prompt:
        for step_data in meta.steps.values():
            if isinstance(step_data, dict) and step_data.get("prompt"):
                prompt = step_data["prompt"]
                break
    message = _build_tag_suggest_message(
        TagsSuggestRequest(
            asset_id=body.asset_id,
            prompt=prompt,
            original_filename=body.original_filename,
            pipeline_steps=pipeline_steps,
            include_image_analysis=body.include_image_analysis,
        )
    )
    run_input: list[object] = [message]
    if body.include_image_analysis:
        img_path, media_type = _get_preview_image_path(body.asset_id)
        if img_path and media_type:
            img_bytes = await asyncio.to_thread(img_path.read_bytes)
            run_input.append(BinaryContent(data=img_bytes, media_type=media_type))
    agent = get_tagging_agent()
    try:
        result = await agent.run(run_input)
    except Exception as e:
        raise HTTPException(
            status_code=502,
            detail={
                "agent": "tagging",
                "error_type": "model_error",
                "message": str(e),
                "fallback_available": False,
            },
        ) from e
    output = result.output
    if output is None:
        raise HTTPException(
            status_code=502,
            detail={
                "agent": "tagging",
                "error_type": "model_error",
                "message": "Agent returned no output",
                "fallback_available": False,
            },
        )
    return output


@router.post(
    "/quality/assess",
    response_model=None,
    responses={
        503: {"description": "Agent not available", "model": AgentError},
    },
)
async def assess_quality(_body: QualityAssessRequest) -> NoReturn:
    """Qualität bewerten (Implementierung in PURZEL-039)."""
    if not settings.agent_available:
        _raise_503("quality")
    raise HTTPException(
        status_code=501,
        detail="Not implemented (PURZEL-039)",
    )


@router.post(
    "/workflow/recommend",
    response_model=None,
    responses={
        503: {"description": "Agent not available", "model": AgentError},
    },
)
async def recommend_workflow(_body: WorkflowRecommendRequest) -> NoReturn:
    """Workflow-Empfehlung (Implementierung in PURZEL-040)."""
    if not settings.agent_available:
        _raise_503("workflow")
    raise HTTPException(
        status_code=501,
        detail="Not implemented (PURZEL-040)",
    )
