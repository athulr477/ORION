"""Task handlers for the background worker."""

import logging
from collections.abc import Awaitable, Callable
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


def _get_worker():
    """Lazy accessor for the worker singleton — avoids circular imports.

    ``tasks.py`` is imported by ``worker.py`` (via ``_ensure_tasks_registered``),
    so a top-level ``from orion.queue.worker import worker`` would create a
    circular import and return a partially-initialized module, silently leaving
    all handlers unregistered.  Deferring the import to call-time is safe
    because by the time any decorator runs the ``worker`` object already exists.
    """
    from orion.queue.worker import worker  # noqa: PLC0415

    return worker


async def handle_pr_analysis(
    payload: dict[str, Any],
    session: AsyncSession,
    update_progress: Callable[[float, str], Awaitable[None]],
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

    from orion.github.routes import _analyse_pr  # inline to avoid early import

    owner = payload["owner"]
    repo = payload["repo"]
    pull_number = payload["pull_number"]
    head_sha = payload["head_sha"]
    installation_id = payload["installation_id"]
    check_run_id = payload["check_run_id"]
    token = payload["token"]
    workspace_id = payload.get("workspace_id", "")

    await update_progress(0.3, f"Fetching and parsing PR #{pull_number}")

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


async def handle_simulate_run(
    payload: dict[str, Any],
    session: AsyncSession,
    update_progress: Callable[[float, str], Awaitable[None]],
) -> dict[str, Any]:
    """Execute the simulation pipeline incrementally."""
    await update_progress(0.1, "Initializing simulation pipeline")

    from orion.dashboard.schemas import SimulateRequest
    from orion.dashboard.service import simulate_webhook_logic

    request = SimulateRequest(**payload)
    workspace_id = payload.get("workspace_id")

    result = await simulate_webhook_logic(
        request, session, update_progress, workspace_id=workspace_id
    )
    return result


def register_all() -> None:
    """Register all task handlers with the worker.

    Called explicitly by the app lifespan (``orion.app``) after ``worker.py``
    is fully initialized, so ``_get_worker()`` returns the real singleton.
    """
    w = _get_worker()
    w.register("pr_analysis")(handle_pr_analysis)
    w.register("simulate_run")(handle_simulate_run)
    logging.getLogger(__name__).info("All task handlers registered.")
