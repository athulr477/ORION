"""Authentication API routes."""

from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from orion.auth.security import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    create_access_token,
    get_current_user,
    verify_password,
)
from orion.database import get_session
from orion.models.user import User
from orion.models.workspace import Workspace, WorkspaceMember

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/token")
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    session: AsyncSession = Depends(get_session),
):
    """OAuth2 compatible token login, getting an access token for future requests."""
    stmt = select(User).where(User.username == form_data.username)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()
    
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username, "role": user.role.value},
        expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "username": user.username,
        "role": user.role.value
    }


@router.get("/workspaces")
async def get_user_workspaces(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Get all workspaces the current user is a member of."""
    stmt = (
        select(Workspace)
        .join(WorkspaceMember, Workspace.id == WorkspaceMember.workspace_id)
        .where(WorkspaceMember.user_id == current_user.id)
        .order_by(Workspace.name)
    )
    result = await session.execute(stmt)
    workspaces = result.scalars().all()
    
    return [
        {
            "id": str(ws.id),
            "name": ws.name,
        }
        for ws in workspaces
    ]
