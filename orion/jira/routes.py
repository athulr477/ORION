"""Jira REST API routes — Phase 11.

Endpoints:
    POST /api/v1/jira/sync
        Bulk-import all issues from the configured Jira project (JQL search).
        Upserts each issue as a Requirement, computes BGE-small embedding,
        extracts structural constraints. Returns counts of created/updated.

    POST /api/v1/jira/sync/{issue_key}
        On-demand single-ticket refresh. Fetches the latest state from Jira
        and upserts into the database.

    POST /api/v1/jira/report-drift
        Called internally after traceability analysis to post drift alert
        comments back to Jira tickets for Partial/Drifted pairs.
        Includes duplicate-comment guard.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from orion.config import settings
from orion.database import get_session
from orion.embedding.engine import embed_text
from orion.embedding.text_builder import build_requirement_text
from orion.extraction.requirement_extractor import extract_constraints
from orion.ingestion.parsers import RequirementData
from orion.ingestion.service import upsert_requirement
from orion.jira.client import (
    fetch_issue,
    fetch_project_issues,
    has_recent_drift_comment,
    post_drift_comment,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/jira", tags=["jira"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class SyncResult(BaseModel):
    """Response from a Jira sync operation."""
    status: str
    project_key: str
    total_fetched: int
    created: int
    updated: int
    skipped: int
    errors: int
    details: list[str] = []


class DriftReportRequest(BaseModel):
    """Request body for posting a drift alert comment to Jira."""
    issue_key: str
    test_function_name: str
    traceability_status: str  # "Partial" or "Drifted"
    risk_score: float
    semantic_score: float | None = None
    structural_score: float | None = None
    audit_summary: str | None = None
    force: bool = False  # If True, skip duplicate comment guard


class DriftReportResult(BaseModel):
    """Response from a drift comment post."""
    issue_key: str
    comment_posted: bool
    skipped_reason: str | None = None


# ---------------------------------------------------------------------------
# Helper: build RequirementData from a JiraIssue
# ---------------------------------------------------------------------------

def _jira_issue_to_requirement_data(issue) -> RequirementData:
    """Convert a JiraIssue to RequirementData for upsert_requirement."""
    # Build a combined description including status/type context
    meta_prefix = ""
    if issue.issue_type:
        meta_prefix += f"[{issue.issue_type}] "
    if issue.priority:
        meta_prefix += f"Priority: {issue.priority}. "

    description = (meta_prefix + issue.description).strip() if meta_prefix else issue.description

    return RequirementData(
        external_id=issue.key,
        title=issue.summary,
        description=description,
        source="jira",
        raw_payload=issue.raw,
        changelog=None,  # REST API fetch doesn't include changelog
    )


# ---------------------------------------------------------------------------
# Helper: compute and persist embedding + constraints for a requirement
# ---------------------------------------------------------------------------

async def _enrich_requirement(session: AsyncSession, requirement) -> None:
    """Compute and store embedding + structural constraints for a requirement.

    Skips if already computed (avoids re-embedding on every sync).

    Args:
        session: Active database session.
        requirement: Requirement ORM instance (already flushed to DB).
    """
    updated = False

    if requirement.constraints_extracted is None:
        constraints = extract_constraints(requirement.description or "")
        # extract_constraints returns a RequirementExtractionResult dataclass—
        # call .to_dict() so it is JSON-serialisable for JSONB storage.
        requirement.constraints_extracted = (
            constraints.to_dict() if hasattr(constraints, "to_dict") else constraints
        )
        updated = True

    if requirement.embedding is None:
        req_text = build_requirement_text(requirement.title, requirement.description or "")
        embedding = embed_text(req_text)
        requirement.embedding = embedding
        updated = True

    if updated:
        await session.flush()


# ---------------------------------------------------------------------------
# POST /api/v1/jira/sync — bulk project sync
# ---------------------------------------------------------------------------

@router.post(
    "/sync",
    response_model=SyncResult,
    summary="Bulk-import all issues from Jira project via JQL",
    description=(
        "Queries the configured Jira project using JQL, fetches all issues, "
        "upserts them as Requirements in the Orion database, and computes "
        "BGE-small embeddings + structural constraints for each."
    ),
)
async def sync_jira_project(
    project_key: str | None = Query(
        None,
        description="Override the project key (default: from JIRA_PROJECT_KEY env var)",
    ),
    max_results: int = Query(
        500,
        ge=1,
        le=2000,
        description="Maximum number of issues to import",
    ),
    session: AsyncSession = Depends(get_session),
) -> SyncResult:
    """Bulk-import all issues from a Jira project."""
    key = project_key or settings.jira_project_key
    if not key:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No project key provided and JIRA_PROJECT_KEY is not set in .env",
        )

    # Validate credentials upfront
    if not settings.jira_base_url or not settings.jira_api_token:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Jira credentials not configured. Set JIRA_BASE_URL, JIRA_USER_EMAIL, JIRA_API_TOKEN in .env",
        )

    logger.info("Starting Jira bulk sync for project: %s (max_results=%d)", key, max_results)

    try:
        issues = fetch_project_issues(project_key=key, max_results=max_results)
    except Exception as exc:
        logger.error("Failed to fetch issues from Jira: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Jira API error: {exc}",
        )

    total_fetched = len(issues)
    created = 0
    updated = 0
    skipped = 0
    errors = 0
    details: list[str] = []

    for issue in issues:
        try:
            req_data = _jira_issue_to_requirement_data(issue)
            requirement, was_created = await upsert_requirement(session, req_data)
            await _enrich_requirement(session, requirement)

            if was_created:
                created += 1
                details.append(f"CREATED {issue.key}: {issue.summary[:60]}")
            else:
                updated += 1
                details.append(f"UPDATED {issue.key}: {issue.summary[:60]}")

        except Exception as exc:
            errors += 1
            logger.exception("Failed to upsert issue %s", issue.key)
            details.append(f"ERROR {issue.key}: {exc}")

    await session.commit()

    logger.info(
        "Jira sync complete: project=%s fetched=%d created=%d updated=%d errors=%d",
        key, total_fetched, created, updated, errors,
    )

    return SyncResult(
        status="ok",
        project_key=key,
        total_fetched=total_fetched,
        created=created,
        updated=updated,
        skipped=skipped,
        errors=errors,
        details=details,
    )


# ---------------------------------------------------------------------------
# POST /api/v1/jira/sync/{issue_key} — single-ticket on-demand refresh
# ---------------------------------------------------------------------------

@router.post(
    "/sync/{issue_key}",
    response_model=SyncResult,
    summary="On-demand single-ticket refresh from Jira",
    description=(
        "Fetches the latest state of a single Jira issue and upserts it "
        "into the Orion database. Useful for the dashboard 'Refresh from Jira' button."
    ),
)
async def sync_single_issue(
    issue_key: str,
    session: AsyncSession = Depends(get_session),
) -> SyncResult:
    """Refresh a single Jira issue."""
    if not settings.jira_base_url or not settings.jira_api_token:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Jira credentials not configured.",
        )

    try:
        issue = fetch_issue(issue_key)
    except Exception as exc:
        logger.error("Failed to fetch issue %s from Jira: %s", issue_key, exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Jira API error fetching {issue_key}: {exc}",
        )

    try:
        req_data = _jira_issue_to_requirement_data(issue)
        requirement, was_created = await upsert_requirement(session, req_data)
        await _enrich_requirement(session, requirement)
        await session.commit()
    except Exception as exc:
        logger.exception("Failed to upsert issue %s", issue_key)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error for {issue_key}: {exc}",
        )

    action = "CREATED" if was_created else "UPDATED"
    return SyncResult(
        status="ok",
        project_key=issue_key.split("-")[0] if "-" in issue_key else issue_key,
        total_fetched=1,
        created=1 if was_created else 0,
        updated=0 if was_created else 1,
        skipped=0,
        errors=0,
        details=[f"{action} {issue_key}: {issue.summary[:80]}"],
    )


# ---------------------------------------------------------------------------
# POST /api/v1/jira/report-drift — post drift comment back to Jira
# ---------------------------------------------------------------------------

@router.post(
    "/report-drift",
    response_model=DriftReportResult,
    summary="Post a traceability drift alert comment to a Jira ticket",
    description=(
        "Posts an Orion drift alert as a structured comment directly onto "
        "the Jira ticket. Includes a duplicate guard — if the most recent "
        "Orion comment already reflects the current drift, it is skipped "
        "unless force=true is set."
    ),
)
async def report_drift_to_jira(
    body: DriftReportRequest,
) -> DriftReportResult:
    """Post a drift comment to a Jira ticket."""
    if body.traceability_status not in ("Partial", "Drifted"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="traceability_status must be 'Partial' or 'Drifted'",
        )

    if not settings.jira_base_url or not settings.jira_api_token:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Jira credentials not configured.",
        )

    # Duplicate guard: skip if already commented (unless force=True)
    if not body.force:
        try:
            if has_recent_drift_comment(body.issue_key):
                logger.info(
                    "Skipping drift comment on %s — recent Orion comment already exists",
                    body.issue_key,
                )
                return DriftReportResult(
                    issue_key=body.issue_key,
                    comment_posted=False,
                    skipped_reason="Recent Orion drift comment already exists. Use force=true to override.",
                )
        except Exception:
            logger.warning("Could not check comments on %s — proceeding", body.issue_key)

    try:
        post_drift_comment(
            issue_key=body.issue_key,
            status=body.traceability_status,
            risk_score=body.risk_score,
            test_function_name=body.test_function_name,
            audit_summary=body.audit_summary,
            semantic_score=body.semantic_score,
            structural_score=body.structural_score,
        )
    except Exception as exc:
        logger.exception("Failed to post drift comment to %s", body.issue_key)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Jira comment API error: {exc}",
        )

    return DriftReportResult(
        issue_key=body.issue_key,
        comment_posted=True,
    )
