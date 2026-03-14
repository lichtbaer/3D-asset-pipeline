"""
Unit-Tests für tagging_agent.
"""

import pytest


def test_get_tagging_agent_returns_agent(monkeypatch):
    """get_tagging_agent liefert Agent-Instanz wenn API-Key gesetzt."""
    monkeypatch.setattr("app.core.config.settings.ANTHROPIC_API_KEY", "test-key")
    import app.agents.tagging_agent as mod
    mod._TAGGING_AGENT = None
    from app.agents.tagging_agent import get_tagging_agent
    agent = get_tagging_agent()
    assert agent is not None
    assert hasattr(agent, "run")
