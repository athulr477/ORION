"""Webhook signature verification (HMAC-SHA256) for Jira and GitHub."""

from __future__ import annotations

import hashlib
import hmac
import logging

from fastapi import HTTPException, Request, status

from orion.config import settings

logger = logging.getLogger(__name__)


async def _read_body(request: Request) -> bytes:
    """Read and cache the raw request body for signature verification.

    FastAPI consumes the body stream, so we cache it on ``request.state``
    to allow both signature verification and JSON parsing to access it.
    """
    if not hasattr(request.state, "body"):
        request.state.body = await request.body()
    return request.state.body


def _verify_hmac_sha256(body: bytes, secret: str, signature: str) -> bool:
    """Compare an HMAC-SHA256 digest against the provided signature."""
    if not secret:
        logger.warning("Webhook secret is empty — skipping signature verification")
        return True  # Allow during development when secret is not configured
    expected = hmac.new(
        secret.encode("utf-8"),
        body,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


async def verify_jira_signature(request: Request) -> None:
    """FastAPI dependency: verify Jira webhook HMAC-SHA256 signature.

    Jira Cloud sends the signature in the ``X-Hub-Signature`` header
    as ``sha256=<hex-digest>``.

    Raises:
        HTTPException 401 if signature is missing or invalid.
    """
    body = await _read_body(request)
    raw_header = request.headers.get("X-Hub-Signature", "")
    if not raw_header and settings.jira_webhook_secret:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Jira webhook signature header",
        )
    # Strip "sha256=" prefix if present
    signature = raw_header.removeprefix("sha256=")
    if not _verify_hmac_sha256(body, settings.jira_webhook_secret, signature):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Jira webhook signature",
        )


async def verify_github_signature(request: Request) -> None:
    """FastAPI dependency: verify GitHub webhook HMAC-SHA256 signature.

    GitHub sends the signature in the ``X-Hub-Signature-256`` header
    as ``sha256=<hex-digest>``.

    Raises:
        HTTPException 401 if signature is missing or invalid.
    """
    body = await _read_body(request)
    raw_header = request.headers.get("X-Hub-Signature-256", "")
    if not raw_header and settings.github_webhook_secret:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing GitHub webhook signature header",
        )
    # Strip "sha256=" prefix
    signature = raw_header.removeprefix("sha256=")
    if not _verify_hmac_sha256(body, settings.github_webhook_secret, signature):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid GitHub webhook signature",
        )
