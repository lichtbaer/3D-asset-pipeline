"""Prompt-Assistent: Einfache Beschreibungen in optimierte 3D-Asset-Prompts umwandeln."""

from pydantic_ai import Agent

from app.agents.base import get_model
from app.agents.models import PromptSuggestion

_PROMPT_AGENT: Agent[None, PromptSuggestion] | None = None


def get_prompt_agent() -> Agent[None, PromptSuggestion]:
    """Lazy-Initialisierung des Prompt-Agenten (erfordert ANTHROPIC_API_KEY)."""
    global _PROMPT_AGENT
    if _PROMPT_AGENT is None:
        _PROMPT_AGENT = Agent(
            model=get_model(),
            output_type=PromptSuggestion,
            system_prompt="""
Du bist ein Experte für AI-Bildgenerierung von 3D-Asset-Charakteren.
Deine Aufgabe: einfache Charakter-Beschreibungen in optimierte Prompts für
Image-to-3D-Pipelines umwandeln.

Technische Anforderungen für 3D-geeignete Bilder:
- T-Pose oder leichte A-Pose (Arme vom Körper weg, sichtbar)
- Neutraler einfarbiger Hintergrund (weiß oder hellgrau bevorzugt)
- Gleichmäßige, diffuse Beleuchtung ohne harte Schatten
- Volle Figur sichtbar (Kopf bis Fuß)
- Keine Überschneidungen von Gliedmaßen mit Körper
- Frontalansicht oder leichte 3/4-Ansicht
- Klare Silhouette

Gib immer zurück:
- optimized_prompt: technisch optimierter Prompt
- negative_prompt: was explizit vermieden werden soll
- reasoning: kurze Erklärung der wichtigsten Änderungen
- variants: 2-3 alternative Prompt-Varianten (andere Stile, Posen)
""",
        )
    return _PROMPT_AGENT
