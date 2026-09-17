"""Authentication and authorization dependencies."""

import uuid
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from orion.auth.security import get_current_user
from orion.database import get_session
from orion.models.user import User
from orion.models.workspace import Workspace, WorkspaceMember


async def get_current_workspace(
    x_workspace_id: Annotated[str | None, Header()] = None,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> Workspace:
    """Retrieve the selected workspace based on X-Workspace-ID header.
    
    Verifies that the current user is a member of the requested workspace.
    Falls back to user's first membership workspace or Default Workspace if header is missing.
    """
    if x_workspace_id:
        try:
            workspace_uuid = uuid.UUID(x_workspace_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid workspace ID format",
            )
            
        stmt = (
            select(Workspace)
            .join(WorkspaceMember, Workspace.id == WorkspaceMember.workspace_id)
            .where(
                Workspace.id == workspace_uuid,
                WorkspaceMember.user_id == current_user.id
            )
        )
        result = await session.execute(stmt)
        workspace = result.scalar_one_or_none()
        
        if not workspace:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access to this workspace is forbidden or it does not exist",
            )
            
        return workspace

    # Fallback 1: User's first workspace membership
    stmt = (
        select(Workspace)
        .join(WorkspaceMember, Workspace.id == WorkspaceMember.workspace_id)
        .where(WorkspaceMember.user_id == current_user.id)
        .order_by(Workspace.name)
        .limit(1)
    )
    result = await session.execute(stmt)
    workspace = result.scalar_one_or_none()
    if workspace:
        return workspace

    # No workspace membership found — refuse access rather than silently
    # falling through to another tenant's workspace.
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=(
            "You are not a member of any workspace. "
            "Contact an administrator to be added to a workspace."
        ),
    )
