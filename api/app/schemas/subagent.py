"""Pydantic-Schemas für Subagent-Tasks."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class DelegateRepoAnalyzerPayload(BaseModel):
    """Input für repo_analyzer."""

    repo_url: str


class DelegatePrReviewerPayload(BaseModel):
    """Input für pr_reviewer."""

    ticket_id: str
    pr_url: str
    acceptance_criteria: list[str] = Field(default_factory=list)


class DelegateDebtScannerPayload(BaseModel):
    """Input für debt_scanner."""

    subproject_id: str


class DelegateDocAgentPayload(BaseModel):
    """Input für doc_agent."""

    ticket_id: str
    pr_url: str


DelegatePayload = (
    DelegateRepoAnalyzerPayload
    | DelegatePrReviewerPayload
    | DelegateDebtScannerPayload
    | DelegateDocAgentPayload
)


class DelegateToSubagentRequest(BaseModel):
    """Request für delegate_to_subagent."""

    type: str = Field(..., pattern="^(repo_analyzer|pr_reviewer|debt_scanner|doc_agent)$")
    subproject_id: str
    input_payload: dict[str, Any]


class DelegateToSubagentResponse(BaseModel):
    """Response von delegate_to_subagent."""

    task_id: str
    message: str


class SubagentTaskResponse(BaseModel):
    """Response für get_task_status."""

    id: UUID
    type: str
    status: str
    subproject_id: str
    input_payload: dict[str, Any]
    output_payload: dict[str, Any] | None
    created_at: datetime
    last_heartbeat_at: datetime | None
    integrated_at: datetime | None

    model_config = {"from_attributes": True}


class IntegrateTaskRequest(BaseModel):
    """Request für integrate-task Endpoint."""

    task_id: str


class IntegrateTaskResponse(BaseModel):
    """Response von integrate_task_result."""

    summary: str
    integrated: bool
