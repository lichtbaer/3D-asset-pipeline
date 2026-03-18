"""Zentrale Enums fuer das Datenmodell."""

from enum import StrEnum


class JobStatus(StrEnum):
    """Status-Werte fuer GenerationJob."""

    PENDING = "pending"
    PROCESSING = "processing"
    DONE = "done"
    FAILED = "failed"
