"""Traceability matrix model — stores the analysis results linking requirements to tests."""

import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from orion.database import Base


class TraceabilityStatus(enum.StrEnum):
    """Risk classification status for a requirement↔test pair.

    Thresholds (from Pre-Phase 0):
        risk_score > 0.75  → Covered
        0.4 ≤ risk_score ≤ 0.75 → Partial
        risk_score < 0.4  → Drifted
    """

    COVERED = "Covered"
    PARTIAL = "Partial"
    DRIFTED = "Drifted"


class TraceabilityMatrix(Base):
    """A single requirement↔test analysis result.

    Columns:
        semantic_score: Cosine similarity between requirement and test embeddings (Phase 4).
        structural_score: Match score between requirement constraints and test assertions (Phase 5).
        risk_score: Combined score = 0.6 × semantic_score + 0.4 × structural_score (Phase 5).
        confidence: Confidence level of the classification (0.0–1.0).
        status: Covered / Partial / Drifted classification.
        requirement_delta: Structured diff when a requirement changes (Phase 6).
        audit_summary: LLM-generated explanation for Partial/Drifted cases (Phase 7).
    """

    __tablename__ = "traceability_matrix"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
    )
    requirement_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("requirements.id", ondelete="CASCADE"),
    )
    test_case_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("test_cases.id", ondelete="CASCADE"),
    )

    # Scores (Phase 4 & 5)
    semantic_score: Mapped[float | None] = mapped_column(
        Float,
        comment="Cosine similarity from Phase 4",
    )
    structural_score: Mapped[float | None] = mapped_column(
        Float,
        comment="Structural match score from Phase 5",
    )
    risk_score: Mapped[float | None] = mapped_column(
        Float,
        comment="Combined: 0.6 × semantic + 0.4 × structural",
    )
    confidence: Mapped[float | None] = mapped_column(
        Float,
        comment="Classification confidence (0.0–1.0)",
    )
    status: Mapped[TraceabilityStatus | None] = mapped_column(
        Enum(
            TraceabilityStatus,
            name="traceability_status",
            values_callable=lambda e: [m.value for m in e],
        ),
        comment="Covered / Partial / Drifted",
    )

    # Phase 6 — Requirement delta tracking
    requirement_delta: Mapped[dict | None] = mapped_column(
        JSONB,
        comment="Structured diff from Phase 6 requirement tracking",
    )

    # Phase 7 — LLM-generated audit summary
    audit_summary: Mapped[str | None] = mapped_column(
        Text,
        comment="Evidence-grounded explanation from Phase 7",
    )

    # Phase 12 — Manual Override
    is_manually_overridden: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
        comment="True if a QA Lead manually overrode the risk score",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationships
    requirement: Mapped["Requirement"] = relationship(
        "Requirement",
        back_populates="traceability_entries",
    )
    test_case: Mapped["TestCase"] = relationship(
        "TestCase",
        back_populates="traceability_entries",
    )

    __table_args__ = (
        UniqueConstraint("requirement_id", "test_case_id", name="uq_req_test"),
        Index("ix_traceability_matrix_requirement_id", "requirement_id"),
        Index("ix_traceability_matrix_test_case_id", "test_case_id"),
        Index("ix_traceability_matrix_status", "status"),
        Index("ix_traceability_matrix_workspace_id", "workspace_id"),
    )

    def __repr__(self) -> str:
        return (
            f"<TraceabilityMatrix(requirement_id={self.requirement_id!r}, "
            f"test_case_id={self.test_case_id!r}, status={self.status!r})>"
        )


# Resolve forward references
from orion.models.requirement import Requirement  # noqa: E402, F811
from orion.models.test_case import TestCase  # noqa: E402, F811
