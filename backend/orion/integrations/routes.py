"""Workspace Integrations API routes.

Provides endpoints for managing, checking, and testing connections to:
- Jira Cloud REST API
- GitHub App & Webhooks
- Ollama local LLM
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends
import httpx
from pydantic import BaseModel

from orion.auth.dependencies import get_current_workspace
from orion.config import settings
from orion.github.auth import _load_private_key, _mint_jwt
from orion.jira.client import test_jira_connection
from orion.models.workspace import Workspace

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/integrations", tags=["integrations"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class JiraStatus(BaseModel):
    configured: bool
    base_url: str
    user_email: str
    project_key: str
    has_token: bool
    token_masked: str


class GitHubStatus(BaseModel):
    configured: bool
    app_id: int
    installation_id: int
    pem_path: str
    pem_exists: bool
    webhook_configured: bool
    webhook_url: str


class OllamaStatus(BaseModel):
    base_url: str
    model: str
    available: bool


class IntegrationsStatusResponse(BaseModel):
    workspace_id: str
    workspace_name: str
    jira: JiraStatus
    github: GitHubStatus
    ollama: OllamaStatus


class JiraTestRequest(BaseModel):
    base_url: str | None = None
    user_email: str | None = None
    api_token: str | None = None
    project_key: str | None = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mask_secret(secret: str) -> str:
    if not secret:
        return ""
    if len(secret) <= 8:
        return "********"
    return f"{secret[:5]}...{secret[-4:]}"


def _check_ollama_available(base_url: str) -> bool:
    try:
        with httpx.Client(timeout=2.0) as client:
            res = client.get(f"{base_url.rstrip('/')}/api/tags")
            return res.is_success
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/status", response_model=IntegrationsStatusResponse)
async def get_integrations_status(
    current_workspace: Workspace = Depends(get_current_workspace),
) -> dict[str, Any]:
    """Get the current integration status for the active workspace."""
    pem_path = Path(settings.github_app_private_key_path) if settings.github_app_private_key_path else None
    pem_exists = pem_path.exists() if pem_path else False

    jira_configured = bool(settings.jira_base_url and settings.jira_api_token)
    github_configured = bool(settings.github_app_id and pem_exists)
    ollama_ok = _check_ollama_available(settings.ollama_base_url)

    return {
        "workspace_id": str(current_workspace.id),
        "workspace_name": current_workspace.name,
        "jira": {
            "configured": jira_configured,
            "base_url": settings.jira_base_url,
            "user_email": settings.jira_user_email,
            "project_key": settings.jira_project_key,
            "has_token": bool(settings.jira_api_token),
            "token_masked": _mask_secret(settings.jira_api_token),
        },
        "github": {
            "configured": github_configured,
            "app_id": settings.github_app_id,
            "installation_id": settings.github_app_installation_id,
            "pem_path": settings.github_app_private_key_path,
            "pem_exists": pem_exists,
            "webhook_configured": bool(settings.github_webhook_secret),
            "webhook_url": "/api/v1/github/events",
        },
        "ollama": {
            "base_url": settings.ollama_base_url,
            "model": settings.ollama_model,
            "available": ollama_ok,
        },
    }


@router.post("/jira/test")
async def test_jira(
    payload: JiraTestRequest,
    current_workspace: Workspace = Depends(get_current_workspace),
) -> dict[str, Any]:
    """Test Jira connectivity and verify user and project permissions."""
    result = test_jira_connection(
        base_url=payload.base_url,
        email=payload.user_email,
        token=payload.api_token,
        project_key=payload.project_key,
    )
    return result


@router.post("/github/test")
async def test_github(
    current_workspace: Workspace = Depends(get_current_workspace),
) -> dict[str, Any]:
    """Verify GitHub App private key PEM and mint a test RS256 JWT."""
    try:
        if not settings.github_app_id:
            return {
                "success": False,
                "error": "GITHUB_APP_ID is not configured. Set GITHUB_APP_ID in .env.",
            }

        private_key = _load_private_key()
        jwt_token = _mint_jwt(settings.github_app_id, private_key)
        return {
            "success": True,
            "app_id": settings.github_app_id,
            "installation_id": settings.github_app_installation_id,
            "jwt_minted": True,
            "jwt_length": len(jwt_token),
            "message": f"Successfully minted RS256 JWT for GitHub App #{settings.github_app_id}",
        }
    except Exception as exc:
        logger.error("GitHub App test failed: %s", exc)
        return {
            "success": False,
            "error": str(exc),
        }
