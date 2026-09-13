"""GitHub App authentication — RS256 JWT minting + Installation Access Token.

Phase 9 authentication flow:
1. Read the private key (.pem) from disk.
2. Mint a 10-minute RS256 JWT signed with the App's private key.
3. Exchange the JWT for an Installation Access Token (valid 60 min) via
   POST https://api.github.com/app/installations/{id}/access_tokens
4. Cache the token in memory; refresh 5 minutes before expiry.

Reference:
    https://docs.github.com/en/apps/creating-github-apps/authenticating-with-a-github-app/generating-an-installation-access-token-for-a-github-app
"""

from __future__ import annotations

import logging
import time
from pathlib import Path

import httpx
import jwt

from orion.config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_GITHUB_API_BASE = "https://api.github.com"
_JWT_EXPIRY_SECONDS = 600          # GitHub requires <= 10 min
_TOKEN_REFRESH_BUFFER_SECONDS = 300  # Refresh 5 min before token expires

# ---------------------------------------------------------------------------
# In-memory token cache
# ---------------------------------------------------------------------------

_cached_token: str | None = None
_token_expires_at: float = 0.0  # epoch seconds


# ---------------------------------------------------------------------------
# JWT minting
# ---------------------------------------------------------------------------

def _load_private_key() -> str:
    """Load the GitHub App private key PEM from the configured path.

    Raises:
        FileNotFoundError: If the .pem file does not exist.
        ValueError: If GITHUB_APP_PRIVATE_KEY_PATH is not configured.
    """
    key_path = settings.github_app_private_key_path
    if not key_path:
        raise ValueError(
            "GITHUB_APP_PRIVATE_KEY_PATH is not set in .env. "
            "Download the private key from your GitHub App settings."
        )
    path = Path(key_path)
    if not path.exists():
        raise FileNotFoundError(
            f"GitHub App private key not found at: {path.resolve()}\n"
            f"Download it from: github.com/settings/apps → your app → Private keys"
        )
    return path.read_text(encoding="utf-8")


def _mint_jwt(app_id: int, private_key_pem: str) -> str:
    """Mint a short-lived RS256 JWT for the GitHub App.

    Args:
        app_id: GitHub App ID (from settings).
        private_key_pem: PEM-encoded RSA private key content.

    Returns:
        Encoded JWT string.
    """
    now = int(time.time())
    payload = {
        "iat": now - 60,   # issued-at (60s in past to account for clock skew)
        "exp": now + _JWT_EXPIRY_SECONDS,
        "iss": str(app_id),
    }
    token = jwt.encode(payload, private_key_pem, algorithm="RS256")
    logger.debug("Minted GitHub App JWT for app_id=%s (exp=%s)", app_id, payload["exp"])
    return token


# ---------------------------------------------------------------------------
# Installation Access Token exchange
# ---------------------------------------------------------------------------

def _exchange_for_installation_token(app_jwt: str, installation_id: int) -> tuple[str, float]:
    """Exchange a GitHub App JWT for an Installation Access Token.

    Args:
        app_jwt: Short-lived RS256 JWT.
        installation_id: The installation ID for the target repo/org.

    Returns:
        Tuple of (token_string, expires_at_epoch_seconds).

    Raises:
        httpx.HTTPStatusError: If the GitHub API returns an error.
    """
    url = f"{_GITHUB_API_BASE}/app/installations/{installation_id}/access_tokens"
    headers = {
        "Authorization": f"Bearer {app_jwt}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    with httpx.Client(timeout=15) as client:
        response = client.post(url, headers=headers)
        response.raise_for_status()

    data = response.json()
    token = data["token"]

    # Parse expiry: GitHub returns ISO 8601 like "2024-01-01T00:00:00Z"
    # We subtract the buffer so we refresh before actual expiry.
    expires_at_str: str = data.get("expires_at", "")
    if expires_at_str:
        from datetime import datetime, timezone
        dt = datetime.fromisoformat(expires_at_str.replace("Z", "+00:00"))
        expires_at = dt.timestamp() - _TOKEN_REFRESH_BUFFER_SECONDS
    else:
        # Fallback: assume 60-minute lifetime
        expires_at = time.time() + 3600 - _TOKEN_REFRESH_BUFFER_SECONDS

    logger.info(
        "Obtained GitHub installation token for installation_id=%s (refreshes in %.0f min)",
        installation_id,
        (expires_at - time.time()) / 60,
    )
    return token, expires_at


# ---------------------------------------------------------------------------
# Public API — cached token getter
# ---------------------------------------------------------------------------

def get_installation_token(installation_id: int | None = None) -> str:
    """Return a valid GitHub Installation Access Token, refreshing if needed.

    Uses module-level cache to avoid re-minting on every request.

    Args:
        installation_id: Override the installation ID from settings.
            Pass this when the ID comes from the webhook payload.

    Returns:
        A valid GitHub Installation Access Token string.

    Raises:
        ValueError: If configuration is missing.
        FileNotFoundError: If the PEM file is missing.
        httpx.HTTPStatusError: If the GitHub API call fails.
    """
    global _cached_token, _token_expires_at

    inst_id = installation_id or settings.github_app_installation_id
    if not inst_id:
        raise ValueError(
            "GITHUB_APP_INSTALLATION_ID is not configured. "
            "Set it in .env or pass it explicitly."
        )

    now = time.time()
    if _cached_token and now < _token_expires_at:
        logger.debug("Using cached GitHub installation token (expires in %.0f s)", _token_expires_at - now)
        return _cached_token

    logger.info("GitHub installation token expired or missing — refreshing")
    private_key_pem = _load_private_key()
    app_jwt = _mint_jwt(settings.github_app_id, private_key_pem)
    token, expires_at = _exchange_for_installation_token(app_jwt, inst_id)

    _cached_token = token
    _token_expires_at = expires_at
    return token
