"""GitHub REST API client — PR file fetching and Check Run management.

Phase 9 client responsibilities:
1. Fetch the list of files changed in a Pull Request.
2. Fetch raw file content (base64-decoded blob) from the repository.
3. Create a Check Run (status=in_progress) at the start of analysis.
4. Complete the Check Run with conclusion + markdown summary when done.

All functions accept an explicit `token` parameter so the caller controls
when to refresh via auth.get_installation_token().

References:
    https://docs.github.com/en/rest/pulls/pulls#list-pull-requests-files
    https://docs.github.com/en/rest/repos/contents#get-repository-content
    https://docs.github.com/en/rest/checks/runs
"""

from __future__ import annotations

import base64
import logging
import re

import httpx

logger = logging.getLogger(__name__)

_GITHUB_API_BASE = "https://api.github.com"
_CHECK_RUN_NAME = "Orion Traceability"

# Patterns matching typical Python test file names
_TEST_FILE_PATTERNS = [
    re.compile(r"(^|/)test_[^/]+\.py$"),
    re.compile(r"(^|/)[^/]+_test\.py$"),
]


def _auth_headers(token: str) -> dict[str, str]:
    """Return standard GitHub API auth headers."""
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def _is_test_file(filename: str) -> bool:
    """Return True if the filename looks like a Python test file."""
    return any(p.search(filename) for p in _TEST_FILE_PATTERNS)


# ---------------------------------------------------------------------------
# PR File Listing
# ---------------------------------------------------------------------------

def fetch_pr_files(
    owner: str,
    repo: str,
    pull_number: int,
    token: str,
) -> list[dict]:
    """Return a list of changed test files in a Pull Request.

    Only returns files whose filename matches Python test naming conventions
    (`test_*.py` or `*_test.py`) and whose status is not `removed`.

    Args:
        owner: Repository owner login (user or org).
        repo: Repository name.
        pull_number: PR number.
        token: GitHub Installation Access Token.

    Returns:
        List of dicts, each with keys: ``filename``, ``status``, ``sha``,
        ``blob_url``, ``raw_url``, ``contents_url``.

    Raises:
        httpx.HTTPStatusError: On non-2xx response.
    """
    url = f"{_GITHUB_API_BASE}/repos/{owner}/{repo}/pulls/{pull_number}/files"
    params = {"per_page": 100}
    test_files: list[dict] = []

    with httpx.Client(timeout=20) as client:
        # Handle pagination (PRs can have many files)
        while url:
            response = client.get(url, headers=_auth_headers(token), params=params)
            response.raise_for_status()
            files = response.json()

            for f in files:
                filename = f.get("filename", "")
                status = f.get("status", "")
                if status != "removed" and _is_test_file(filename):
                    test_files.append(f)
                    logger.debug("Found test file in PR: %s (status=%s)", filename, status)

            # Follow 'next' link for pagination
            link_header = response.headers.get("Link", "")
            next_url = None
            for part in link_header.split(","):
                if 'rel="next"' in part:
                    match = re.search(r"<([^>]+)>", part)
                    if match:
                        next_url = match.group(1)
            url = next_url
            params = {}  # params already encoded in next_url

    logger.info(
        "PR #%d in %s/%s: %d test file(s) changed",
        pull_number, owner, repo, len(test_files),
    )
    return test_files


# ---------------------------------------------------------------------------
# File Content Fetching
# ---------------------------------------------------------------------------

def fetch_file_content(
    owner: str,
    repo: str,
    path: str,
    ref: str,
    token: str,
) -> str:
    """Fetch and decode the raw content of a file at a specific commit/ref.

    Args:
        owner: Repository owner login.
        repo: Repository name.
        path: File path within the repository.
        ref: Commit SHA or branch name.
        token: GitHub Installation Access Token.

    Returns:
        Decoded UTF-8 string content of the file.

    Raises:
        httpx.HTTPStatusError: On non-2xx response.
        UnicodeDecodeError: If the file is not UTF-8 text.
    """
    url = f"{_GITHUB_API_BASE}/repos/{owner}/{repo}/contents/{path}"
    params = {"ref": ref}

    with httpx.Client(timeout=20) as client:
        response = client.get(url, headers=_auth_headers(token), params=params)
        response.raise_for_status()

    data = response.json()
    encoding = data.get("encoding", "base64")
    content_b64 = data.get("content", "")

    if encoding == "base64":
        raw_bytes = base64.b64decode(content_b64)
        return raw_bytes.decode("utf-8", errors="replace")

    # Fallback — content might already be plain text in some edge cases
    return content_b64


# ---------------------------------------------------------------------------
# Check Run Management
# ---------------------------------------------------------------------------

def create_check_run(
    owner: str,
    repo: str,
    head_sha: str,
    token: str,
) -> int:
    """Create a new Check Run with status=in_progress.

    Should be called immediately after receiving the webhook, so GitHub shows
    a spinner on the PR while Orion is analyzing.

    Args:
        owner: Repository owner login.
        repo: Repository name.
        head_sha: The commit SHA the Check Run is reported against.
        token: GitHub Installation Access Token.

    Returns:
        The Check Run ID (used to update/complete later).

    Raises:
        httpx.HTTPStatusError: On non-2xx response.
    """
    url = f"{_GITHUB_API_BASE}/repos/{owner}/{repo}/check-runs"
    payload = {
        "name": _CHECK_RUN_NAME,
        "head_sha": head_sha,
        "status": "in_progress",
        "output": {
            "title": "Orion Traceability Analysis — Running…",
            "summary": "Analysing requirement-test traceability. This will complete shortly.",
        },
    }

    with httpx.Client(timeout=20) as client:
        response = client.post(url, headers=_auth_headers(token), json=payload)
        response.raise_for_status()

    check_run_id: int = response.json()["id"]
    logger.info(
        "Created Check Run #%d for %s/%s @ %s",
        check_run_id, owner, repo, head_sha[:8],
    )
    return check_run_id


def complete_check_run(
    owner: str,
    repo: str,
    check_run_id: int,
    conclusion: str,
    title: str,
    summary: str,
    token: str,
) -> None:
    """Mark a Check Run as completed with a conclusion and markdown summary.

    Args:
        owner: Repository owner login.
        repo: Repository name.
        check_run_id: ID returned by create_check_run().
        conclusion: One of ``success``, ``neutral``, ``failure``, ``skipped``.
        title: Short title shown in the GitHub Checks UI.
        summary: Markdown body shown when the check is expanded.
        token: GitHub Installation Access Token.

    Raises:
        httpx.HTTPStatusError: On non-2xx response.
    """
    url = f"{_GITHUB_API_BASE}/repos/{owner}/{repo}/check-runs/{check_run_id}"
    payload = {
        "status": "completed",
        "conclusion": conclusion,
        "output": {
            "title": title,
            "summary": summary,
        },
    }

    with httpx.Client(timeout=20) as client:
        response = client.patch(url, headers=_auth_headers(token), json=payload)
        response.raise_for_status()

    logger.info(
        "Completed Check Run #%d with conclusion=%s",
        check_run_id, conclusion,
    )


def fail_check_run(
    owner: str,
    repo: str,
    check_run_id: int,
    error_message: str,
    token: str,
) -> None:
    """Mark a Check Run as failed with an error message.

    Used when an unexpected exception prevents Orion from completing analysis.

    Args:
        owner: Repository owner login.
        repo: Repository name.
        check_run_id: ID returned by create_check_run().
        error_message: Human-readable error message.
        token: GitHub Installation Access Token.
    """
    try:
        complete_check_run(
            owner=owner,
            repo=repo,
            check_run_id=check_run_id,
            conclusion="failure",
            title="Orion Traceability — Error",
            summary=f"⚠️ Analysis failed with an internal error:\n\n```\n{error_message}\n```",
            token=token,
        )
    except Exception:
        logger.exception(
            "Failed to mark Check Run #%d as failed — error was: %s",
            check_run_id, error_message,
        )


# ---------------------------------------------------------------------------
# Markdown Summary Builder
# ---------------------------------------------------------------------------

_STATUS_EMOJI = {
    "Covered": "✅",
    "Partial": "⚠️",
    "Drifted": "❌",
}

_CONCLUSION_MAP = {
    "Covered": "success",
    "Partial": "neutral",
    "Drifted": "failure",
}


def build_check_summary(results: list[dict]) -> tuple[str, str, str]:
    """Build the Check Run title, markdown summary, and GitHub conclusion.

    Args:
        results: List of dicts, each with keys:
            ``req_id``, ``req_title``, ``test_fn``, ``file_path``,
            ``status``, ``risk_score``, ``semantic_score``,
            ``structural_score``, ``audit_summary`` (optional).

    Returns:
        Tuple of (conclusion, title, markdown_summary).
        - conclusion: "success" | "neutral" | "failure"
        - title: Short single-line summary.
        - markdown_summary: Full markdown body for the Check Run.
    """
    if not results:
        return (
            "neutral",
            "Orion Traceability — No test files with @traces found",
            (
                "No test files containing `@traces(\"REQ-xxx\")` decorators were found "
                "in this pull request. Orion could not analyse traceability.\n\n"
                "Add `@traces(\"REQ-xxx\")` decorators to your test functions to link "
                "them to requirements."
            ),
        )

    # Determine worst-case overall conclusion
    statuses = [r["status"] for r in results]
    if "Drifted" in statuses:
        overall_status = "Drifted"
    elif "Partial" in statuses:
        overall_status = "Partial"
    else:
        overall_status = "Covered"

    conclusion = _CONCLUSION_MAP[overall_status]
    emoji = _STATUS_EMOJI[overall_status]

    covered = sum(1 for s in statuses if s == "Covered")
    partial = sum(1 for s in statuses if s == "Partial")
    drifted = sum(1 for s in statuses if s == "Drifted")
    total = len(results)

    title = (
        f"{emoji} Orion Traceability — {overall_status} "
        f"({covered}/{total} Covered, {partial} Partial, {drifted} Drifted)"
    )

    # Build markdown summary table
    rows = ["| Requirement | Test Function | Status | Risk | Semantic | Structural |",
            "|---|---|:---:|:---:|:---:|:---:|"]
    for r in results:
        status_emoji = _STATUS_EMOJI.get(r["status"], "❓")
        rows.append(
            f"| `{r['req_id']}` {r['req_title']} "
            f"| `{r['test_fn']}` "
            f"| {status_emoji} {r['status']} "
            f"| {r['risk_score']:.3f} "
            f"| {r['semantic_score']:.3f} "
            f"| {r['structural_score']:.3f} |"
        )

    table = "\n".join(rows)

    # Audit summaries for Partial/Drifted
    audit_lines: list[str] = []
    for r in results:
        if r["status"] in ("Partial", "Drifted") and r.get("audit_summary"):
            audit_lines.append(
                f"**`{r['req_id']}`** ({r['status']}): {r['audit_summary']}"
            )

    audit_section = ""
    if audit_lines:
        audit_section = "\n\n### Audit Details\n\n" + "\n\n".join(audit_lines)

    summary = (
        f"## Orion Requirements Traceability Analysis\n\n"
        f"{table}"
        f"{audit_section}\n\n"
        f"---\n_Powered by [Orion](https://github.com) — "
        f"Hybrid engine: `risk = 0.6 × semantic + 0.4 × structural`_"
    )

    return conclusion, title, summary
