"""Test case model — stores test functions ingested from GitHub pushes."""

import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from orion.database import Base


class TestCase(Base):
    """A test function ingested from a GitHub push.

    The link to a requirement is established via the `@traces("REQ-123")`
    decorator, parsed at ingestion time (Phase 2). This populates the
    `requirement_id` foreign key.

    Fields:
        requirement_id: FK to the linked requirement (from @traces decorator).
        external_id: Unique identifier combining file_path + function_name.
        function_name: The test function name (e.g. "test_threshold_check").
        file_path: Path to the test file in the repository.
        source_code: Full source code of the test function.
        docstring: Test function docstring (nullable — fallback embedding
            uses function_name + assertion literals when absent).
        assertions_extracted: Structured assertion data extracted in Phase 3
            (operators, literal values, exception types, etc.).
        embedding: 384-dimensional vector from BGE-small-en-v1.5 (Phase 4).
    """

    __tablename__ = "test_cases"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    requirement_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("requirements.id", ondelete="SET NULL"),
        nullable=True,
        comment="FK to linked requirement (from @traces decorator)",
    )
    external_id: Mapped[str] = mapped_column(
        String(500),
        unique=True,
        nullable=False,
        comment="Unique ID: file_path::function_name",
    )
    function_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    file_path: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )
    source_code: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="",
    )
    docstring: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Test docstring; null triggers fallback embedding strategy",
    )
    assertions_extracted: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Structured assertions extracted in Phase 3",
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
    requirement: Mapped["Requirement"] = relationship(
        "Requirement",
        back_populates="test_cases",
    )
    traceability_entries: Mapped[list["TraceabilityMatrix"]] = relationship(
        "TraceabilityMatrix",
        back_populates="test_case",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_test_cases_external_id", "external_id"),
        Index("ix_test_cases_requirement_id", "requirement_id"),
        Index("ix_test_cases_file_path", "file_path"),
    )

    def __repr__(self) -> str:
        return f"<TestCase(function_name={self.function_name!r}, file_path={self.file_path!r})>"


# Resolve forward references
from orion.models.requirement import Requirement  # noqa: E402, F811
from orion.models.traceability_matrix import TraceabilityMatrix  # noqa: E402, F811
