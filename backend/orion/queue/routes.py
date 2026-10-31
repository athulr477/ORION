"""Task queue API endpoints."""

from __future__ import annotations

import logging
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from orion.auth.dependencies import get_current_workspace
from orion.auth.security import get_current_user
from orion.database import get_session
from orion.models.task_job import TaskJob
from orion.models.workspace import Workspace

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get("", response_model=list[dict[str, Any]], summary="List background tasks")
async def list_tasks(
    limit: int = 50,
    session: AsyncSession = Depends(get_session),
    current_user: Any = Depends(get_current_user),
    current_workspace: Workspace = Depends(get_current_workspace),
) -> list[dict[str, Any]]:
    """Get a list of recent background tasks for the current workspace."""
    stmt = (
        select(TaskJob)
        .where(TaskJob.workspace_id == current_workspace.id)
        .order_by(TaskJob.created_at.desc())
        .limit(limit)
    )
    result = await session.execute(stmt)
    tasks = result.scalars().all()

    return [
        {
            "id": str(t.id),
            "task_type": t.task_type,
            "status": t.status.value if hasattr(t.status, "value") else str(t.status),
            "progress": round(t.progress, 2) if t.progress is not None else 0.0,
            "current_step": t.current_step,
            "created_at": t.created_at.isoformat() if t.created_at else None,
            "completed_at": t.completed_at.isoformat() if t.completed_at else None,
            "error_message": t.error_message,
        }
        for t in tasks
    ]


@router.get("/{task_id}", response_model=dict[str, Any], summary="Get task status")
async def get_task(
    task_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: Any = Depends(get_current_user),
    current_workspace: Workspace = Depends(get_current_workspace),
) -> dict[str, Any]:
    """Retrieve detailed status for a specific task in the current workspace."""
    try:
        task_uuid = uuid.UUID(task_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid task ID") from exc

    stmt = select(TaskJob).where(
        TaskJob.id == task_uuid,
        TaskJob.workspace_id == current_workspace.id,
    )
    result = await session.execute(stmt)
    t = result.scalar_one_or_none()

    if not t:
        raise HTTPException(status_code=404, detail="Task not found")

    return {
        "id": str(t.id),
        "task_type": t.task_type,
        "status": t.status.value if hasattr(t.status, "value") else str(t.status),
        "progress": round(t.progress, 2) if t.progress is not None else 0.0,
        "current_step": t.current_step,
        "payload": t.payload,
        "result": t.result,
        "error_message": t.error_message,
        "created_at": t.created_at.isoformat() if t.created_at else None,
        "started_at": t.started_at.isoformat() if t.started_at else None,
        "completed_at": t.completed_at.isoformat() if t.completed_at else None,
    }
