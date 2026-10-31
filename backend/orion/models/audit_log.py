"""Audit log model for tracking manual risk score overrides."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from orion.database import Base


class AuditLog(Base):
    """Cryptographically verifiable (in a real-world scenario) audit trail for overrides."""

    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
    )
    traceability_matrix_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("traceability_matrix.id", ondelete="CASCADE"),
    )
    previous_status: Mapped[str | None] = mapped_column(
        String,
        comment="The status before override (e.g., Drifted)",
    )
    new_status: Mapped[str] = mapped_column(
        String,
        comment="The new status after override (e.g., Covered)",
    )
    rationale: Mapped[str] = mapped_column(
        Text,
        comment="Mandatory reason provided by QA Lead",
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    # Relationships
    user: Mapped["User"] = relationship("User")
    matrix_entry: Mapped["TraceabilityMatrix"] = relationship("TraceabilityMatrix")

    __table_args__ = (
        Index("ix_audit_logs_traceability_matrix_id", "traceability_matrix_id"),
        Index("ix_audit_logs_user_id", "user_id"),
        Index("ix_audit_logs_workspace_id", "workspace_id"),
    )

    def __repr__(self) -> str:
        return f"<AuditLog(user_id={self.user_id!r}, matrix_id={self.traceability_matrix_id!r})>"


# Resolve forward references
from orion.models.traceability_matrix import TraceabilityMatrix  # noqa: E402, F811
from orion.models.user import User  # noqa: E402, F811
