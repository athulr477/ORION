"""Database model for background task tracking."""

from __future__ import annotations

import datetime
import enum
import uuid

from sqlalchemy import Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from orion.database import Base


class TaskStatus(enum.StrEnum):
    """Status lifecycle of a background task."""

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    CANCELLED = "CANCELLED"


class TaskJob(Base):
    """Represents a queued or running background job."""

    __tablename__ = "task_jobs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        index=True,
    )
    task_type: Mapped[str] = mapped_column(String, index=True)
    status: Mapped[TaskStatus] = mapped_column(String, index=True, default=TaskStatus.PENDING)

    # Progress and live tracking
    progress: Mapped[float] = mapped_column(Float, default=0.0, server_default="0")
    current_step: Mapped[str | None] = mapped_column(String)

    # Input/Output data
    payload: Mapped[dict] = mapped_column(JSONB, default=dict)
    result: Mapped[dict | None] = mapped_column(JSONB)
    error_message: Mapped[str | None] = mapped_column(Text)

    # Timestamps
    created_at: Mapped[datetime.datetime] = mapped_column(
        server_default=func.now(),
    )
    started_at: Mapped[datetime.datetime | None] = mapped_column()
    completed_at: Mapped[datetime.datetime | None] = mapped_column()

    # Robustness
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    max_retries: Mapped[int] = mapped_column(Integer, default=3)
