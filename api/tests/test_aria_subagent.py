"""Tests für ARIA Subagent-Tools und Kontext-Injection."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.aria.context import build_subagent_context
from app.aria.prompts import ARIA_SYSTEM_PROMPT
from app.aria.tools import delegate_to_subagent, get_task_status, integrate_task_result
from app.models import SubagentTask


class TestDelegateToSubagent:
    @pytest.mark.asyncio
    async def test_delegate_creates_task_in_db(self):
        """delegate_to_subagent erstellt korrekten Task in DB."""
        created_task = SubagentTask(
            id=uuid4(),
            type="repo_analyzer",
            status="pending",
            subproject_id="proj-1",
            company_id="default",
            input_payload={"repo_url": "https://github.com/foo/bar"},
            created_at=datetime.now(timezone.utc),
        )

        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session.add = MagicMock()
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock(side_effect=lambda t: setattr(t, "id", created_task.id))

        with patch("app.aria.tools.async_session_factory") as mock_factory:
            mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_factory.return_value.__aexit__ = AsyncMock(return_value=None)

            with patch("app.services.subagent_service.create_task", new_callable=AsyncMock) as mock_create:
                mock_create.return_value = created_task
                result = await delegate_to_subagent(
                    type="repo_analyzer",
                    subproject_id="proj-1",
                    input_payload={"repo_url": "https://github.com/foo/bar"},
                )

        assert "task_id" in result
        assert result["task_id"] == str(created_task.id)
        assert "repo_analyzer" in result["message"]
        assert "läuft im Hintergrund" in result["message"]


class TestIntegrateTaskResult:
    @pytest.mark.asyncio
    async def test_integrate_writes_correct_entries_by_type(self):
        """integrate_task_result schreibt korrekte Einträge je nach Typ."""
        task_id = uuid4()
        task = SubagentTask(
            id=task_id,
            type="debt_scanner",
            status="completed",
            subproject_id="proj-1",
            company_id="default",
            input_payload={"subproject_id": "proj-1"},
            output_payload={"debt_entries": []},
            created_at=datetime.now(timezone.utc),
        )

        mock_session = AsyncMock()
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()

        with patch("app.aria.tools.get_task", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = task
            with patch("app.aria.tools.mark_integrated", new_callable=AsyncMock) as mock_mark:
                mock_mark.return_value = task
                result = await integrate_task_result(str(task_id), session=mock_session)

        assert result["integrated"] is True
        assert "Debt" in result["summary"] or "debt" in result["summary"].lower()


class TestContextInjection:
    @pytest.mark.asyncio
    async def test_tasks_appear_in_aria_context_string(self):
        """Kontext-Injection: Tasks erscheinen im ARIA-Context-String."""
        task = SubagentTask(
            id=uuid4(),
            type="repo_analyzer",
            status="running",
            subproject_id="proj-1",
            company_id="default",
            input_payload={"repo_url": "https://github.com/foo/bar"},
            created_at=datetime.now(timezone.utc),
            last_heartbeat_at=datetime.now(timezone.utc),
        )

        with patch("app.aria.context.get_active_tasks_summary", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = [task]
            with patch("app.aria.context.async_session_factory") as mock_factory:
                mock_sess = AsyncMock()
                mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_sess)
                mock_factory.return_value.__aexit__ = AsyncMock(return_value=None)
                ctx = await build_subagent_context("default")

        assert "[Aktive Subagenten-Tasks]" in ctx
        assert "repo_analyzer" in ctx
        assert "running" in ctx
        assert "🔄" in ctx

    @pytest.mark.asyncio
    async def test_empty_context_when_no_tasks(self):
        """Leerer Kontext wenn keine Tasks."""
        with patch("app.aria.context.get_active_tasks_summary", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = []
            with patch("app.aria.context.async_session_factory") as mock_factory:
                mock_sess = AsyncMock()
                mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_sess)
                mock_factory.return_value.__aexit__ = AsyncMock(return_value=None)
                ctx = await build_subagent_context("default")

        assert ctx == ""


class TestSystemPrompt:
    def test_system_prompt_contains_delegation_instruction(self):
        """System-Prompt enthält Delegation-Anweisung (niemals direkt analyze_repository)."""
        assert "delegate_to_subagent" in ARIA_SYSTEM_PROMPT
        assert "analyze_repository" in ARIA_SYSTEM_PROMPT
        assert "niemals" in ARIA_SYSTEM_PROMPT or "Niemals" in ARIA_SYSTEM_PROMPT
        assert "integrate_task_result" in ARIA_SYSTEM_PROMPT
