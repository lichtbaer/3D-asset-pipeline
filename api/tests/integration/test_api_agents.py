"""
Integration-Tests für /agents API.
Kritisch: Agent-503-Fallback bei fehlendem API-Key.
"""

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(tmp_storage_paths) -> TestClient:
    from app.main import app
    from tests.conftest import PrefixedTestClient
    return PrefixedTestClient(app)


def test_agent_returns_503_without_api_key(client: TestClient, monkeypatch):
    """
    Agent-Fallback bei fehlendem API-Key: 503.
    """
    monkeypatch.setattr("app.core.config.settings.ANTHROPIC_API_KEY", None)

    r = client.post(
        "/agents/prompt/optimize",
        json={
            "description": "Ein Hund",
            "intended_use": "3D",
            "existing_prompt": None,
            "style": None,
        },
    )
    assert r.status_code == 503
    detail = r.json().get("detail", {})
    if isinstance(detail, dict):
        # APIError-Format: code "AGENT_NOT_AVAILABLE" oder "not_available" in message
        assert detail.get("code") == "AGENT_NOT_AVAILABLE" or "not_available" in str(
            detail.get("error", "")
        )
    else:
        assert "not_available" in str(detail)


def test_agent_tags_suggest_503_without_key(client: TestClient, monkeypatch, sample_asset: str):
    """Tags-Suggest ohne API-Key -> 503."""
    monkeypatch.setattr("app.core.config.settings.ANTHROPIC_API_KEY", None)

    r = client.post(
        "/agents/tags/suggest",
        json={
            "asset_id": sample_asset,
            "prompt": None,
            "original_filename": None,
            "pipeline_steps": ["mesh"],
            "include_image_analysis": False,
        },
    )
    assert r.status_code == 503
