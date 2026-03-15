"""
Unit-Tests für agents Router.
Agent-Endpunkte mit gemocktem Pydantic-AI-Agent (kein Netzwerk).
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.agents.chat_agent import ChatResponse as ChatResponseModel
from app.agents.models import (
    PromptSuggestion,
    QualityAssessment,
    QualityIssue,
    RecommendedAction,
    TagSuggestion,
    WorkflowRecommendation,
)


@pytest.fixture
def client(tmp_storage_paths) -> TestClient:
    from app.main import app
    from tests.conftest import PrefixedTestClient
    return PrefixedTestClient(app)


@pytest.fixture
def mock_prompt_agent():
    """Mock für Prompt-Agent mit erfolgreichem Output."""
    mock = MagicMock()
    mock.run = AsyncMock(
        return_value=MagicMock(
            output=PromptSuggestion(
                optimized_prompt="test prompt",
                negative_prompt="bad things",
                reasoning="because",
                variants=["variant 1", "variant 2"],
            )
        )
    )
    return mock


@pytest.fixture
def mock_tagging_agent():
    """Mock für Tagging-Agent mit erfolgreichem Output."""
    mock = MagicMock()
    mock.run = AsyncMock(
        return_value=MagicMock(
            output=TagSuggestion(tags=["purzel", "dog", "armor"], confidence=0.9)
        )
    )
    return mock


def test_prompt_optimize_success(client: TestClient, mock_prompt_agent, monkeypatch):
    """POST /agents/prompt/optimize mit gemocktem Agent -> 200."""
    monkeypatch.setattr("app.core.config.settings.ANTHROPIC_API_KEY", "test-key")
    with patch("app.routers.agents.get_prompt_agent", return_value=mock_prompt_agent):
        resp = client.post(
            "/agents/prompt/optimize",
            json={
                "description": "armored dog",
                "intended_use": "rigging",
                "existing_prompt": None,
                "style": None,
            },
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["optimized_prompt"] == "test prompt"
    assert data["negative_prompt"] == "bad things"


def test_tags_suggest_success(
    client: TestClient, mock_tagging_agent, sample_asset: str, monkeypatch
):
    """POST /agents/tags/suggest mit gemocktem Agent -> 200."""
    monkeypatch.setattr("app.core.config.settings.ANTHROPIC_API_KEY", "test-key")
    with patch("app.routers.agents.get_tagging_agent", return_value=mock_tagging_agent):
        resp = client.post(
            "/agents/tags/suggest",
            json={
                "asset_id": sample_asset,
                "prompt": "armored dog",
                "original_filename": None,
                "pipeline_steps": ["mesh"],
                "include_image_analysis": False,
            },
        )
    assert resp.status_code == 200
    data = resp.json()
    assert "purzel" in data["tags"]
    assert "dog" in data["tags"]


def test_agents_unavailable_without_api_key(client: TestClient, monkeypatch):
    """Agent ohne API-Key -> 503."""
    monkeypatch.setattr("app.core.config.settings.ANTHROPIC_API_KEY", "")
    resp = client.post(
        "/agents/prompt/optimize",
        json={
            "description": "test",
            "intended_use": "rigging",
            "existing_prompt": None,
            "style": None,
        },
    )
    assert resp.status_code == 503
    detail = resp.json().get("detail", {})
    if isinstance(detail, dict):
        assert detail.get("code") == "AGENT_NOT_AVAILABLE"
    else:
        assert "not_available" in str(detail).lower()


def test_tags_suggest_404_asset_not_found(client: TestClient, monkeypatch):
    """Tags-Suggest mit unbekanntem Asset -> 404."""
    monkeypatch.setattr("app.core.config.settings.ANTHROPIC_API_KEY", "test-key")
    resp = client.post(
        "/agents/tags/suggest",
        json={
            "asset_id": "00000000-0000-0000-0000-000000000000",
            "prompt": "dog",
            "original_filename": None,
            "pipeline_steps": [],
            "include_image_analysis": False,
        },
    )
    assert resp.status_code == 404


@pytest.fixture
def mock_quality_agent():
    """Mock für Quality-Agent."""
    mock = MagicMock()
    mock.run = AsyncMock(
        return_value=MagicMock(
            output=QualityAssessment(
                score=8,
                issues=[
                    QualityIssue(
                        type="floor_artifact",
                        severity="low",
                        description="Minor floor artifact",
                    )
                ],
                rigging_suitable=True,
                recommended_actions=[
                    RecommendedAction(
                        action="clip_floor",
                        reason="Remove floor",
                        priority=1,
                    )
                ],
            )
        )
    )
    return mock


def test_quality_assess_success(
    client: TestClient, mock_quality_agent, sample_asset: str, monkeypatch
):
    """POST /agents/quality/assess mit gemocktem Agent -> 200."""
    monkeypatch.setattr("app.core.config.settings.ANTHROPIC_API_KEY", "test-key")
    with patch("app.routers.agents.get_quality_agent", return_value=mock_quality_agent):
        with patch(
            "app.routers.agents.mesh_analyze",
            return_value=MagicMock(
                model_dump=lambda: {
                    "vertex_count": 1000,
                    "face_count": 2000,
                    "is_watertight": True,
                    "is_manifold": True,
                    "has_duplicate_vertices": False,
                    "file_size_bytes": 1024,
                }
            ),
        ):
            resp = client.post(
                "/agents/quality/assess",
                json={
                    "asset_id": sample_asset,
                    "include_mesh_analysis": True,
                    "include_vision": False,
                },
            )
    assert resp.status_code == 200
    data = resp.json()
    assert data["score"] == 8
    assert data["rigging_suitable"] is True


@pytest.fixture
def mock_workflow_agent():
    """Mock für Workflow-Agent."""
    mock = MagicMock()
    mock.run = AsyncMock(
        return_value=MagicMock(
            output=WorkflowRecommendation(
                next_step="clip_floor",
                reason="Remove floor artifacts",
                alternative_steps=["repair_mesh"],
                warnings=[],
            )
        )
    )
    return mock


def test_workflow_recommend_success(
    client: TestClient, mock_workflow_agent, sample_asset: str, monkeypatch
):
    """POST /agents/workflow/recommend mit gemocktem Agent -> 200."""
    monkeypatch.setattr("app.core.config.settings.ANTHROPIC_API_KEY", "test-key")
    with patch("app.routers.agents.get_workflow_agent", return_value=mock_workflow_agent):
        with patch(
            "app.routers.agents.mesh_analyze",
            return_value=MagicMock(
                model_dump=lambda: {
                    "vertex_count": 1000,
                    "face_count": 2000,
                    "is_watertight": True,
                }
            ),
        ):
            with patch(
                "app.routers.agents._run_quality_assessment_internal",
                new_callable=AsyncMock,
                return_value=QualityAssessment(
                    score=8,
                    issues=[],
                    rigging_suitable=True,
                    recommended_actions=[],
                ),
            ):
                resp = client.post(
                    "/agents/workflow/recommend",
                    json={
                        "asset_id": sample_asset,
                        "intention": None,
                        "quality_assessment": None,
                    },
                )
    assert resp.status_code == 200
    data = resp.json()
    assert data["next_step"] == "clip_floor"


@pytest.fixture
def mock_chat_agent():
    """Mock für Chat-Agent."""
    mock = MagicMock()
    mock.run = AsyncMock(
        return_value=MagicMock(
            output=ChatResponseModel(
                message="Test-Antwort",
                suggestions=["Weitere Frage 1", "Weitere Frage 2"],
                prompt_suggestion=None,
                action=None,
            )
        )
    )
    return mock


def test_chat_success(client: TestClient, mock_chat_agent, monkeypatch):
    """POST /agents/chat mit gemocktem Agent -> 200."""
    monkeypatch.setattr("app.core.config.settings.ANTHROPIC_API_KEY", "test-key")
    with patch("app.routers.agents.get_chat_agent", return_value=mock_chat_agent):
        resp = client.post(
            "/agents/chat",
            json={
                "message": "Hallo",
                "history": [],
                "asset_id": None,
                "max_history": 10,
            },
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["message"] == "Test-Antwort"
    assert len(data["suggestions"]) == 2
