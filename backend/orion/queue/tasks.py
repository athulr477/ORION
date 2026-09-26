"""Task handlers for the background worker."""

import logging
from collections.abc import Awaitable, Callable
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from orion.queue.worker import worker

logger = logging.getLogger(__name__)


@worker.register("pr_analysis")
async def handle_pr_analysis(
    payload: dict[str, Any],
    session: AsyncSession,
    update_progress: Callable[[float, str], Awaitable[None]]
) -> dict[str, Any]:
    """Execute the PR analysis pipeline.
    
    Payload expects:
        owner: str
        repo: str
        pull_number: int
        head_sha: str
        installation_id: int
        check_run_id: int
        token: str
    """
    await update_progress(0.1, "Initializing PR analysis")
    
    # We import inline to avoid circular dependencies if worker is imported early
    from orion.github.routes import _analyse_pr
    
    owner = payload["owner"]
    repo = payload["repo"]
    pull_number = payload["pull_number"]
    head_sha = payload["head_sha"]
    installation_id = payload["installation_id"]
    check_run_id = payload["check_run_id"]
    token = payload["token"]
    workspace_id = payload.get("workspace_id", "")

    await update_progress(0.3, f"Fetching and parsing PR #{pull_number}")
    
    # Run the heavy PR analysis function
    await _analyse_pr(
        owner=owner,
        repo=repo,
        pull_number=pull_number,
        head_sha=head_sha,
        installation_id=installation_id,
        check_run_id=check_run_id,
        token=token,
        workspace_id=workspace_id,
    )
    
    await update_progress(0.9, "Check Run posted to GitHub")
    return {"status": "success", "pull_number": pull_number}


@worker.register("simulate_run")
async def handle_simulate_run(
    payload: dict[str, Any],
    session: AsyncSession,
    update_progress: Callable[[float, str], Awaitable[None]]
) -> dict[str, Any]:
    """Execute the simulation pipeline incrementally."""
    await update_progress(0.1, "Initializing simulation pipeline")
    
    # Inline import
    from orion.dashboard.schemas import SimulateRequest
    from orion.dashboard.service import simulate_webhook_logic

    request = SimulateRequest(**payload)
    workspace_id = payload.get("workspace_id")
    
    result = await simulate_webhook_logic(request, session, update_progress, workspace_id=workspace_id)
    return result

