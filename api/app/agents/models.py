"""Gemeinsame Pydantic-Modelle für alle Agent-Outputs."""

from pydantic import BaseModel, Field, field_validator


class AgentError(BaseModel):
    """Strukturierter Fehler bei Agent-Aufrufen."""

    agent: str
    error_type: str  # "timeout", "rate_limit", "model_error", "not_available"
    message: str
    fallback_available: bool


class TagSuggestion(BaseModel):
    """Vorgeschlagene Tags für ein Asset."""

    tags: list[str] = Field(
        description="Vorgeschlagene Tags, lowercase, max 20 Zeichen je Tag"
    )
    confidence: float = Field(ge=0.0, le=1.0)

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, v: list[str]) -> list[str]:
        seen: set[str] = set()
        out: list[str] = []
        for t in v:
            t_clean = t.strip().lower()[:20]
            if t_clean and t_clean not in seen:
                seen.add(t_clean)
                out.append(t_clean)
        return out


class PromptSuggestion(BaseModel):
    """Optimierter Prompt mit Varianten."""

    optimized_prompt: str = Field(min_length=1, description="Technisch optimierter Prompt")
    negative_prompt: str = Field(description="Was explizit vermieden werden soll")
    reasoning: str = Field(description="Kurze Begründung der Änderungen")
    variants: list[str] = Field(
        min_length=2,
        max_length=3,
        description="2-3 alternative Prompt-Varianten",
    )


class QualityIssue(BaseModel):
    """Ein erkanntes Qualitätsproblem."""

    type: str  # "floor_artifact", "missing_limb", "bad_topology", "low_detail"
    severity: str  # "low", "medium", "high"
    description: str


class RecommendedAction(BaseModel):
    """Empfohlene Aktion zur Verbesserung."""

    action: str  # "clip_floor", "repair_mesh", "simplify", "regenerate"
    reason: str
    priority: int  # 1 = höchste Priorität


class QualityAssessment(BaseModel):
    """Qualitätsbewertung eines 3D-Assets."""

    score: int = Field(ge=1, le=10)
    issues: list[QualityIssue]
    rigging_suitable: bool
    recommended_actions: list[RecommendedAction]


class WorkflowRecommendation(BaseModel):
    """Empfehlung für den nächsten Workflow-Schritt."""

    next_step: str  # "clip_floor", "repair", "simplify", "rig", "animate", "export"
    reason: str
    alternative_steps: list[str]
    warnings: list[str]
