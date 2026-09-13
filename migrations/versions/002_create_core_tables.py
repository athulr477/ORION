"""Create core tables: requirements, test_cases, traceability_matrix.

Revision ID: 002_core_tables
Revises: 001_pgvector
Create Date: 2025-01-01 00:00:01.000000

"""
from typing import Sequence, Union

import pgvector.sqlalchemy
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "002_core_tables"
down_revision: Union[str, None] = "001_pgvector"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- requirements ---
    op.create_table(
        "requirements",
        sa.Column("id", sa.UUID(), nullable=False, default=sa.text("gen_random_uuid()")),
        sa.Column(
            "external_id",
            sa.String(length=255),
            nullable=False,
            comment="Source-system requirement ID, e.g. REQ-123",
        ),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column(
            "source",
            sa.String(length=50),
            nullable=False,
            server_default="jira",
            comment="Origin system: jira, manual, etc.",
        ),
        sa.Column(
            "raw_payload",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="Full original payload from the webhook",
        ),
        sa.Column(
            "constraints_extracted",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="Structured constraints extracted in Phase 3",
        ),
        sa.Column(
            "embedding",
            pgvector.sqlalchemy.Vector(dim=384),
            nullable=True,
            comment="BGE-small-en-v1.5 embedding (384 dimensions)",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("external_id"),
    )
    op.create_index("ix_requirements_external_id", "requirements", ["external_id"])
    op.create_index("ix_requirements_source", "requirements", ["source"])

    # --- test_cases ---
    op.create_table(
        "test_cases",
        sa.Column("id", sa.UUID(), nullable=False, default=sa.text("gen_random_uuid()")),
        sa.Column(
            "requirement_id",
            sa.UUID(),
            nullable=True,
            comment="FK to linked requirement (from @traces decorator)",
        ),
        sa.Column(
            "external_id",
            sa.String(length=500),
            nullable=False,
            comment="Unique ID: file_path::function_name",
        ),
        sa.Column("function_name", sa.String(length=255), nullable=False),
        sa.Column("file_path", sa.String(length=500), nullable=False),
        sa.Column("source_code", sa.Text(), nullable=False, server_default=""),
        sa.Column(
            "docstring",
            sa.Text(),
            nullable=True,
            comment="Test docstring; null triggers fallback embedding strategy",
        ),
        sa.Column(
            "assertions_extracted",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="Structured assertions extracted in Phase 3",
        ),
        sa.Column(
            "embedding",
            pgvector.sqlalchemy.Vector(dim=384),
            nullable=True,
            comment="BGE-small-en-v1.5 embedding (384 dimensions)",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["requirement_id"],
            ["requirements.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("external_id"),
    )
    op.create_index("ix_test_cases_external_id", "test_cases", ["external_id"])
    op.create_index("ix_test_cases_requirement_id", "test_cases", ["requirement_id"])
    op.create_index("ix_test_cases_file_path", "test_cases", ["file_path"])

    # --- traceability_matrix ---
    # Create the enum type first
    traceability_status = postgresql.ENUM(
        "Covered", "Partial", "Drifted",
        name="traceability_status",
        create_type=True,
    )

    op.create_table(
        "traceability_matrix",
        sa.Column("id", sa.UUID(), nullable=False, default=sa.text("gen_random_uuid()")),
        sa.Column("requirement_id", sa.UUID(), nullable=False),
        sa.Column("test_case_id", sa.UUID(), nullable=False),
        sa.Column(
            "semantic_score",
            sa.Float(),
            nullable=True,
            comment="Cosine similarity from Phase 4",
        ),
        sa.Column(
            "structural_score",
            sa.Float(),
            nullable=True,
            comment="Structural match score from Phase 5",
        ),
        sa.Column(
            "risk_score",
            sa.Float(),
            nullable=True,
            comment="Combined: 0.6 × semantic + 0.4 × structural",
        ),
        sa.Column(
            "confidence",
            sa.Float(),
            nullable=True,
            comment="Classification confidence (0.0–1.0)",
        ),
        sa.Column(
            "status",
            traceability_status,
            nullable=True,
            comment="Covered / Partial / Drifted",
        ),
        sa.Column(
            "requirement_delta",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="Structured diff from Phase 6 requirement tracking",
        ),
        sa.Column(
            "audit_summary",
            sa.Text(),
            nullable=True,
            comment="Evidence-grounded explanation from Phase 7",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["requirement_id"],
            ["requirements.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["test_case_id"],
            ["test_cases.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("requirement_id", "test_case_id", name="uq_req_test"),
    )
    op.create_index(
        "ix_traceability_matrix_requirement_id",
        "traceability_matrix",
        ["requirement_id"],
    )
    op.create_index(
        "ix_traceability_matrix_test_case_id",
        "traceability_matrix",
        ["test_case_id"],
    )
    op.create_index(
        "ix_traceability_matrix_status",
        "traceability_matrix",
        ["status"],
    )


def downgrade() -> None:
    op.drop_table("traceability_matrix")
    op.execute("DROP TYPE IF EXISTS traceability_status;")
    op.drop_table("test_cases")
    op.drop_table("requirements")
