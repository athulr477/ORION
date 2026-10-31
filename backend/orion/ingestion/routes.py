"""FastAPI routes for webhook ingestion endpoints."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from orion.database import get_session
from orion.ingestion.parsers import (
    extract_test_functions,
    parse_jira_payload,
)
from orion.ingestion.schemas import (
    IngestionResult,
    JiraWebhookPayload,
    SimulateGitHubPushPayload,
)
from orion.ingestion.service import upsert_requirement, upsert_test_cases
from orion.ingestion.signatures import verify_github_signature, verify_jira_signature

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


# ---------------------------------------------------------------------------
# Jira Webhook
# ---------------------------------------------------------------------------


@router.post(
    "/jira",
    response_model=IngestionResult,
    summary="Receive Jira webhook",
    dependencies=[Depends(verify_jira_signature)],
)
async def jira_webhook(
    payload: JiraWebhookPayload,
    session: AsyncSession = Depends(get_session),
) -> IngestionResult:
    """Ingest a requirement from a Jira webhook event.

    Supports ``jira:issue_created`` and ``jira:issue_updated`` events.
    Verifies HMAC-SHA256 signature before processing.
    """
    logger.info(
        "Received Jira webhook: event=%s issue=%s",
        payload.webhook_event,
        payload.issue.key,
    )

    data = parse_jira_payload(payload.model_dump(by_alias=True))
    requirement, was_created = await upsert_requirement(session, data)
    await session.commit()

    action = "created" if was_created else "updated"
    return IngestionResult(
        status="ok",
        created=1 if was_created else 0,
        updated=0 if was_created else 1,
        details=f"Requirement {requirement.external_id} {action}",
    )


# ---------------------------------------------------------------------------
# GitHub Push Webhook (simulate mode for Phase 2)
# ---------------------------------------------------------------------------


@router.post(
    "/github",
    response_model=IngestionResult,
    summary="Receive GitHub push webhook (simulate mode)",
    dependencies=[Depends(verify_github_signature)],
)
async def github_webhook(
    payload: SimulateGitHubPushPayload,
    session: AsyncSession = Depends(get_session),
) -> IngestionResult:
    """Ingest test cases from a simulated GitHub push.

    In Phase 2, file content is sent directly in the payload (simulate mode).
    Real GitHub API content fetching will be added in Phase 9 with GitHub App auth.

    Parses ``@traces("REQ-xxx")`` decorators from test files and links
    test cases to requirements via FK.
    """
    logger.info(
        "Received GitHub push webhook: repo=%s ref=%s files=%d",
        payload.repository_name,
        payload.ref,
        len(payload.test_files),
    )

    total_created = 0
    total_updated = 0
    total_linked = 0
    total_unlinked = 0

    for test_file in payload.test_files:
        functions = extract_test_functions(test_file.content)
        if not functions:
            logger.info("No test functions found in %s — skipping", test_file.file_path)
            continue

        created, updated, linked, unlinked = await upsert_test_cases(
            session, test_file.file_path, functions
        )
        total_created += created
        total_updated += updated
        total_linked += linked
        total_unlinked += unlinked

    await session.commit()

    return IngestionResult(
        status="ok",
        created=total_created,
        updated=total_updated,
        linked=total_linked,
        unlinked=total_unlinked,
        details=(
            f"Processed {len(payload.test_files)} file(s): "
            f"{total_created} created, {total_updated} updated, "
            f"{total_linked} linked, {total_unlinked} unlinked"
        ),
    )
