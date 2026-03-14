"""Tests für die Analyse-Logik (gemockt)."""

import sys
from pathlib import Path

# Repo-analyzer Root für Imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from schemas import Finding, RepoAnalysisOutput


@pytest.fixture
def mock_github_files():
    """Mock-Dateibaum eines typischen Python/React-Projekts."""
    return [
        {"path": "requirements.txt", "type": "blob"},
        {"path": "package.json", "type": "blob"},
        {"path": "api/app/main.py", "type": "blob"},
        {"path": "frontend/src/App.tsx", "type": "blob"},
        {"path": "api/tests/test_main.py", "type": "blob"},
        {"path": "Dockerfile", "type": "blob"},
        {"path": "docker-compose.yml", "type": "blob"},
    ]


@pytest.fixture
def mock_llm_response():
    """Mock-LLM-Antwort für Chunk 1."""
    return {
        "detected_stack": ["Python 3.12", "FastAPI", "React", "PostgreSQL"],
        "architecture_patterns": ["Repository Pattern", "Dependency Injection"],
    }


@pytest.mark.asyncio
async def test_repo_analysis_output_schema():
    """Output-Schema validiert gegen Pydantic-Modell."""
    output = RepoAnalysisOutput(
        detected_stack=["Python 3.12", "FastAPI"],
        architecture_patterns=["Repository Pattern"],
        findings=[
            Finding(
                title="Fehlende Tests",
                description="Keine Tests für Router",
                severity="medium",
                category="testing",
                file_path="api/app/routers/main.py",
            )
        ],
        summary="Typisches FastAPI-Projekt.",
    )
    assert output.detected_stack == ["Python 3.12", "FastAPI"]
    assert len(output.findings) == 1
    assert output.findings[0].severity == "medium"
    assert output.findings[0].category == "testing"

    # Serialisierung/Deserialisierung
    dumped = output.model_dump()
    loaded = RepoAnalysisOutput.model_validate(dumped)
    assert loaded.detected_stack == output.detected_stack


@pytest.mark.asyncio
async def test_finding_severity_values():
    """Findings nach Severity kategorisiert."""
    for severity in ["critical", "high", "medium", "low"]:
        f = Finding(
            title="Test",
            description="Desc",
            severity=severity,
            category="maintainability",
            file_path=None,
        )
        assert f.severity == severity


@pytest.mark.asyncio
async def test_finding_category_values():
    """Findings nach Category kategorisiert."""
    for category in ["security", "performance", "maintainability", "testing", "documentation"]:
        f = Finding(
            title="Test",
            description="Desc",
            severity="low",
            category=category,
            file_path=None,
        )
        assert f.category == category


@pytest.mark.asyncio
async def test_analyze_produces_valid_output(mock_github_files, mock_llm_response):
    """Mock-Repository analysieren → strukturierter Output."""
    from analyzer import analyze

    with (
        patch("analyzer.GitHubClient") as MockGH,
        patch("analyzer.LLMClient") as MockLLM,
    ):
        mock_gh_instance = MagicMock()
        mock_gh_instance.get_file_tree = AsyncMock(return_value=mock_github_files)
        mock_gh_instance.get_file_content = AsyncMock(return_value="# Mock content")
        mock_gh_instance.select_code_samples = MagicMock(
            return_value=mock_github_files[:5]
        )
        MockGH.return_value = mock_gh_instance

        mock_llm_instance = MagicMock()
        mock_llm_instance.analyze_chunk = AsyncMock(
            side_effect=[
                mock_llm_response,
                {"architecture_patterns": []},
                {"findings": [], "summary": "Mock summary"},
            ]
        )
        MockLLM.return_value = mock_llm_instance

        result = await analyze({"repo_url": "https://github.com/owner/repo"})

    assert isinstance(result, RepoAnalysisOutput)
    assert "Python" in str(result.detected_stack) or "FastAPI" in str(result.detected_stack)
    assert result.summary == "Mock summary"


@pytest.mark.asyncio
async def test_analyze_github_error_raises():
    """Bei GitHub API Fehler: Exception wird geworfen (process_task ruft fail_task)."""
    from analyzer import analyze

    with patch("analyzer.GitHubClient") as MockGH:
        mock_gh_instance = MagicMock()
        mock_gh_instance.get_file_tree = AsyncMock(
            side_effect=Exception("GitHub API rate limit")
        )
        MockGH.return_value = mock_gh_instance

        with pytest.raises(Exception) as exc_info:
            await analyze({"repo_url": "https://github.com/owner/repo"})
        assert "GitHub" in str(exc_info.value) or "rate" in str(exc_info.value).lower()
