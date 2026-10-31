"""Database-backed task broker."""

from __future__ import annotations

import logging
import uuid
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from orion.models.task_job import TaskJob, TaskStatus

logger = logging.getLogger(__name__)


async def enqueue_task(
    session: AsyncSession,
    task_type: str,
    payload: dict[str, Any],
    workspace_id: str | uuid.UUID | None = None,
) -> uuid.UUID:
    """Enqueue a new task into the background worker system.

    Args:
        session: Database session.
        task_type: A string identifying the type of task (e.g. "simulate_run").
        payload: Input parameters for the task.
        workspace_id: The workspace ID. If None, we will try to fetch the default workspace for backwards compatibility with tests.

    Returns:
        The UUID of the created task.
    """
    if not workspace_id:
        from orion.models.workspace import Workspace

        stmt = select(Workspace.id).where(Workspace.name == "Default Workspace")
        result = await session.execute(stmt)
        workspace_id = result.scalar_one_or_none()

    job = TaskJob(
        id=uuid.uuid4(),
        task_type=task_type,
        payload=payload,
        status=TaskStatus.PENDING,
        workspace_id=workspace_id,
    )
    session.add(job)
    await session.commit()
    logger.info("Enqueued task %s of type '%s'", job.id, task_type)
    return job.id


async def get_task_status(session: AsyncSession, task_id: uuid.UUID) -> TaskJob | None:
    """Retrieve a task by ID."""
    stmt = select(TaskJob).where(TaskJob.id == task_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def claim_next_task(session: AsyncSession) -> TaskJob | None:
    """Atomically claim the next pending task.

    Uses PostgreSQL's `FOR UPDATE SKIP LOCKED` to ensure concurrent workers
    don't claim the same task.

    This function modifies the state of the task to RUNNING. The caller must
    commit the transaction (this is typically done by the worker engine).
    """
    import datetime

    # We use a subquery to select the ID of the next pending task with row-level locking
    subq = (
        select(TaskJob.id)
        .where(TaskJob.status == TaskStatus.PENDING)
        .order_by(TaskJob.created_at.asc())
        .limit(1)
        .with_for_update(skip_locked=True)
    )

    # Update the status to RUNNING in the same transaction
    stmt = (
        update(TaskJob)
        .where(TaskJob.id == subq.scalar_subquery())
        .values(
            status=TaskStatus.RUNNING,
            started_at=datetime.datetime.now(datetime.UTC).replace(tzinfo=None),
        )
        .returning(TaskJob)
    )

    result = await session.execute(stmt)
    job = result.scalar_one_or_none()

    # Do not commit here — we want the caller (worker) to commit the claim,
    # or it will automatically roll back if the worker crashes immediately.
    return job
