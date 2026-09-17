"""Phase 2 verification script — tests webhook ingestion endpoints.

Checks:
1. Mock Jira payload → requirement created in DB
2. Mock GitHub push payload with @traces("REQ-123") → test case created & linked
3. Payload with invalid signature → 401 rejection
4. FK link between test_cases.requirement_id and requirements.id

Usage:
    # Start the server first:
    #   python -m uvicorn orion.app:app --port 8000
    # Then run this script:
    #   python scripts/verify_phase2.py
"""

from __future__ import annotations

import hashlib
import hmac
import json
import sys
import textwrap

import httpx

BASE_URL = "http://localhost:8000/api/v1"

# These must match the secrets in .env
JIRA_SECRET = "orion-jira-dev-secret"
GITHUB_SECRET = "orion-github-dev-secret"


def _sign(body: bytes, secret: str) -> str:
    """Compute HMAC-SHA256 and return as 'sha256=<hex>' header value."""
    digest = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


# ---------------------------------------------------------------------------
# Test payloads
# ---------------------------------------------------------------------------

JIRA_PAYLOAD = {
    "webhookEvent": "jira:issue_created",
    "issue": {
        "key": "REQ-101",
        "fields": {
            "summary": "Response time must be less than 200ms",
            "description": (
                "The API endpoint /api/v1/query must return a response "
                "within 200 milliseconds under normal load conditions. "
                "Response time must not exceed 500ms under peak load."
            ),
        },
    },
}

JIRA_UPDATE_PAYLOAD = {
    "webhookEvent": "jira:issue_updated",
    "issue": {
        "key": "REQ-101",
        "fields": {
            "summary": "Response time must be less than 150ms",
            "description": (
                "The API endpoint /api/v1/query must return a response "
                "within 150 milliseconds under normal load conditions. "
                "Response time must not exceed 400ms under peak load."
            ),
        },
    },
    "changelog": {
        "items": [
            {
                "field": "summary",
                "fromString": "Response time must be less than 200ms",
                "toString": "Response time must be less than 150ms",
            },
            {
                "field": "description",
                "fromString": "...within 200 milliseconds...",
                "toString": "...within 150 milliseconds...",
            },
        ]
    },
}

TEST_FILE_CONTENT = textwrap.dedent('''\
    """Tests for API response time requirements."""

    import pytest
    from orion_app.decorators import traces


    @traces("REQ-101")
    def test_response_time_under_normal_load(api_client):
        """Verify response time is under 200ms for normal load."""
        response = api_client.get("/api/v1/query")
        assert response.status_code == 200
        assert response.elapsed.total_seconds() < 0.2


    @traces("REQ-101")
    def test_response_time_under_peak_load(api_client, peak_load):
        """Verify response time is under 500ms for peak load."""
        response = api_client.get("/api/v1/query")
        assert response.status_code == 200
        assert response.elapsed.total_seconds() < 0.5


    def test_untraced_helper():
        """A test without @traces — should be ingested but unlinked."""
        assert True


    @traces("REQ-999")
    def test_nonexistent_requirement():
        """Traces a requirement that doesn't exist yet."""
        assert True
''')

GITHUB_PAYLOAD = {
    "ref": "refs/heads/main",
    "repository_name": "orion-test-repo",
    "test_files": [
        {
            "file_path": "tests/test_response_time.py",
            "content": TEST_FILE_CONTENT,
        }
    ],
}


# ---------------------------------------------------------------------------
# Verification checks
# ---------------------------------------------------------------------------


def check(label: str, condition: bool, detail: str = "") -> bool:
    """Print a pass/fail check result."""
    icon = "PASS" if condition else "FAIL"
    msg = f"[{icon}] {label}"
    if detail:
        msg += f" -- {detail}"
    print(msg)
    return condition


def main() -> None:
    all_passed = True

    with httpx.Client(timeout=30) as client:
        # ----------------------------------------------------------
        # 0. Health check
        # ----------------------------------------------------------
        print("\n=== Health Check ===")
        resp = client.get("http://localhost:8000/health")
        all_passed &= check(
            "Health endpoint",
            resp.status_code == 200 and resp.json().get("status") == "healthy",
            f"status={resp.status_code}",
        )

        # ----------------------------------------------------------
        # 1. Jira webhook — create requirement
        # ----------------------------------------------------------
        print("\n=== Jira Webhook: Create Requirement ===")
        body = json.dumps(JIRA_PAYLOAD).encode()
        sig = _sign(body, JIRA_SECRET)
        resp = client.post(
            f"{BASE_URL}/webhooks/jira",
            content=body,
            headers={
                "Content-Type": "application/json",
                "X-Hub-Signature": sig,
            },
        )
        data = resp.json()
        all_passed &= check(
            "Jira create — status 200", resp.status_code == 200, f"got {resp.status_code}"
        )
        all_passed &= check(
            "Jira create — requirement created",
            data.get("created") == 1,
            f"response: {data}",
        )

        # ----------------------------------------------------------
        # 2. Jira webhook — update requirement
        # ----------------------------------------------------------
        print("\n=== Jira Webhook: Update Requirement ===")
        body = json.dumps(JIRA_UPDATE_PAYLOAD).encode()
        sig = _sign(body, JIRA_SECRET)
        resp = client.post(
            f"{BASE_URL}/webhooks/jira",
            content=body,
            headers={
                "Content-Type": "application/json",
                "X-Hub-Signature": sig,
            },
        )
        data = resp.json()
        all_passed &= check(
            "Jira update — status 200", resp.status_code == 200, f"got {resp.status_code}"
        )
        all_passed &= check(
            "Jira update — requirement updated",
            data.get("updated") == 1,
            f"response: {data}",
        )

        # ----------------------------------------------------------
        # 3. Jira webhook — bad signature → 401
        # ----------------------------------------------------------
        print("\n=== Jira Webhook: Bad Signature ===")
        body = json.dumps(JIRA_PAYLOAD).encode()
        bad_sig = "sha256=0000000000000000000000000000000000000000000000000000000000000000"
        resp = client.post(
            f"{BASE_URL}/webhooks/jira",
            content=body,
            headers={
                "Content-Type": "application/json",
                "X-Hub-Signature": bad_sig,
            },
        )
        all_passed &= check(
            "Bad Jira signature → 401",
            resp.status_code == 401,
            f"got {resp.status_code}",
        )

        # ----------------------------------------------------------
        # 4. Jira webhook — missing signature → 401
        # ----------------------------------------------------------
        print("\n=== Jira Webhook: Missing Signature ===")
        body = json.dumps(JIRA_PAYLOAD).encode()
        resp = client.post(
            f"{BASE_URL}/webhooks/jira",
            content=body,
            headers={"Content-Type": "application/json"},
        )
        all_passed &= check(
            "Missing Jira signature → 401",
            resp.status_code == 401,
            f"got {resp.status_code}",
        )

        # ----------------------------------------------------------
        # 5. GitHub webhook — create test cases with @traces links
        # ----------------------------------------------------------
        print("\n=== GitHub Webhook: Create Test Cases ===")
        body = json.dumps(GITHUB_PAYLOAD).encode()
        sig = _sign(body, GITHUB_SECRET)
        resp = client.post(
            f"{BASE_URL}/webhooks/github",
            content=body,
            headers={
                "Content-Type": "application/json",
                "X-Hub-Signature-256": sig,
            },
        )
        data = resp.json()
        all_passed &= check(
            "GitHub push — status 200",
            resp.status_code == 200,
            f"got {resp.status_code}",
        )
        all_passed &= check(
            "GitHub push — test cases created",
            data.get("created", 0) >= 3,
            f"created={data.get('created')}, response: {data}",
        )
        all_passed &= check(
            "GitHub push — some tests linked to REQ-101",
            data.get("linked", 0) >= 2,
            f"linked={data.get('linked')}",
        )
        all_passed &= check(
            "GitHub push — REQ-999 unlinked (doesn't exist)",
            data.get("unlinked", 0) >= 1,
            f"unlinked={data.get('unlinked')}",
        )

        # ----------------------------------------------------------
        # 6. GitHub webhook — bad signature → 401
        # ----------------------------------------------------------
        print("\n=== GitHub Webhook: Bad Signature ===")
        body = json.dumps(GITHUB_PAYLOAD).encode()
        bad_sig = "sha256=0000000000000000000000000000000000000000000000000000000000000000"
        resp = client.post(
            f"{BASE_URL}/webhooks/github",
            content=body,
            headers={
                "Content-Type": "application/json",
                "X-Hub-Signature-256": bad_sig,
            },
        )
        all_passed &= check(
            "Bad GitHub signature → 401",
            resp.status_code == 401,
            f"got {resp.status_code}",
        )

        # ----------------------------------------------------------
        # 7. Re-send GitHub push — should update, not duplicate
        # ----------------------------------------------------------
        print("\n=== GitHub Webhook: Idempotent Upsert ===")
        body = json.dumps(GITHUB_PAYLOAD).encode()
        sig = _sign(body, GITHUB_SECRET)
        resp = client.post(
            f"{BASE_URL}/webhooks/github",
            content=body,
            headers={
                "Content-Type": "application/json",
                "X-Hub-Signature-256": sig,
            },
        )
        data = resp.json()
        all_passed &= check(
            "Idempotent upsert — updated (not created)",
            data.get("created", -1) == 0 and data.get("updated", 0) >= 3,
            f"created={data.get('created')}, updated={data.get('updated')}",
        )

    # ----------------------------------------------------------
    # Summary
    # ----------------------------------------------------------
    print("\n" + "=" * 50)
    if all_passed:
        print("All Phase 2 verification checks PASSED!")
    else:
        print("Some checks FAILED -- review output above.")
    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
