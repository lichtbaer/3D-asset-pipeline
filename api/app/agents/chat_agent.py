"""Chat-Agent: Freies Gespräch mit Kontext zu Assets und Pipeline."""

from pydantic import BaseModel, Field
from pydantic_ai import Agent
from typing import Literal

from app.agents.base import get_model


class ChatMessage(BaseModel):
    """Eine Nachricht in der Chat-Historie."""

    role: Literal["user", "assistant"]
    content: str
    timestamp: str


class ChatAction(BaseModel):
    """Optionale direkte Aktion vom Agent."""

    type: Literal[
        "optimize_prompt",
        "suggest_tags",
        "assess_quality",
        "open_tab",
    ]
    params: dict


class ChatResponse(BaseModel):
    """Strukturierte Antwort des Chat-Agenten."""

    message: str = Field(description="Die Hauptantwort des Agenten")
    suggestions: list[str] = Field(
        default_factory=list,
        description="2-3 klickbare Folge-Fragen",
        min_length=0,
        max_length=5,
    )
    prompt_suggestion: str | None = Field(
        default=None,
        description="Vorgeschlagener Prompt falls der Agent einen empfiehlt",
    )
    action: ChatAction | None = Field(
        default=None,
        description="Optionale direkte Aktion",
    )


_CHAT_AGENT: Agent[dict, ChatResponse] | None = None


def get_chat_agent() -> Agent[dict, ChatResponse]:
    """Lazy-Initialisierung des Chat-Agenten (erfordert ANTHROPIC_API_KEY)."""
    global _CHAT_AGENT
    if _CHAT_AGENT is None:
        _CHAT_AGENT = Agent(
            model=get_model(),
            output_type=ChatResponse,
            system_prompt="""
Du bist ein kreativer und technischer Assistent für eine 3D-Asset-Pipeline.
Du hilfst bei:
- Bildideen und Prompt-Entwicklung für AI-Bildgenerierung
- Bewertung und Verbesserung von Prompts
- Entscheidungen im Pipeline-Workflow (welcher Provider, welche Parameter)
- Kreative Vorschläge für Charakter-Designs
- Technische Fragen zur Pipeline

Du kennst den Kontext des aktuellen Assets wenn er mitgegeben wird.
Antworte präzise, kreativ und direkt umsetzbar.

Gib immer 2-3 kurze suggestions als Folge-Fragen (z.B. "Zeig mir einen optimierten Prompt").
Wenn du einen konkreten Prompt vorschlägst, setze prompt_suggestion.
""",
        )
    return _CHAT_AGENT
