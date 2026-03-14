"""Auto-Tagging: Analysiert Metadaten und schlägt passende Tags vor."""

from pydantic_ai import Agent

from app.agents.base import get_model
from app.agents.models import TagSuggestion

_TAGGING_AGENT: Agent[None, TagSuggestion] | None = None


def get_tagging_agent() -> Agent[None, TagSuggestion]:
    """Lazy-Initialisierung des Tagging-Agenten (erfordert ANTHROPIC_API_KEY)."""
    global _TAGGING_AGENT
    if _TAGGING_AGENT is None:
        _TAGGING_AGENT = Agent(
            model=get_model(),
            output_type=TagSuggestion,
            system_prompt="""
Du analysierst 3D-Asset-Metadaten und schlägst präzise, nützliche Tags vor.
Tags sollen lowercase, max 20 Zeichen, englisch oder deutsch sein.

Kategorien für Tags (wähle nur relevante):
- Charakter-Typ: "humanoid", "animal", "creature", "robot", "vehicle", "prop"
- Stil: "realistic", "cartoon", "low-poly", "stylized"
- Pipeline-Stand: "mesh-ready", "rig-ready", "animated", "print-ready"
- Qualität: "high-detail", "low-poly", "needs-repair"
- Projekt: extrahiere relevante Begriffe aus dem Prompt (z.B. "purzel", "dog", "armor")

Gib 3-8 Tags zurück, keine Duplikate, keine generischen Tags wie "character" oder "3d".
""",
        )
    return _TAGGING_AGENT
