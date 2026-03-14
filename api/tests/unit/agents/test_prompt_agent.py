"""
Unit-Tests für prompt_agent.
Agent-Fallback bei fehlendem API-Key wird in Integration-Tests geprüft.
"""

import pytest


def test_get_prompt_agent_returns_agent(monkeypatch):
    """get_prompt_agent liefert Agent-Instanz wenn API-Key gesetzt."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setattr("app.core.config.settings.ANTHROPIC_API_KEY", "test-key")
    # Agent-Cache zurücksetzen
    import app.agents.prompt_agent as mod
    mod._PROMPT_AGENT = None
    from app.agents.prompt_agent import get_prompt_agent
    agent = get_prompt_agent()
    assert agent is not None
    assert hasattr(agent, "run")
