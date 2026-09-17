"""Jira REST API v3 client — issue search, fetch, and comment posting.

Authentication: HTTP Basic Auth with email:api_token (base64-encoded).
All calls use synchronous httpx (the Jira API is called from background
tasks and scripts, not from the main async event loop hot path).

Endpoints used:
    GET  /rest/api/3/search               — JQL issue search (paginated)
    GET  /rest/api/3/issue/{issueIdOrKey} — Fetch a single issue
    POST /rest/api/3/issue/{issueIdOrKey}/comment — Post a comment to a ticket

Reference:
    https://developer.atlassian.com/cloud/jira/platform/rest/v3/intro/
"""

from __future__ import annotations

import base64
import logging
from typing import Any

import httpx

from orion.config import settings
from orion.jira.adf import adf_to_text

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_API_BASE = "{base_url}/rest/api/3"
_PAGE_SIZE = 50  # Jira max is 100; 50 is safe and not too many round-trips

# ---------------------------------------------------------------------------
# Auth header builder
# ---------------------------------------------------------------------------


def _auth_headers(email: str | None = None, token: str | None = None) -> dict[str, str]:
    """Build HTTP Basic Auth headers for the configured Jira Cloud account.

    Encodes email:api_token in base64 as required by Atlassian REST API v3.

    Raises:
        ValueError: If JIRA_USER_EMAIL or JIRA_API_TOKEN are not configured.
    """
    user_email = email or settings.jira_user_email
    api_token = token or settings.jira_api_token
    if not user_email or not api_token:
        raise ValueError(
            "JIRA_USER_EMAIL and JIRA_API_TOKEN must be configured in .env or passed explicitly.\n"
            "Generate a token at: https://id.atlassian.com/manage-profile/security/api-tokens"
        )
    credential = f"{user_email}:{api_token}"
    encoded = base64.b64encode(credential.encode("utf-8")).decode("ascii")
    return {
        "Authorization": f"Basic {encoded}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }


def _base_url(base_url: str | None = None) -> str:
    base = (base_url or settings.jira_base_url).rstrip("/")
    if not base:
        raise ValueError("JIRA_BASE_URL must be configured in .env or passed explicitly (e.g. https://yoursite.atlassian.net)")
    return _API_BASE.format(base_url=base)


def test_jira_connection(
    base_url: str | None = None,
    email: str | None = None,
    token: str | None = None,
    project_key: str | None = None,
) -> dict[str, Any]:
    """Test connectivity and authentication against Jira Cloud REST API.

    Returns:
        dict with success status and user/project metadata.
    """
    try:
        headers = _auth_headers(email=email, token=token)
        url_prefix = _base_url(base_url=base_url)
    except Exception as exc:
        return {"success": False, "error": str(exc)}

    with httpx.Client(timeout=15) as client:
        # 1. Test user identity
        try:
            res = client.get(f"{url_prefix}/myself", headers=headers)
            if res.status_code == 401:
                return {"success": False, "error": "Invalid Jira credentials (HTTP 401 Unauthorized). Check email and API token."}
            elif res.status_code == 403:
                return {"success": False, "error": "Access forbidden (HTTP 403). Ensure the API token has sufficient permissions."}
            res.raise_for_status()
            user_data = res.json()
        except httpx.RequestError as exc:
            return {"success": False, "error": f"Failed to connect to Jira server at {base_url or settings.jira_base_url}: {exc}"}
        except Exception as exc:
            return {"success": False, "error": f"Jira API error: {exc}"}

        # 2. Test project access if specified
        target_project = project_key or settings.jira_project_key
        project_info = None
        if target_project:
            try:
                proj_res = client.get(f"{url_prefix}/project/{target_project}", headers=headers)
                if proj_res.is_success:
                    proj_data = proj_res.json()
                    project_info = {
                        "key": proj_data.get("key"),
                        "name": proj_data.get("name"),
                        "projectTypeKey": proj_data.get("projectTypeKey"),
                    }
            except Exception as exc:
                logger.warning("Could not verify Jira project %s: %s", target_project, exc)

        return {
            "success": True,
            "display_name": user_data.get("displayName"),
            "email_address": user_data.get("emailAddress") or (email or settings.jira_user_email),
            "account_id": user_data.get("accountId"),
            "project": project_info or {"key": target_project, "verified": False},
        }


# ---------------------------------------------------------------------------
# Issue Data Model
# ---------------------------------------------------------------------------

class JiraIssue:
    """Parsed data from a Jira issue, ready to upsert as a Requirement."""

    def __init__(
        self,
        key: str,
        summary: str,
        description: str,
        status: str,
        issue_type: str,
        priority: str,
        raw: dict,
    ) -> None:
        self.key = key
        self.summary = summary
        self.description = description
        self.status = status
        self.issue_type = issue_type
        self.priority = priority
        self.raw = raw

    def __repr__(self) -> str:
        return f"<JiraIssue key={self.key!r} summary={self.summary[:40]!r}>"


def _parse_issue(issue_data: dict) -> JiraIssue:
    """Parse the fields of a single Jira issue API response into JiraIssue."""
    fields = issue_data.get("fields", {})
    key = issue_data.get("key", "")

    summary = fields.get("summary") or ""

    # Description may be ADF (dict) or plain text (str) — adf_to_text handles both
    raw_desc = fields.get("description")
    description = adf_to_text(raw_desc)

    # Status, type, priority
    status_obj = fields.get("status") or {}
    status = status_obj.get("name", "")

    issuetype_obj = fields.get("issuetype") or {}
    issue_type = issuetype_obj.get("name", "")

    priority_obj = fields.get("priority") or {}
    priority = priority_obj.get("name", "")

    return JiraIssue(
        key=key,
        summary=summary,
        description=description,
        status=status,
        issue_type=issue_type,
        priority=priority,
        raw=issue_data,
    )


# ---------------------------------------------------------------------------
# Public API: Fetch a single issue
# ---------------------------------------------------------------------------

def fetch_issue(issue_key: str) -> JiraIssue:
    """Fetch a single Jira issue by its key (e.g. 'SCRUM-1').

    Args:
        issue_key: The Jira issue key.

    Returns:
        Parsed JiraIssue instance.

    Raises:
        httpx.HTTPStatusError: On non-2xx response (404, 401, etc.).
        ValueError: If Jira credentials are not configured.
    """
    url = f"{_base_url()}/issue/{issue_key}"
    params = {
        "fields": "summary,description,status,issuetype,priority,comment",
    }
    with httpx.Client(timeout=20) as client:
        response = client.get(url, headers=_auth_headers(), params=params)
        response.raise_for_status()

    issue_data = response.json()
    issue = _parse_issue(issue_data)
    logger.info(
        "Fetched Jira issue %s: %s (type=%s, status=%s)",
        issue.key, issue.summary[:60], issue.issue_type, issue.status,
    )
    return issue


# ---------------------------------------------------------------------------
# Public API: JQL search (paginated)
# ---------------------------------------------------------------------------

def search_issues(
    jql: str,
    max_results: int = 500,
) -> list[JiraIssue]:
    """Run a JQL search and return all matching issues (auto-paginated).

    Uses GET /rest/api/3/search/jql — the new Atlassian endpoint.
    The old POST /rest/api/3/search and GET /rest/api/3/search both
    return 410 Gone for free-tier Jira Cloud instances.

    The /search/jql response returns only {id} stubs per issue.
    We then batch-fetch full issue details using the returned IDs.

    Args:
        jql: JQL query string, e.g. 'project = "SCRUM" ORDER BY created ASC'.
        max_results: Maximum total issues to return (safety cap). Default 500.

    Returns:
        List of JiraIssue instances.

    Raises:
        httpx.HTTPStatusError: On non-2xx response.
        ValueError: If Jira credentials are not configured.
    """
    search_url = f"{_base_url()}/search/jql"
    issues: list[JiraIssue] = []
    next_page_token: str | None = None
    fields = "summary,description,status,issuetype,priority"

    with httpx.Client(timeout=30) as client:
        while len(issues) < max_results:
            params: dict[str, Any] = {
                "jql": jql,
                "maxResults": min(_PAGE_SIZE, max_results - len(issues)),
                "fields": fields,
            }
            if next_page_token:
                params["nextPageToken"] = next_page_token

            response = client.get(search_url, headers=_auth_headers(), params=params)
            response.raise_for_status()
            data = response.json()

            page_issues = data.get("issues", [])
            if not page_issues:
                break

            for raw in page_issues:
                # The new endpoint may return full fields or just stubs.
                # If stub (only 'id' present), fetch the full issue.
                if raw.get("fields"):
                    issues.append(_parse_issue(raw))
                else:
                    issue_id = raw.get("id") or raw.get("key", "")
                    if issue_id:
                        try:
                            full = fetch_issue(issue_id)
                            issues.append(full)
                        except Exception as exc:
                            logger.warning("Could not fetch full data for %s: %s", issue_id, exc)

            logger.info(
                "JQL search '%s': fetched %d issues so far",
                jql[:60], len(issues),
            )

            # Pagination: the new endpoint uses nextPageToken
            next_page_token = data.get("nextPageToken")
            is_last = data.get("isLast", True)
            if is_last or not next_page_token:
                break

    return issues


# ---------------------------------------------------------------------------
# Public API: Project bulk sync
# ---------------------------------------------------------------------------

def fetch_project_issues(
    project_key: str | None = None,
    issue_types: list[str] | None = None,
    max_results: int = 500,
) -> list[JiraIssue]:
    """Fetch all issues from a Jira project using JQL.

    Constructs a JQL query like:
        project = "SCRUM" AND issuetype in (Story, Task, Bug, Epic) ORDER BY created ASC

    Args:
        project_key: Jira project key. Defaults to settings.jira_project_key.
        issue_types: List of issue types to include. Defaults to common types.
        max_results: Safety cap on total results.

    Returns:
        List of JiraIssue instances.
    """
    key = project_key or settings.jira_project_key
    types = issue_types or ["Story", "Task", "Bug", "Epic", "Subtask", "Requirement"]
    types_str = ", ".join(types)
    jql = f'project = "{key}" AND issuetype in ({types_str}) ORDER BY created ASC'
    logger.info("Fetching all issues from project %s with JQL: %s", key, jql)
    return search_issues(jql, max_results=max_results)


# ---------------------------------------------------------------------------
# Public API: Post comment to a Jira issue (bi-directional drift alert)
# ---------------------------------------------------------------------------

_DRIFT_COMMENT_TAG = "orion-rtm-alert"


def post_drift_comment(
    issue_key: str,
    status: str,
    risk_score: float,
    test_function_name: str,
    audit_summary: str | None,
    semantic_score: float | None = None,
    structural_score: float | None = None,
) -> None:
    """Post a traceability drift alert comment to a Jira issue.

    Uses ADF format for the comment body so it renders with correct formatting
    in Jira Cloud (plain text comments don't support bold/code).

    The comment includes a machine-readable tag so Orion can avoid duplicate
    alerts in the future (check for existing comments containing the tag).

    Args:
        issue_key: Jira issue key (e.g. 'SCRUM-1').
        status: Traceability status ('Partial' or 'Drifted').
        risk_score: Combined risk score from the hybrid engine.
        test_function_name: Name of the linked test function.
        audit_summary: Phase 7 verbalized audit explanation (optional).
        semantic_score: Semantic similarity score (optional).
        structural_score: Structural match score (optional).

    Raises:
        httpx.HTTPStatusError: On non-2xx response.
        ValueError: If Jira credentials are not configured.
    """
    url = f"{_base_url()}/issue/{issue_key}/comment"

    # Build a readable text body
    status_emoji = "⚠️" if status == "Partial" else "❌"
    score_parts = [f"Risk: **{risk_score:.3f}**"]
    if semantic_score is not None:
        score_parts.append(f"Semantic: {semantic_score:.3f}")
    if structural_score is not None:
        score_parts.append(f"Structural: {structural_score:.3f}")
    scores_text = " | ".join(score_parts)

    audit_text = audit_summary or (
        f"Test `{test_function_name}` has diverged from this requirement's constraints."
    )

    # ADF comment body (Jira Cloud)
    adf_comment = {
        "version": 1,
        "type": "doc",
        "content": [
            {
                "type": "paragraph",
                "content": [
                    {"type": "text", "text": f"{status_emoji} Orion Traceability Alert", "marks": [{"type": "strong"}]},
                    {"type": "text", "text": f" — {status}"},
                ],
            },
            {
                "type": "paragraph",
                "content": [
                    {"type": "text", "text": "Linked test: ", "marks": [{"type": "strong"}]},
                    {"type": "text", "text": test_function_name, "marks": [{"type": "code"}]},
                ],
            },
            {
                "type": "paragraph",
                "content": [{"type": "text", "text": scores_text}],
            },
            {
                "type": "paragraph",
                "content": [{"type": "text", "text": audit_text}],
            },
            {
                "type": "paragraph",
                "content": [
                    {
                        "type": "text",
                        "text": f"[{_DRIFT_COMMENT_TAG}]",
                        "marks": [{"type": "code"}],
                    },
                ],
            },
        ],
    }

    payload = {"body": adf_comment}

    with httpx.Client(timeout=20) as client:
        response = client.post(url, headers=_auth_headers(), json=payload)
        response.raise_for_status()

    logger.info(
        "Posted drift comment to %s (status=%s, risk=%.3f)",
        issue_key, status, risk_score,
    )


def has_recent_drift_comment(issue_key: str) -> bool:
    """Check if Orion has already posted a drift alert comment on this issue.

    Returns True if the latest comment contains the Orion machine tag,
    preventing duplicate spam comments on unchanged drift.

    Args:
        issue_key: Jira issue key.

    Returns:
        True if a recent Orion drift comment exists, False otherwise.
    """
    try:
        url = f"{_base_url()}/issue/{issue_key}/comment"
        params = {"maxResults": 5, "orderBy": "-created"}
        with httpx.Client(timeout=15) as client:
            response = client.get(url, headers=_auth_headers(), params=params)
            response.raise_for_status()

        data = response.json()
        comments = data.get("comments", [])

        for comment in reversed(comments):  # most recent last
            body = comment.get("body", {})
            # Convert ADF body to text to check for our tag
            body_text = adf_to_text(body) if isinstance(body, dict) else str(body)
            if _DRIFT_COMMENT_TAG in body_text:
                return True

    except Exception:
        logger.warning("Could not check existing comments on %s", issue_key, exc_info=True)

    return False
