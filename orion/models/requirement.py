"""Requirement model — stores requirements ingested from Jira or other sources."""

import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, Index, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from orion.database import Base


class Requirement(Base):
    """A requirement ingested from an external source (e.g. Jira).

    Fields:
        external_id: The source-system identifier (e.g. "REQ-123" from Jira).
        title: Short requirement title.
        description: Full requirement text — the primary content for semantic
            embedding and constraint extraction.
        source: Origin system identifier (e.g. "jira", "manual").
        raw_payload: Complete original payload as received from the webhook,
            preserved for auditability.
        constraints_extracted: Structured constraints extracted in Phase 3
            (comparison operators, numeric thresholds, boolean conditions).
        embedding: 384-dimensional vector from BGE-small-en-v1.5 (Phase 4).
    """

    __tablename__ = "requirements"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    external_id: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        comment="Source-system requirement ID, e.g. REQ-123",
    )
    title: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )
    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="",
    )
    source: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="jira",
        comment="Origin system: jira, manual, etc.",
    )
    raw_payload: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Full original payload from the webhook",
    )
    constraints_extracted: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Structured constraints extracted in Phase 3",
    )
    embedding = mapped_column(
        Vector(384),
        nullable=True,
        comment="BGE-small-en-v1.5 embedding (384 dimensions)",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    test_cases: Mapped[list["TestCase"]] = relationship(
        "TestCase",
        back_populates="requirement",
        cascade="all, delete-orphan",
    )
    traceability_entries: Mapped[list["TraceabilityMatrix"]] = relationship(
        "TraceabilityMatrix",
        back_populates="requirement",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_requirements_external_id", "external_id"),
        Index("ix_requirements_source", "source"),
    )

    def __repr__(self) -> str:
        return f"<Requirement(external_id={self.external_id!r}, title={self.title!r})>"


# Resolve forward references
from orion.models.test_case import TestCase  # noqa: E402, F811
from orion.models.traceability_matrix import TraceabilityMatrix  # noqa: E402, F811
