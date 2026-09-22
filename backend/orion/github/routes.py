"""GitHub App webhook routes — Phase 9.

Listens for pull_request events from GitHub.
For each PR touching test files with @traces decorators, runs the
Orion hybrid risk engine end-to-end and reports a native GitHub Check Run.

Endpoint:
    POST /api/v1/github/events

Flow:
    1. Verify X-Hub-Signature-256 HMAC.
    2. Filter: only process pull_request events with action in
       [opened, synchronize, reopened]. Return 200 for all others.
    3. Parse owner/repo/pull_number/head_sha from payload.
    4. Resolve installation_id from payload (fallback to settings).
    5. Get Installation Access Token.
    6. Create in_progress Check Run → get check_run_id.
    7. Fetch changed test files from the PR.
    8. For each test file:
       a. Fetch raw content from GitHub API.
       b. Parse @traces decorators → requirement IDs.
       c. Look up requirement in DB.
       d. Extract code assertions + compute embedding.
       e. Compute structural + semantic scores → classify.
       f. Run Phase 7 verbalization for Partial/Drifted.
    9. Aggregate: worst status wins (Drifted > Partial > Covered).
    10. Complete Check Run with conclusion + markdown table.
"""

from __future__ import annotations

import hashlib
import hmac
import logging

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from orion.analysis.risk_engine import classify
from orion.analysis.structural_matcher import compute_structural_score
from orion.config import settings
from orion.database import get_session, get_session_context
from orion.embedding.engine import semantic_similarity, embed_text
from orion.embedding.text_builder import build_test_text
from orion.extraction.code_extractor import extract_assertions
from orion.ingestion.service import enrich_requirement
from orion.github.auth import get_installation_token
from orion.queue.broker import enqueue_task
from orion.github.client import (
    build_check_summary,
    complete_check_run,
    create_check_run,
    fail_check_run,
    fetch_file_content,
    fetch_pr_files,
)
from orion.github.schemas import GitHubPRPayload
from orion.ingestion.parsers import extract_test_functions
from orion.models.requirement import Requirement
from orion.models.test_case import TestCase
from orion.models.traceability_matrix import TraceabilityMatrix, TraceabilityStatus
from orion.verbalization.service import verbalize_entry

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/github", tags=["github"])

# Actions that trigger a traceability analysis
_ANALYSED_ACTIONS = {"opened", "synchronize", "reopened"}


# ---------------------------------------------------------------------------
# Signature verification helper (inline — avoids coupling to ingestion pkg)
# ---------------------------------------------------------------------------

async def _verify_github_signature_raw(request: Request) -> bytes:
    """Read body and verify X-Hub-Signature-256.

    Returns the raw body bytes so the caller can parse JSON separately.

    Raises:
        HTTPException 401: If signature is missing or invalid.
    """
    body = await request.body()
    secret = settings.github_webhook_secret

    raw_header = request.headers.get("X-Hub-Signature-256", "")
    if not raw_header and secret:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-Hub-Signature-256 header",
        )

    if secret:
        signature = raw_header.removeprefix("sha256=")
        expected = hmac.new(
            secret.encode("utf-8"),
            body,
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(expected, signature):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid GitHub webhook signature",
            )

    return body


# ---------------------------------------------------------------------------
# Core analysis — runs in a background task
# ---------------------------------------------------------------------------

async def _analyse_pr(
    owner: str,
    repo: str,
    pull_number: int,
    head_sha: str,
    installation_id: int,
    check_run_id: int,
    token: str,
    workspace_id: str,
) -> None:
    """Run the full Orion analysis for a PR and complete the GitHub Check Run.

    This runs as a FastAPI BackgroundTask so the webhook endpoint can
    return 202 Accepted immediately within GitHub's 10-second timeout.
    """
    results: list[dict] = []

    try:
        # ------------------------------------------------------------------
        # Fetch changed test files
        # ------------------------------------------------------------------
        test_files = fetch_pr_files(owner, repo, pull_number, token)
        if not test_files:
            logger.info(
                "PR #%d in %s/%s: no test files changed — skipping analysis",
                pull_number, owner, repo,
            )
            conclusion, title, summary = build_check_summary([])
            complete_check_run(owner, repo, check_run_id, conclusion, title, summary, token)
            return

        # ------------------------------------------------------------------
        # For each test file, run the hybrid pipeline
        # ------------------------------------------------------------------
        async with get_session_context() as session:
            for file_info in test_files:
                filename = file_info["filename"]
                logger.info("Analysing test file: %s", filename)

                # Fetch raw file content from GitHub
                try:
                    file_content = fetch_file_content(owner, repo, filename, head_sha, token)
                except Exception as exc:
                    logger.warning("Could not fetch %s from GitHub: %s", filename, exc)
                    continue

                # Parse @traces decorators → test functions
                functions = extract_test_functions(file_content)
                if not functions:
                    logger.info("No @traces decorators found in %s", filename)
                    continue

                for func_data in functions:
                    for req_external_id in func_data.traced_requirements:
                        result = await _classify_pair(
                            session=session,
                            req_external_id=req_external_id,
                            func_data=func_data,
                            file_path=filename,
                            workspace_id=workspace_id,
                        )
                        if result:
                            results.append(result)

        # ------------------------------------------------------------------
        # Aggregate & complete Check Run
        # ------------------------------------------------------------------
        conclusion, title, summary = build_check_summary(results)
        complete_check_run(owner, repo, check_run_id, conclusion, title, summary, token)

        logger.info(
            "PR #%d in %s/%s: analysis complete — %d pairs, conclusion=%s",
            pull_number, owner, repo, len(results), conclusion,
        )

    except Exception as exc:
        logger.exception(
            "Unhandled error analysing PR #%d in %s/%s",
            pull_number, owner, repo,
        )
        fail_check_run(owner, repo, check_run_id, str(exc), token)


async def _classify_pair(
    session: AsyncSession,
    req_external_id: str,
    func_data,
    file_path: str,
    workspace_id: str,
) -> dict | None:
    """Run the Orion hybrid classification pipeline for one requirement-test pair.

    Args:
        session: Async database session.
        req_external_id: Requirement external ID from @traces decorator.
        func_data: Parsed test function data (from ingestion/parsers.py).
        file_path: File path within the repository.

    Returns:
        Dict with classification results, or None if the requirement is not found in DB.
    """
    # Look up the requirement in the database
    stmt = (
        select(Requirement)
        .where(
            Requirement.external_id == req_external_id,
            Requirement.workspace_id == workspace_id
        )
    )
    result = await session.execute(stmt)
    requirement = result.scalar_one_or_none()

    if requirement is None:
        logger.warning(
            "Requirement %s not found in DB — "
            "it may need to be ingested first via /webhooks/jira",
            req_external_id,
        )
        return None

    # -----------------------------------------------------------------------
    # Phase 3 & 4: Enrich requirement (constraints & embedding)
    # -----------------------------------------------------------------------
    await enrich_requirement(session, requirement)
    req_constraints = requirement.constraints_extracted
    req_embedding = requirement.embedding

    code_assertions = extract_assertions(func_data.source_code)
    assertions_dict = {"assertions": [a.__dict__ for a in code_assertions]}

    test_text = build_test_text(
        function_name=func_data.function_name,
        docstring=func_data.docstring,
        assertions_extracted=assertions_dict,
    )
    test_embedding = embed_text(test_text)

    semantic_score = semantic_similarity(req_embedding, test_embedding)

    # -----------------------------------------------------------------------
    # Phase 5: Structural matching + hybrid classification
    # -----------------------------------------------------------------------
    match_result = compute_structural_score(req_constraints, code_assertions)
    structural_score = match_result.structural_score
    risk_result = classify(semantic_score, structural_score)

    # -----------------------------------------------------------------------
    # Upsert into traceability_matrix
    # -----------------------------------------------------------------------
    test_external_id = f"{file_path}::{func_data.function_name}"

    # Find or create the TestCase record
    tc_stmt = select(TestCase).where(
        TestCase.external_id == test_external_id,
        TestCase.workspace_id == workspace_id
    )
    tc_result = await session.execute(tc_stmt)
    test_case = tc_result.scalar_one_or_none()

    if test_case is None:
        import uuid
        test_case = TestCase(
            id=uuid.uuid4(),
            external_id=test_external_id,
            function_name=func_data.function_name,
            file_path=file_path,
            source_code=func_data.source_code,
            docstring=func_data.docstring,
            requirement_id=requirement.id,
            workspace_id=workspace_id,
            assertions_extracted=assertions_dict,
            embedding=test_embedding,
        )
        session.add(test_case)
        await session.flush()
    else:
        test_case.source_code = func_data.source_code
        test_case.docstring = func_data.docstring
        test_case.requirement_id = requirement.id
        test_case.assertions_extracted = assertions_dict
        test_case.embedding = test_embedding
        await session.flush()

    # Find or upsert traceability matrix entry
    tm_stmt = (
        select(TraceabilityMatrix)
        .options(
            selectinload(TraceabilityMatrix.requirement),
            selectinload(TraceabilityMatrix.test_case),
        )
        .where(
            TraceabilityMatrix.requirement_id == requirement.id,
            TraceabilityMatrix.test_case_id == test_case.id,
            TraceabilityMatrix.workspace_id == workspace_id,
        )
    )
    tm_result = await session.execute(tm_stmt)
    entry = tm_result.scalar_one_or_none()

    if entry is None:
        import uuid
        entry = TraceabilityMatrix(
            id=uuid.uuid4(),
            requirement_id=requirement.id,
            test_case_id=test_case.id,
            workspace_id=workspace_id,
        )
        session.add(entry)

    entry.semantic_score = risk_result.semantic_score
    entry.structural_score = risk_result.structural_score
    entry.risk_score = risk_result.risk_score
    entry.confidence = risk_result.confidence
    entry.status = TraceabilityStatus(risk_result.status)
    await session.flush()

    # -----------------------------------------------------------------------
    # Phase 7: LLM verbalization for Partial/Drifted
    # -----------------------------------------------------------------------
    audit_summary: str | None = None
    if risk_result.status in ("Partial", "Drifted"):
        try:
            # Attach loaded relationships for verbalization
            entry.requirement = requirement
            entry.test_case = test_case
            audit_summary = await verbalize_entry(session, entry)
        except Exception:
            logger.warning(
                "Verbalization failed for %s ↔ %s",
                req_external_id, func_data.function_name,
                exc_info=True,
            )

    await session.commit()

    return {
        "req_id": req_external_id,
        "req_title": requirement.title,
        "test_fn": func_data.function_name,
        "file_path": file_path,
        "status": risk_result.status,
        "risk_score": risk_result.risk_score,
        "semantic_score": risk_result.semantic_score,
        "structural_score": risk_result.structural_score,
        "audit_summary": audit_summary or entry.audit_summary,
    }


# ---------------------------------------------------------------------------
# Webhook endpoint
# ---------------------------------------------------------------------------

@router.post(
    "/events",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Receive GitHub App webhook events (pull_request)",
    description=(
        "Accepts GitHub App webhook events. For pull_request events with "
        "action=opened/synchronize/reopened, runs the Orion hybrid traceability "
        "engine on changed test files and posts a GitHub Check Run result."
    ),
)
async def github_app_events(
    request: Request,
    session: AsyncSession = Depends(get_session),
    workspace_id: str | None = Query(
        None,
        description=(
            "Workspace UUID this GitHub App is bound to. "
            "Append ?workspace_id=<uuid> when registering the webhook URL in your GitHub App settings."
        ),
    ),
) -> dict:
    """Handle GitHub App webhook events.

    Returns 202 Accepted immediately; analysis runs in the background
    to stay within GitHub's 10-second webhook timeout.

    The webhook URL must include ?workspace_id=<your-workspace-uuid> so Orion
    knows which tenant to write results to. Example:
        https://your-host/api/v1/github/events?workspace_id=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
    """
    # Validate workspace_id before doing any other work
    if not workspace_id:
        logger.error(
            "GitHub webhook received without workspace_id query parameter. "
            "Re-register the webhook URL with ?workspace_id=<uuid> appended."
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Missing required 'workspace_id' query parameter. "
                "Append ?workspace_id=<your-workspace-uuid> to the webhook URL "
                "in your GitHub App settings."
            ),
        )
    try:
        import uuid as _uuid
        _uuid.UUID(workspace_id)  # validate format
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid workspace_id format: {workspace_id!r} — must be a UUID.",
        )
    # 1. Verify signature and read body
    body = await _verify_github_signature_raw(request)

    # 2. Check event type header
    event_type = request.headers.get("X-GitHub-Event", "")
    if event_type == "ping":
        logger.info("GitHub App ping received — webhook is connected ✓")
        return {"status": "pong"}

    if event_type != "pull_request":
        logger.debug("Ignoring GitHub event: %s", event_type)
        return {"status": "ignored", "event": event_type}

    # 3. Parse payload
    import json
    try:
        raw = json.loads(body)
        payload = GitHubPRPayload.model_validate(raw)
    except Exception as exc:
        logger.error("Failed to parse GitHub PR payload: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid payload: {exc}",
        )

    # 4. Filter by action
    if payload.action not in _ANALYSED_ACTIONS:
        logger.debug("Ignoring pull_request action: %s", payload.action)
        return {"status": "ignored", "action": payload.action}

    owner = payload.owner
    repo = payload.repo
    pull_number = payload.pull_number
    head_sha = payload.head_sha

    if not all([owner, repo, pull_number, head_sha]):
        logger.error("Incomplete PR payload: owner=%s repo=%s pr=%s sha=%s",
                     owner, repo, pull_number, head_sha)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Incomplete pull_request payload — missing owner/repo/number/sha",
        )

    # 5. Resolve installation ID (payload wins over settings)
    installation_id = payload.installation_id or settings.github_app_installation_id

    logger.info(
        "PR #%d opened/synced in %s/%s @ %s (installation=%s)",
        pull_number, owner, repo, head_sha[:8], installation_id,
    )

    # 6. Get installation token + create Check Run immediately
    try:
        token = get_installation_token(installation_id)
        check_run_id = create_check_run(owner, repo, head_sha, token)
    except Exception as exc:
        logger.error("Failed to create Check Run: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Could not authenticate with GitHub: {exc}",
        )

    # 7. Enqueue background analysis using Phase 13 task queue
    payload_dict = {
        "owner": owner,
        "repo": repo,
        "pull_number": pull_number,
        "head_sha": head_sha,
        "installation_id": installation_id,
        "check_run_id": check_run_id,
        "token": token,
        "workspace_id": str(workspace_id) if workspace_id else None,
    }
    await enqueue_task(session, "pr_analysis", payload_dict)

    return {
        "status": "accepted",
        "check_run_id": check_run_id,
        "pr": pull_number,
        "repo": f"{owner}/{repo}",
    }
