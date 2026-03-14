"""Request-Schemas für Agent-Endpunkte (Details in PURZEL-037 bis 040)."""

from typing import Any

from pydantic import BaseModel, Field


class PromptOptimizeRequest(BaseModel):
    """Request für Prompt-Optimierung (PURZEL-037)."""

    prompt: str = Field(..., min_length=1, description="Zu optimierender Prompt")


class TagsSuggestRequest(BaseModel):
    """Request für Tag-Vorschläge (PURZEL-038)."""

    text: str = Field(..., description="Beschreibung oder Kontext für Tagging")


class QualityAssessRequest(BaseModel):
    """Request für Qualitätsbewertung (PURZEL-039)."""

    mesh_url: str | None = Field(default=None, description="URL zum Mesh oder Asset")
    context: str | None = Field(default=None, description="Zusätzlicher Kontext")


class WorkflowRecommendRequest(BaseModel):
    """Request für Workflow-Empfehlung (PURZEL-040)."""

    current_step: str = Field(..., description="Aktueller Workflow-Schritt")
    context: dict[str, Any] | None = Field(default=None, description="Pipeline-Kontext")
