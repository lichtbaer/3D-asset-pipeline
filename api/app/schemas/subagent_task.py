"""Pydantic-Schemas für Subagent-Tasks (repo_analyzer etc.)."""

from typing import Literal

from pydantic import BaseModel, Field


class Finding(BaseModel):
    """Ein einzelnes Finding aus der Repository-Analyse."""

    title: str
    description: str
    severity: Literal["critical", "high", "medium", "low"]
    category: Literal[
        "security", "performance", "maintainability", "testing", "documentation"
    ]
    file_path: str | None = None


class RepoAnalysisOutput(BaseModel):
    """Output-Schema der repo_analyzer Analyse."""

    detected_stack: list[str] = Field(default_factory=list)
    architecture_patterns: list[str] = Field(default_factory=list)
    findings: list[Finding] = Field(default_factory=list)
    summary: str = ""


class RepoAnalyzerInput(BaseModel):
    """Input-Payload für repo_analyzer Tasks."""

    repo_url: str
    """Vollständige GitHub-URL, z.B. https://github.com/owner/repo"""
