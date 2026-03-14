"""Agent-API: Prompt-Assistent, Auto-Tagging, Qualitätsbewertung, Workflow-Empfehlung, Chat."""

import asyncio
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic_ai import BinaryContent

from app.agents.chat_agent import ChatResponse as ChatResponseModel
from app.agents.chat_agent import get_chat_agent
from app.agents.models import (
    AgentError,
    PromptSuggestion,
    QualityAssessment,
    TagSuggestion,
    WorkflowRecommendation,
)
from app.agents.prompt_agent import get_prompt_agent
from app.agents.quality_agent import get_quality_agent
from app.agents.tagging_agent import get_tagging_agent
from app.agents.workflow_agent import get_workflow_agent
from app.core.config import settings
from app.core.errors import APIError, raise_api_error
from app.core.rate_limit import limiter
from app.schemas.agents import (
    ChatRequest,
    PromptOptimizeRequest,
    QualityAssessRequest,
    TagsSuggestRequest,
    WorkflowRecommendRequest,
)
from app.services import asset_service
from app.services.mesh_processing_service import analyze as mesh_analyze

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
    """Wirft 503 mit strukturiertem APIError."""
    err = _agent_not_available_error(agent)
    raise HTTPException(
        status_code=503,
        detail=APIError(
            error=err.message,
            detail=err.message,
            code="AGENT_NOT_AVAILABLE",
        ).model_dump(),
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
@limiter.limit("20/minute")
async def optimize_prompt(
    request: Request, body: PromptOptimizeRequest
) -> PromptSuggestion:
    """Prompt optimieren oder aus Beschreibung generieren (PURZEL-037)."""
    if not settings.agent_available:
        _raise_503("prompt")
    agent = get_prompt_agent()
    try:
        result = await agent.run(_build_prompt_message(body))
    except Exception as e:
        raise_api_error(
            502,
            "Modell-Fehler",
            detail=str(e),
            code="MODEL_ERROR",
            chain=e,
        )
    output = result.output
    if output is None:
        raise_api_error(502, "Agent returned no output", code="MODEL_ERROR")
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
@limiter.limit("20/minute")
async def suggest_tags(
    request: Request, body: TagsSuggestRequest
) -> TagSuggestion:
    """Tags vorschlagen basierend auf Prompt, Dateiname, Pipeline-Stand und optional Bild."""
    if not settings.agent_available:
        _raise_503("tagging")
    meta = asset_service.get_asset(body.asset_id)
    if not meta:
        raise_api_error(404, "Asset nicht gefunden", code="ASSET_NOT_FOUND")
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
    run_input: list[str | BinaryContent] = [message]
    if body.include_image_analysis:
        img_path, media_type = _get_preview_image_path(body.asset_id)
        if img_path and media_type:
            img_bytes = await asyncio.to_thread(img_path.read_bytes)
            run_input.append(BinaryContent(data=img_bytes, media_type=media_type))
    agent = get_tagging_agent()
    try:
        result = await agent.run(run_input)
    except Exception as e:
        raise_api_error(502, "Modell-Fehler", detail=str(e), code="MODEL_ERROR", chain=e)
    output = result.output
    if output is None:
        raise_api_error(502, "Agent returned no output", code="MODEL_ERROR")
    return output


def _get_mesh_source_file(asset_id: str) -> str:
    """Primäre Mesh-Datei für Analyse (mesh.glb oder aus steps)."""
    meta = asset_service.get_asset(asset_id)
    if not meta or "mesh" not in meta.steps:
        return "mesh.glb"
    mesh_step = meta.steps.get("mesh", {})
    if isinstance(mesh_step, dict) and mesh_step.get("file"):
        return str(mesh_step["file"])
    return "mesh.glb"


async def _run_quality_assessment_internal(
    asset_id: str,
    *,
    include_mesh_analysis: bool = True,
    include_vision: bool = True,
) -> QualityAssessment | None:
    """Interne Quality-Assessment-Logik (für Route und Workflow)."""
    mesh_analysis_dict: dict[str, Any] | None = None
    if include_mesh_analysis:
        try:
            source_file = _get_mesh_source_file(asset_id)
            analysis = await asyncio.to_thread(mesh_analyze, asset_id, source_file)
            mesh_analysis_dict = analysis.model_dump()
        except FileNotFoundError:
            pass

    message = _build_quality_prompt(asset_id, mesh_analysis_dict)
    run_input: list[str | BinaryContent] = [message]

    if include_vision:
        img_path, media_type = _get_preview_image_path(asset_id)
        if img_path and media_type:
            img_bytes = await asyncio.to_thread(img_path.read_bytes)
            run_input.append(BinaryContent(data=img_bytes, media_type=media_type))

    agent = get_quality_agent()
    result = await agent.run(run_input)
    output = result.output
    if output is None:
        return None

    has_high = any(i.severity == "high" for i in output.issues)
    if has_high and output.rigging_suitable:
        output = output.model_copy(update={"rigging_suitable": False})
    return output


def _build_quality_prompt(
    asset_id: str,
    mesh_analysis: dict[str, Any] | None,
) -> str:
    """Baut die User-Nachricht für den Quality-Agenten."""
    parts = [f"Asset-ID: {asset_id}"]
    if mesh_analysis:
        parts.append("\nMesh-Kennzahlen:")
        parts.append(f"- Vertices: {mesh_analysis.get('vertex_count', '?')}")
        parts.append(f"- Faces: {mesh_analysis.get('face_count', '?')}")
        parts.append(f"- Watertight: {mesh_analysis.get('is_watertight', '?')}")
        parts.append(f"- Manifold: {mesh_analysis.get('is_manifold', '?')}")
        parts.append(f"- Duplikate: {mesh_analysis.get('has_duplicate_vertices', '?')}")
        parts.append(f"- Dateigröße: {mesh_analysis.get('file_size_bytes', 0) / 1024:.1f} KB")
    parts.append("\nBewerte die Qualität des 3D-Meshes.")
    return "\n".join(parts)


@router.post(
    "/quality/assess",
    response_model=QualityAssessment,
    responses={
        503: {"description": "Agent not available", "model": AgentError},
    },
)
@limiter.limit("10/minute")
async def assess_quality(
    request: Request, body: QualityAssessRequest
) -> QualityAssessment:
    """Qualität bewerten (PURZEL-039)."""
    if not settings.agent_available:
        _raise_503("quality")
    meta = asset_service.get_asset(body.asset_id)
    if not meta:
        raise_api_error(404, "Asset nicht gefunden", code="ASSET_NOT_FOUND")
    if "mesh" not in meta.steps:
        raise_api_error(
            400,
            "Asset hat keinen Mesh-Step (nur Assets mit mesh können bewertet werden)",
            code="INVALID_ASSET",
        )

    try:
        output = await _run_quality_assessment_internal(
            body.asset_id,
            include_mesh_analysis=body.include_mesh_analysis,
            include_vision=body.include_vision,
        )
    except Exception as e:
        raise_api_error(502, "Modell-Fehler", detail=str(e), code="MODEL_ERROR", chain=e)

    if output is None:
        raise_api_error(502, "Agent returned no output", code="MODEL_ERROR")

    return output


def _build_workflow_prompt(
    asset_id: str,
    mesh_analysis: dict[str, Any] | None,
    pipeline_steps: list[str],
    quality_assessment: QualityAssessment | None,
    intention: str | None,
) -> str:
    """Baut die User-Nachricht für den Workflow-Agenten."""
    parts = [f"Asset-ID: {asset_id}"]
    parts.append(f"Vorhandene Pipeline-Steps: {', '.join(pipeline_steps) or 'keine'}")
    if intention:
        parts.append(f"Nutzer-Intention: {intention}")
    if mesh_analysis:
        parts.append("\nMesh-Kennzahlen:")
        parts.append(f"- Vertices: {mesh_analysis.get('vertex_count', '?')}")
        parts.append(f"- Faces: {mesh_analysis.get('face_count', '?')}")
        parts.append(f"- Watertight: {mesh_analysis.get('is_watertight', '?')}")
    if quality_assessment:
        parts.append("\nQualitätsbewertung:")
        parts.append(f"- Score: {quality_assessment.score}/10")
        parts.append(f"- Rigging geeignet: {quality_assessment.rigging_suitable}")
        for i in quality_assessment.issues:
            parts.append(f"  - {i.type} ({i.severity}): {i.description}")
        if quality_assessment.recommended_actions:
            parts.append("Empfohlene Aktionen:")
            for a in quality_assessment.recommended_actions:
                parts.append(f"  - {a.action}: {a.reason}")
    parts.append("\nEmpfehle den optimalen nächsten Workflow-Schritt.")
    return "\n".join(parts)


@router.post(
    "/workflow/recommend",
    response_model=WorkflowRecommendation,
    responses={
        503: {"description": "Agent not available", "model": AgentError},
    },
)
@limiter.limit("10/minute")
async def recommend_workflow(
    request: Request, body: WorkflowRecommendRequest
) -> WorkflowRecommendation:
    """Workflow-Empfehlung (PURZEL-040)."""
    if not settings.agent_available:
        _raise_503("workflow")
    meta = asset_service.get_asset(body.asset_id)
    if not meta:
        raise_api_error(404, "Asset nicht gefunden", code="ASSET_NOT_FOUND")

    pipeline_steps = list(meta.steps.keys())
    quality = body.quality_assessment

    # Mesh-Analyse und ggf. Quality-Assessment laden
    mesh_analysis_dict = None
    if "mesh" in meta.steps:
        try:
            source_file = _get_mesh_source_file(body.asset_id)
            analysis = await asyncio.to_thread(
                mesh_analyze, body.asset_id, source_file
            )
            mesh_analysis_dict = analysis.model_dump()
        except FileNotFoundError:
            pass

    # Quality-Assessment laden falls nicht übergeben (für Workflow-Kontext)
    if quality is None and "mesh" in meta.steps:
        quality = await _run_quality_assessment_internal(
            body.asset_id,
            include_mesh_analysis=True,
            include_vision=False,
        )

    message = _build_workflow_prompt(
        body.asset_id,
        mesh_analysis_dict,
        pipeline_steps,
        quality,
        body.intention,
    )

    agent = get_workflow_agent()
    try:
        result = await agent.run(message)
    except Exception as e:
        raise_api_error(502, "Modell-Fehler", detail=str(e), code="MODEL_ERROR", chain=e)

    output = result.output
    if output is None:
        raise_api_error(502, "Agent returned no output", code="MODEL_ERROR")

    return output


def _build_chat_context(body: ChatRequest) -> dict[str, Any]:
    """Baut den Kontext für den Chat-Agenten (History + Asset)."""
    ctx: dict[str, Any] = {
        "message": body.message,
        "history": [
            {"role": m.role, "content": m.content, "timestamp": m.timestamp}
            for m in body.history[-body.max_history :]
        ],
    }
    if body.asset_id:
        meta = asset_service.get_asset(body.asset_id)
        if meta:
            steps_summary = ", ".join(
                f"{s} ✓" if meta.steps.get(s, {}).get("file") else f"{s} —"
                for s in ("image", "bgremoval", "mesh", "rigging", "animation")
            )
            ctx["asset_context"] = {
                "asset_id": body.asset_id,
                "name": meta.name or f"Asset {body.asset_id[:8]}…",
                "steps": steps_summary,
                "steps_detail": dict(meta.steps),
            }
        else:
            ctx["asset_context"] = {"asset_id": body.asset_id, "name": None}
    return ctx


def _build_chat_user_message(ctx: dict[str, Any]) -> str:
    """Formatiert die User-Nachricht mit Kontext für den Agenten."""
    parts: list[str] = []
    if ctx.get("asset_context"):
        ac = ctx["asset_context"]
        parts.append(f"[Asset-Kontext: {ac.get('name', ac['asset_id'])}]")
        if ac.get("steps"):
            parts.append(f"Pipeline-Stand: {ac['steps']}")
        parts.append("")
    parts.append(ctx["message"])
    if ctx.get("history"):
        parts.append("")
        parts.append("[Konversations-Historie zur Einordnung:]")
        for h in ctx["history"]:
            role = "User" if h["role"] == "user" else "Assistant"
            parts.append(f"{role}: {h['content']}")
    return "\n".join(parts)


@router.post(
    "/chat",
    response_model=ChatResponseModel,
    responses={
        503: {"description": "Agent not available", "model": AgentError},
    },
)
@limiter.limit("20/minute")
async def chat(request: Request, body: ChatRequest) -> ChatResponseModel:
    """Freies Chat mit KI-Assistent (Asset-Kontext optional)."""
    if not settings.agent_available:
        _raise_503("chat")
    ctx = _build_chat_context(body)
    user_message = _build_chat_user_message(ctx)
    agent = get_chat_agent()
    try:
        result = await agent.run(user_message)
    except Exception as e:
        raise_api_error(502, "Modell-Fehler", detail=str(e), code="MODEL_ERROR", chain=e)
    output = result.output
    if output is None:
        raise_api_error(502, "Agent returned no output", code="MODEL_ERROR")
    return output
