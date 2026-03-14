"""Agent-API: Prompt-Assistent, Auto-Tagging, Qualitätsbewertung, Workflow-Empfehlung."""

from typing import NoReturn

from fastapi import APIRouter, HTTPException

from app.agents.models import AgentError, PromptSuggestion
from app.agents.prompt_agent import get_prompt_agent
from app.core.config import settings
from app.schemas.agents import (
    PromptOptimizeRequest,
    QualityAssessRequest,
    TagsSuggestRequest,
    WorkflowRecommendRequest,
)

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


@router.post(
    "/tags/suggest",
    response_model=None,
    responses={
        503: {"description": "Agent not available", "model": AgentError},
    },
)
async def suggest_tags(_body: TagsSuggestRequest) -> NoReturn:
    """Tags vorschlagen (Implementierung in PURZEL-038)."""
    if not settings.agent_available:
        _raise_503("tagging")
    raise HTTPException(
        status_code=501,
        detail="Not implemented (PURZEL-038)",
    )


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
