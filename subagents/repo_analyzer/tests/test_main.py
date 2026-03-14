"""Tests für main.py (Poll-Loop, Heartbeat, complete, fail)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from unittest.mock import AsyncMock, patch


@pytest.mark.asyncio
async def test_heartbeat_sent_during_processing():
    """Heartbeat wird gesendet während Analyse läuft (gemockt)."""
    from main import heartbeat, process_task

    with patch("main.heartbeat", new_callable=AsyncMock) as mock_hb:
        with patch("main.analyze", new_callable=AsyncMock) as mock_analyze:
            from schemas import RepoAnalysisOutput

            mock_analyze.return_value = RepoAnalysisOutput(
                detected_stack=["Python"],
                architecture_patterns=[],
                findings=[],
                summary="OK",
            )
            mock_hb.return_value = True

            with patch("main.complete_task", new_callable=AsyncMock) as mock_complete:
                mock_complete.return_value = True

                await process_task(
                    {
                        "id": "test-task-123",
                        "input_payload": {"repo_url": "https://github.com/owner/repo"},
                    }
                )

            # Heartbeat mindestens einmal sofort
            assert mock_hb.call_count >= 1


@pytest.mark.asyncio
async def test_fail_task_called_on_error():
    """Bei Fehler: fail_task wird aufgerufen."""
    from main import process_task

    with (
        patch("main.heartbeat", new_callable=AsyncMock) as mock_heartbeat,
        patch("main.analyze", new_callable=AsyncMock) as mock_analyze,
        patch("main.fail_task", new_callable=AsyncMock) as mock_fail,
    ):
        mock_heartbeat.return_value = True
        mock_analyze.side_effect = RuntimeError("GitHub API Fehler")
        mock_fail.return_value = True

        await process_task(
            {
                "id": "test-task-456",
                "input_payload": {"repo_url": "https://github.com/owner/repo"},
            }
        )

        mock_fail.assert_called_once()
        call_args = mock_fail.call_args
        assert call_args[0][0] == "test-task-456"
        assert "GitHub" in call_args[0][1] or "Fehler" in call_args[0][1]
