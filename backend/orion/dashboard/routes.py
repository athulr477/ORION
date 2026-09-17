"""Dashboard API routes — Phase 8.

Endpoints serving the React frontend with RTM data, live reclassification,
XAI heatmap evidence, summary stats, and a simulate-webhook demo button.
"""

from __future__ import annotations

import logging
import re
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from orion.analysis.risk_engine import (
    classify,
)
from orion.analysis.structural_matcher import compute_structural_score
from orion.auth.security import get_current_user, require_qa_lead
from orion.auth.dependencies import get_current_workspace
from orion.models.user import User
from orion.models.workspace import Workspace
from orion.models.audit_log import AuditLog
from orion.dashboard.schemas import (
    HeatmapConstraintMatch,
    HeatmapKeyword,
    HeatmapResponse,
    MatrixResponse,
    MatrixRow,
    ReclassifiedRow,
    ReclassifyRequest,
    ReclassifyResponse,
    SimulateRequest,
    SimulateResponse,
    StatsResponse,
    OverrideRequest,
)
from orion.database import get_session
from orion.extraction.code_extractor import extract_assertions
from orion.extraction.requirement_extractor import extract_constraints
from orion.models.requirement import Requirement
from orion.models.test_case import TestCase
from orion.models.traceability_matrix import TraceabilityMatrix, TraceabilityStatus

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


# ---------------------------------------------------------------------------
# Helper: build MatrixRow from ORM objects
# ---------------------------------------------------------------------------


def _build_matrix_row(entry: TraceabilityMatrix) -> MatrixRow:
    """Convert a TraceabilityMatrix ORM instance (with loaded relations) to a MatrixRow."""
    req = entry.requirement
    tc = entry.test_case
    return MatrixRow(
        id=str(entry.id),
        requirement_id=str(entry.requirement_id),
        requirement_external_id=req.external_id if req else "?",
        requirement_title=req.title if req else "Unknown",
        test_case_id=str(entry.test_case_id),
        test_function_name=tc.function_name if tc else "Unknown",
        test_file_path=tc.file_path if tc else "",
        semantic_score=round(entry.semantic_score, 4) if entry.semantic_score is not None else None,
        structural_score=round(entry.structural_score, 4) if entry.structural_score is not None else None,
        risk_score=round(entry.risk_score, 4) if entry.risk_score is not None else None,
        confidence=round(entry.confidence, 4) if entry.confidence is not None else None,
        status=entry.status.value if entry.status else None,
        audit_summary=entry.audit_summary,
        has_delta=entry.requirement_delta is not None and bool(entry.requirement_delta),
        is_manually_overridden=getattr(entry, "is_manually_overridden", False),
        created_at=entry.created_at.isoformat() if entry.created_at else None,
        updated_at=entry.updated_at.isoformat() if entry.updated_at else None,
    )


# ---------------------------------------------------------------------------
# GET /matrix — paginated RTM table
# ---------------------------------------------------------------------------


@router.get("/matrix", response_model=MatrixResponse, summary="Paginated RTM table")
async def get_matrix(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    status: str | None = Query(None, description="Filter by status: Covered, Partial, Drifted"),
    sort: str = Query("risk_score", description="Sort column"),
    order: str = Query("desc", description="asc or desc"),
    search: str | None = Query(None, description="Search requirement title or external_id"),
    session: AsyncSession = Depends(get_session),
    current_workspace: Workspace = Depends(get_current_workspace),
) -> MatrixResponse:
    """Return paginated traceability matrix rows with joined requirement/test data."""

    # Base query with eager loading
    stmt = (
        select(TraceabilityMatrix)
        .options(
            selectinload(TraceabilityMatrix.requirement),
            selectinload(TraceabilityMatrix.test_case),
        )
        .where(TraceabilityMatrix.workspace_id == current_workspace.id)
    )

    # Filter by status
    if status:
        try:
            status_enum = TraceabilityStatus(status)
            stmt = stmt.where(TraceabilityMatrix.status == status_enum)
        except ValueError:
            raise HTTPException(400, f"Invalid status: {status}")

    # Search filter — join requirement table for search
    if search:
        stmt = stmt.join(TraceabilityMatrix.requirement).where(
            Requirement.title.ilike(f"%{search}%")
            | Requirement.external_id.ilike(f"%{search}%")
        )

    # Count total (before pagination)
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total_result = await session.execute(count_stmt)
    total = total_result.scalar() or 0

    # Sort
    sort_map = {
        "risk_score": TraceabilityMatrix.risk_score,
        "semantic_score": TraceabilityMatrix.semantic_score,
        "structural_score": TraceabilityMatrix.structural_score,
        "confidence": TraceabilityMatrix.confidence,
        "status": TraceabilityMatrix.status,
        "created_at": TraceabilityMatrix.created_at,
        "updated_at": TraceabilityMatrix.updated_at,
    }
    sort_col = sort_map.get(sort, TraceabilityMatrix.risk_score)
    if sort_col is not None:
        if order == "asc":
            stmt = stmt.order_by(sort_col.asc().nulls_last())
        else:
            stmt = stmt.order_by(sort_col.desc().nulls_last())

    # Paginate
    offset = (page - 1) * page_size
    stmt = stmt.offset(offset).limit(page_size)

    result = await session.execute(stmt)
    entries = result.scalars().all()

    rows = [_build_matrix_row(e) for e in entries]

    return MatrixResponse(
        rows=rows,
        total=total,
        page=page,
        page_size=page_size,
    )


# ---------------------------------------------------------------------------
# POST /matrix/reclassify — live threshold preview
# ---------------------------------------------------------------------------


@router.post(
    "/matrix/reclassify",
    response_model=ReclassifyResponse,
    summary="Live reclassification with custom thresholds",
)
async def reclassify_matrix(
    body: ReclassifyRequest,
    session: AsyncSession = Depends(get_session),
    current_workspace: Workspace = Depends(get_current_workspace),
) -> ReclassifyResponse:
    """Re-run classification with custom thresholds without persisting changes.

    Used by the sensitivity slider in the frontend.
    """
    if body.drifted_threshold >= body.covered_threshold:
        raise HTTPException(
            400,
            "drifted_threshold must be less than covered_threshold",
        )

    stmt = select(TraceabilityMatrix).where(
        TraceabilityMatrix.workspace_id == current_workspace.id,
        TraceabilityMatrix.risk_score.is_not(None),
    )
    result = await session.execute(stmt)
    entries = result.scalars().all()

    rows: list[ReclassifiedRow] = []
    changed_count = 0

    for entry in entries:
        rs = entry.risk_score
        if rs is None:
            continue

        # Classify with custom thresholds
        if rs > body.covered_threshold:
            new_status = "Covered"
        elif rs < body.drifted_threshold:
            new_status = "Drifted"
        else:
            new_status = "Partial"

        original = entry.status.value if entry.status else None
        changed = new_status != original

        if changed:
            changed_count += 1

        rows.append(
            ReclassifiedRow(
                id=str(entry.id),
                risk_score=round(rs, 4),
                original_status=original,
                new_status=new_status,
                changed=changed,
            )
        )

    return ReclassifyResponse(
        covered_threshold=body.covered_threshold,
        drifted_threshold=body.drifted_threshold,
        rows=rows,
        total=len(rows),
        changed_count=changed_count,
    )


# ---------------------------------------------------------------------------
# GET /matrix/{entry_id}/heatmap — XAI evidence
# ---------------------------------------------------------------------------


def _extract_keywords(text: str) -> list[str]:
    """Extract meaningful keywords from text for overlap highlighting."""
    if not text:
        return []
    words = re.findall(r"[a-zA-Z_]\w{2,}", text)
    stopwords = {
        "the", "and", "for", "are", "but", "not", "you", "all", "can",
        "her", "was", "one", "our", "out", "has", "had", "his", "how",
        "its", "may", "new", "now", "old", "see", "way", "who", "did",
        "get", "let", "say", "she", "too", "use", "that", "this", "with",
        "have", "from", "they", "been", "will", "each", "make", "like",
        "than", "them", "then", "what", "when", "some", "time", "very",
        "must", "shall", "should", "would", "could", "into", "also",
        "about", "other", "which", "their", "there", "these", "just",
        "over", "such", "more", "only", "after", "those", "being",
        "under", "between", "does", "none",
    }
    return [w.lower() for w in words if w.lower() not in stopwords]


@router.get(
    "/matrix/{entry_id}/heatmap",
    response_model=HeatmapResponse,
    summary="XAI keyword-overlap heatmap data",
)
async def get_heatmap(
    entry_id: str,
    session: AsyncSession = Depends(get_session),
    current_workspace: Workspace = Depends(get_current_workspace),
) -> HeatmapResponse:
    """Return evidence data for the XAI heatmap modal.

    Includes requirement constraints, test assertions, structural match
    details, and keyword overlap highlighting.
    """
    try:
        entry_uuid = uuid.UUID(entry_id)
    except ValueError:
        raise HTTPException(400, "Invalid entry ID format")

    stmt = (
        select(TraceabilityMatrix)
        .options(
            selectinload(TraceabilityMatrix.requirement),
            selectinload(TraceabilityMatrix.test_case),
        )
        .where(
            TraceabilityMatrix.id == entry_uuid,
            TraceabilityMatrix.workspace_id == current_workspace.id
        )
    )
    result = await session.execute(stmt)
    entry = result.scalar_one_or_none()

    if entry is None:
        raise HTTPException(404, "Traceability entry not found")

    req = entry.requirement
    tc = entry.test_case

    if req is None or tc is None:
        raise HTTPException(404, "Linked requirement or test case not found")

    # Extract constraint and assertion lists from JSONB
    constraints_data = req.constraints_extracted or {}
    assertions_data = tc.assertions_extracted or {}
    constraints = constraints_data.get("constraints", [])
    assertions = assertions_data.get("assertions", [])

    # Re-run structural matcher to get match details
    match_result = compute_structural_score(constraints_data, assertions_data)

    # Build match details for the heatmap
    matches: list[HeatmapConstraintMatch] = []
    for detail in match_result.match_details:
        c = constraints[detail.constraint_index] if detail.constraint_index < len(constraints) else {}
        a = assertions[detail.assertion_index] if detail.assertion_index < len(assertions) else {}

        matches.append(
            HeatmapConstraintMatch(
                constraint_index=detail.constraint_index,
                constraint_text=c.get("raw_text", ""),
                constraint_operator=c.get("operator"),
                constraint_value=str(c.get("value", "")) if c.get("value") is not None else None,
                assertion_index=detail.assertion_index,
                assertion_text=f"{a.get('left', '')} {a.get('operator', '')} {a.get('right', '')}".strip(),
                assertion_operator=a.get("operator"),
                assertion_value=str(a.get("value", "")) if a.get("value") is not None else None,
                operator_score=round(detail.operator_score, 3),
                value_score=round(detail.value_score, 3),
                keyword_score=round(detail.keyword_score, 3),
                combined_score=round(detail.combined_score, 3),
            )
        )

    # Build keyword overlap data
    req_keywords = _extract_keywords(req.description or "")
    test_keywords = _extract_keywords(tc.source_code or "")
    req_set = set(req_keywords)
    test_set = set(test_keywords)
    overlap = req_set & test_set

    keywords: list[HeatmapKeyword] = []
    for w in sorted(req_set):
        keywords.append(HeatmapKeyword(
            word=w, source="requirement",
            matched=w in overlap,
            score=1.0 if w in overlap else 0.0,
        ))
    for w in sorted(test_set):
        if w not in req_set:  # Avoid duplicates
            keywords.append(HeatmapKeyword(
                word=w, source="test",
                matched=False,
                score=0.0,
            ))

    return HeatmapResponse(
        entry_id=str(entry.id),
        requirement_external_id=req.external_id,
        requirement_title=req.title,
        requirement_description=req.description or "",
        test_function_name=tc.function_name,
        test_file_path=tc.file_path,
        semantic_score=round(entry.semantic_score, 4) if entry.semantic_score is not None else None,
        structural_score=round(entry.structural_score, 4) if entry.structural_score is not None else None,
        risk_score=round(entry.risk_score, 4) if entry.risk_score is not None else None,
        status=entry.status.value if entry.status else None,
        audit_summary=entry.audit_summary,
        requirement_constraints=constraints,
        test_assertions=assertions,
        matches=matches,
        keywords=keywords,
        requirement_delta=entry.requirement_delta,
    )


# ---------------------------------------------------------------------------
# GET /stats — summary statistics
# ---------------------------------------------------------------------------


@router.get("/stats", response_model=StatsResponse, summary="Summary statistics")
async def get_stats(
    session: AsyncSession = Depends(get_session),
    current_workspace: Workspace = Depends(get_current_workspace),
) -> StatsResponse:
    """Return aggregate statistics for the dashboard header cards."""

    # Count by status
    status_counts = {}
    for s in TraceabilityStatus:
        count_stmt = select(func.count()).where(
            TraceabilityMatrix.workspace_id == current_workspace.id,
            TraceabilityMatrix.status == s
        )
        result = await session.execute(count_stmt)
        status_counts[s.value] = result.scalar() or 0

    # Total entries
    total_stmt = select(func.count()).select_from(TraceabilityMatrix).where(TraceabilityMatrix.workspace_id == current_workspace.id)
    total_result = await session.execute(total_stmt)
    total = total_result.scalar() or 0

    # Average scores
    avg_stmt = select(
        func.avg(TraceabilityMatrix.risk_score),
        func.avg(TraceabilityMatrix.semantic_score),
        func.avg(TraceabilityMatrix.structural_score),
    ).where(TraceabilityMatrix.workspace_id == current_workspace.id)
    avg_result = await session.execute(avg_stmt)
    avg_row = avg_result.one()

    # Total requirements and test cases
    req_count_stmt = select(func.count()).select_from(Requirement).where(Requirement.workspace_id == current_workspace.id)
    req_result = await session.execute(req_count_stmt)
    total_reqs = req_result.scalar() or 0

    tc_count_stmt = select(func.count()).select_from(TestCase).where(TestCase.workspace_id == current_workspace.id)
    tc_result = await session.execute(tc_count_stmt)
    total_tests = tc_result.scalar() or 0

    return StatsResponse(
        total_entries=total,
        covered_count=status_counts.get("Covered", 0),
        partial_count=status_counts.get("Partial", 0),
        drifted_count=status_counts.get("Drifted", 0),
        avg_risk_score=round(avg_row[0], 4) if avg_row[0] is not None else None,
        avg_semantic_score=round(avg_row[1], 4) if avg_row[1] is not None else None,
        avg_structural_score=round(avg_row[2], 4) if avg_row[2] is not None else None,
        total_requirements=total_reqs,
        total_test_cases=total_tests,
    )


# ---------------------------------------------------------------------------
# POST /simulate — end-to-end demo
# ---------------------------------------------------------------------------


@router.post(
    "/simulate",
    summary="Simulate full pipeline asynchronously",
)
async def simulate_webhook(
    body: SimulateRequest,
    session: AsyncSession = Depends(get_session),
    current_workspace: Workspace = Depends(get_current_workspace),
) -> dict:
    """Enqueue a simulation task to run in the background."""
    from orion.queue.broker import enqueue_task
    payload = body.model_dump()
    payload["workspace_id"] = str(current_workspace.id)
    task_id = await enqueue_task(session, "simulate_run", payload)
    return {"status": "accepted", "task_id": str(task_id)}


# ---------------------------------------------------------------------------
# POST /matrix/{entry_id}/override — QA Lead Override
# ---------------------------------------------------------------------------


@router.post(
    "/matrix/{entry_id}/override",
    response_model=dict,
    summary="QA Lead manual risk score override",
)
async def override_matrix_entry(
    entry_id: str,
    body: OverrideRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_qa_lead),
    current_workspace: Workspace = Depends(get_current_workspace),
) -> dict:
    """Manually override a risk score and write to the audit log."""
    try:
        entry_uuid = uuid.UUID(entry_id)
    except ValueError:
        raise HTTPException(400, "Invalid entry ID format")

    stmt = select(TraceabilityMatrix).where(
        TraceabilityMatrix.id == entry_uuid,
        TraceabilityMatrix.workspace_id == current_workspace.id
    )
    result = await session.execute(stmt)
    entry = result.scalar_one_or_none()

    if entry is None:
        raise HTTPException(404, "Traceability entry not found")

    try:
        new_status = TraceabilityStatus(body.new_status)
    except ValueError:
        raise HTTPException(400, f"Invalid status: {body.new_status}")

    old_status = entry.status.value if entry.status else "Unknown"

    # Update entry
    entry.status = new_status
    entry.is_manually_overridden = True

    # Create audit log
    audit_log = AuditLog(
        user_id=current_user.id,
        workspace_id=current_workspace.id,
        traceability_matrix_id=entry.id,
        previous_status=old_status,
        new_status=new_status.value,
        rationale=body.rationale,
    )
    session.add(audit_log)
    await session.commit()

    return {"status": "success", "new_status": new_status.value}
