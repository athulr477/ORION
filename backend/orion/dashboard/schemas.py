"""Pydantic response schemas for the dashboard API."""

from __future__ import annotations

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Matrix table row
# ---------------------------------------------------------------------------


class MatrixRow(BaseModel):
    """A single row in the RTM table, joining traceability + requirement + test."""

    id: str
    requirement_id: str
    requirement_external_id: str
    requirement_title: str
    test_case_id: str
    test_function_name: str
    test_file_path: str
    semantic_score: float | None = None
    structural_score: float | None = None
    risk_score: float | None = None
    confidence: float | None = None
    status: str | None = None
    audit_summary: str | None = None
    has_delta: bool = False
    is_manually_overridden: bool = False
    created_at: str | None = None
    updated_at: str | None = None


class MatrixResponse(BaseModel):
    """Paginated matrix table response."""

    rows: list[MatrixRow]
    total: int
    page: int
    page_size: int


# ---------------------------------------------------------------------------
# Reclassify (live threshold preview)
# ---------------------------------------------------------------------------


class ReclassifyRequest(BaseModel):
    """Custom thresholds for live reclassification preview."""

    covered_threshold: float = Field(
        0.75,
        ge=0.0,
        le=1.0,
        description="risk_score above this → Covered",
    )
    drifted_threshold: float = Field(
        0.4,
        ge=0.0,
        le=1.0,
        description="risk_score below this → Drifted",
    )


class ReclassifiedRow(BaseModel):
    """A row with recomputed status based on custom thresholds."""

    id: str
    risk_score: float | None = None
    original_status: str | None = None
    new_status: str | None = None
    changed: bool = False


class ReclassifyResponse(BaseModel):
    """Result of live reclassification with custom thresholds."""

    covered_threshold: float
    drifted_threshold: float
    rows: list[ReclassifiedRow]
    total: int
    changed_count: int


# ---------------------------------------------------------------------------
# XAI Heatmap
# ---------------------------------------------------------------------------


class HeatmapKeyword(BaseModel):
    """A keyword occurrence with match info."""

    word: str
    source: str = Field(description="'requirement' or 'test'")
    matched: bool = False
    score: float = 0.0


class HeatmapConstraintMatch(BaseModel):
    """A constraint-to-assertion match for the heatmap."""

    constraint_index: int
    constraint_text: str = ""
    constraint_operator: str | None = None
    constraint_value: str | None = None
    assertion_index: int
    assertion_text: str = ""
    assertion_operator: str | None = None
    assertion_value: str | None = None
    operator_score: float = 0.0
    value_score: float = 0.0
    keyword_score: float = 0.0
    combined_score: float = 0.0


class HeatmapResponse(BaseModel):
    """XAI heatmap data for a single traceability entry."""

    entry_id: str
    requirement_external_id: str
    requirement_title: str
    requirement_description: str = ""
    test_function_name: str
    test_file_path: str
    semantic_score: float | None = None
    structural_score: float | None = None
    risk_score: float | None = None
    status: str | None = None
    audit_summary: str | None = None
    requirement_constraints: list[dict] = Field(default_factory=list)
    test_assertions: list[dict] = Field(default_factory=list)
    matches: list[HeatmapConstraintMatch] = Field(default_factory=list)
    keywords: list[HeatmapKeyword] = Field(default_factory=list)
    requirement_delta: dict | None = None


# ---------------------------------------------------------------------------
# Stats
# ---------------------------------------------------------------------------


class StatsResponse(BaseModel):
    """Summary statistics for the dashboard header."""

    total_entries: int = 0
    covered_count: int = 0
    partial_count: int = 0
    drifted_count: int = 0
    avg_risk_score: float | None = None
    avg_semantic_score: float | None = None
    avg_structural_score: float | None = None
    total_requirements: int = 0
    total_test_cases: int = 0


# ---------------------------------------------------------------------------
# Simulate webhook
# ---------------------------------------------------------------------------


class SimulateRequest(BaseModel):
    """Payload for the simulate-webhook demo button."""

    requirement_external_id: str = Field(
        "REQ-DEMO-001",
        description="External ID for the demo requirement",
    )
    requirement_title: str = Field(
        "Response time must be less than 200ms",
        description="Requirement title",
    )
    requirement_description: str = Field(
        "The API response time must be less than 200 milliseconds "
        "under normal load conditions. The system must handle at "
        "least 100 concurrent requests.",
        description="Requirement description text",
    )
    test_function_name: str = Field(
        "test_response_time_under_limit",
        description="Test function name",
    )
    test_source_code: str = Field(
        (
            '@traces("REQ-DEMO-001")\n'
            "def test_response_time_under_limit():\n"
            '    """Verify API responds within 200ms."""\n'
            "    response = client.get('/api/endpoint')\n"
            "    assert response.elapsed.total_seconds() < 0.2\n"
            "    assert response.status_code == 200\n"
        ),
        description="Full test source code",
    )
    test_file_path: str = Field(
        "tests/test_performance.py",
        description="Test file path",
    )


class SimulateResponse(BaseModel):
    """Result of a simulate-webhook demo run."""

    status: str = "ok"
    requirement_id: str | None = None
    test_case_id: str | None = None
    matrix_entry: MatrixRow | None = None
    pipeline_steps: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Manual Override
# ---------------------------------------------------------------------------


class OverrideRequest(BaseModel):
    """Payload for QA Lead manual risk score override."""

    new_status: str = Field(description="The new status (Covered, Partial, Drifted)")
    rationale: str = Field(description="Mandatory reason for override")
