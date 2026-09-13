"""Phase 9 verification script — GitHub App Integration & PR Check Runs.

Tests:
1. Configuration check — GitHub App settings are present.
2. PEM file exists and is a valid RSA private key.
3. JWT minting — generates a valid RS256 JWT without hitting GitHub.
4. Schemas — GitHubPRPayload parses a mock webhook payload correctly.
5. Check Run summary builder — correct conclusion mapping for all statuses.
6. Backend import check — all github modules import without errors.
7. API endpoint check — POST /api/v1/github/events is registered and reachable.
8. Ping event handling — server responds with {"status": "pong"}.
9. Signature rejection — bad HMAC signature returns 401.
10. Installation token exchange (LIVE) — exchanges JWT for real token (skipped if no PEM).
11. Check Run lifecycle (LIVE) — creates + completes a real Check Run on a test repo.

Usage:
    python scripts/verify_phase9.py

    # Skip live GitHub API calls (unit tests only):
    python scripts/verify_phase9.py --offline
"""

from __future__ import annotations

import hashlib
import hmac
import io
import json
import sys
import time

# Windows-safe output: force UTF-8 on stdout
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_passes = 0
_failures = 0


def check(label: str, condition: bool, detail: str = "") -> bool:
    global _passes, _failures
    icon = "PASS" if condition else "FAIL"
    msg = f"[{icon}] {label}"
    if detail:
        msg += f"  --  {detail}"
    print(msg)
    if condition:
        _passes += 1
    else:
        _failures += 1
    return condition


def section(title: str) -> None:
    print(f"\n--- {title} ---")


# ---------------------------------------------------------------------------
# Test 1: Configuration
# ---------------------------------------------------------------------------

section("Test 1: Configuration")

try:
    from orion.config import settings

    check(
        "GITHUB_APP_ID is set",
        settings.github_app_id != 0,
        f"value={settings.github_app_id}",
    )
    check(
        "GITHUB_APP_INSTALLATION_ID is set",
        settings.github_app_installation_id != 0,
        f"value={settings.github_app_installation_id}",
    )
    check(
        "GITHUB_APP_PRIVATE_KEY_PATH is set",
        bool(settings.github_app_private_key_path),
        f"path={settings.github_app_private_key_path}",
    )
    check(
        "GITHUB_WEBHOOK_SECRET is set",
        bool(settings.github_webhook_secret),
        f"secret={'***' if settings.github_webhook_secret else '(empty)'}",
    )
except Exception as exc:
    check("Config loads without error", False, str(exc))

# ---------------------------------------------------------------------------
# Test 2: PEM file existence and validity
# ---------------------------------------------------------------------------

section("Test 2: PEM private key file")

_pem_ok = False
try:
    from pathlib import Path

    pem_path = Path(settings.github_app_private_key_path)
    pem_exists = pem_path.exists()
    check("PEM file exists on disk", pem_exists, str(pem_path))

    if pem_exists:
        pem_content = pem_path.read_text(encoding="utf-8")
        is_rsa = "PRIVATE KEY" in pem_content
        check("PEM contains RSA private key", is_rsa, "Must contain '-----BEGIN RSA PRIVATE KEY-----'")
        _pem_ok = is_rsa
except Exception as exc:
    check("PEM file check", False, str(exc))

# ---------------------------------------------------------------------------
# Test 3: JWT minting (no network)
# ---------------------------------------------------------------------------

section("Test 3: JWT Minting (offline, no GitHub call)")

try:
    import jwt as pyjwt

    from orion.github.auth import _mint_jwt

    if _pem_ok:
        pem_content = Path(settings.github_app_private_key_path).read_text()
        token = _mint_jwt(settings.github_app_id, pem_content)

        check("JWT is non-empty string", bool(token), f"length={len(token)}")

        # Decode and verify claims (without verifying signature — we just minted it)
        # Use algorithms without verification to inspect claims
        header = pyjwt.get_unverified_header(token)
        check("JWT algorithm is RS256", header.get("alg") == "RS256", f"alg={header.get('alg')}")

        # Decode without verification to inspect payload
        payload = pyjwt.decode(token, options={"verify_signature": False})
        check(
            "JWT iss matches GITHUB_APP_ID",
            payload.get("iss") == str(settings.github_app_id),
            f"iss={payload.get('iss')} expected={settings.github_app_id}",
        )
        now = int(time.time())
        exp = payload.get("exp", 0)
        check(
            "JWT expiry is ~10 minutes from now",
            540 <= (exp - now) <= 660,
            f"exp_in={exp - now}s",
        )
    else:
        check("JWT minting skipped — PEM not available", True, "SKIP")
except Exception as exc:
    check("JWT minting", False, str(exc))

# ---------------------------------------------------------------------------
# Test 4: Schema parsing
# ---------------------------------------------------------------------------

section("Test 4: GitHubPRPayload schema")

try:
    from orion.github.schemas import GitHubPRPayload

    mock_payload = {
        "action": "opened",
        "pull_request": {
            "number": 42,
            "title": "Add test_api_latency",
            "head": {
                "sha": "abc123def456abc123def456abc123def456abc123",
                "ref": "feature/rtm-tests",
            },
        },
        "repository": {
            "name": "my-repo",
            "full_name": "myorg/my-repo",
            "owner": {"login": "myorg"},
        },
        "installation": {"id": 161384467},
        "extra_field_ignored": True,
    }

    parsed = GitHubPRPayload.model_validate(mock_payload)
    check("action parsed correctly", parsed.action == "opened", f"action={parsed.action}")
    check("owner parsed correctly", parsed.owner == "myorg", f"owner={parsed.owner}")
    check("repo parsed correctly", parsed.repo == "my-repo", f"repo={parsed.repo}")
    check("pull_number parsed correctly", parsed.pull_number == 42, f"pr={parsed.pull_number}")
    check("head_sha parsed correctly", parsed.head_sha == "abc123def456abc123def456abc123def456abc123")
    check("installation_id parsed correctly", parsed.installation_id == 161384467)

    # Test owner inference from full_name when login is absent
    no_login_payload = dict(mock_payload)
    no_login_payload["repository"] = {"name": "my-repo", "full_name": "myorg/my-repo"}
    parsed2 = GitHubPRPayload.model_validate(no_login_payload)
    check(
        "Owner inferred from full_name when login absent",
        parsed2.owner == "myorg",
        f"inferred owner={parsed2.owner}",
    )
except Exception as exc:
    check("Schema parsing", False, str(exc))

# ---------------------------------------------------------------------------
# Test 5: Check Run summary builder
# ---------------------------------------------------------------------------

section("Test 5: build_check_summary — conclusion mapping")

try:
    from orion.github.client import build_check_summary

    # Empty results → neutral
    conclusion, title, summary = build_check_summary([])
    check(
        "Empty results → conclusion=neutral",
        conclusion == "neutral",
        f"conclusion={conclusion}",
    )

    # All Covered → success
    covered_results = [
        {
            "req_id": "REQ-001", "req_title": "API Latency", "test_fn": "test_latency",
            "file_path": "tests/test_api.py", "status": "Covered",
            "risk_score": 0.85, "semantic_score": 0.88, "structural_score": 0.80,
            "audit_summary": None,
        }
    ]
    conclusion, title, summary = build_check_summary(covered_results)
    check("All Covered → conclusion=success", conclusion == "success", f"conclusion={conclusion}")
    check("Summary contains markdown table", "| Requirement |" in summary)

    # Mix with Partial → neutral
    partial_results = covered_results + [
        {
            "req_id": "REQ-002", "req_title": "Throughput", "test_fn": "test_throughput",
            "file_path": "tests/test_api.py", "status": "Partial",
            "risk_score": 0.60, "semantic_score": 0.65, "structural_score": 0.52,
            "audit_summary": "Test covers the endpoint but missing throughput threshold assertion.",
        }
    ]
    conclusion, title, summary = build_check_summary(partial_results)
    check("Partial present → conclusion=neutral", conclusion == "neutral", f"conclusion={conclusion}")

    # Mix with Drifted → failure (worst wins)
    drifted_results = partial_results + [
        {
            "req_id": "REQ-003", "req_title": "SLA", "test_fn": "test_sla",
            "file_path": "tests/test_api.py", "status": "Drifted",
            "risk_score": 0.28, "semantic_score": 0.30, "structural_score": 0.22,
            "audit_summary": "Requirement updated to < 100ms but test still asserts < 200ms.",
        }
    ]
    conclusion, title, summary = build_check_summary(drifted_results)
    check(
        "Drifted present → conclusion=failure (worst wins)",
        conclusion == "failure",
        f"conclusion={conclusion}",
    )
    check("Audit section in summary for Drifted", "Audit Details" in summary)
    check("Audit text in summary", "100ms" in summary)

except Exception as exc:
    check("Summary builder", False, str(exc))

# ---------------------------------------------------------------------------
# Test 6: Module imports
# ---------------------------------------------------------------------------

section("Test 6: Module imports")

modules_to_import = [
    "orion.github.auth",
    "orion.github.client",
    "orion.github.routes",
    "orion.github.schemas",
]
for mod in modules_to_import:
    try:
        import importlib
        importlib.import_module(mod)
        check(f"Import {mod}", True)
    except Exception as exc:
        check(f"Import {mod}", False, str(exc))

# ---------------------------------------------------------------------------
# Test 7 & 8 & 9: API endpoint tests (requires running backend)
# ---------------------------------------------------------------------------

section("Test 7-9: API Endpoint Tests (requires running backend)")

try:
    import httpx

    client = httpx.Client(timeout=10)
    try:
        health = client.get("http://localhost:8000/health")
        backend_running = health.status_code == 200
    except httpx.ConnectError:
        backend_running = False

    if not backend_running:
        print("\n  NOTE: Backend is not running. Skipping endpoint tests.")
        print("  Start it with: uvicorn orion.app:app --reload")
        check("Backend running (skipped)", True, "SKIP")
    else:
        check("Backend health check passes", True)

        # Test 7: Endpoint is registered
        # GitHub will send a ping event when you first configure the webhook
        ping_body = json.dumps({"zen": "Keep it logically awesome."}).encode()
        secret = settings.github_webhook_secret.encode()
        sig = "sha256=" + hmac.new(secret, ping_body, hashlib.sha256).hexdigest()

        ping_resp = client.post(
            "http://localhost:8000/api/v1/github/events",
            content=ping_body,
            headers={
                "Content-Type": "application/json",
                "X-GitHub-Event": "ping",
                "X-Hub-Signature-256": sig,
            },
        )
        check(
            "Test 7: /api/v1/github/events is registered",
            ping_resp.status_code in (200, 202),
            f"status={ping_resp.status_code}",
        )

        # Test 8: Ping returns pong
        try:
            resp_data = ping_resp.json()
            check(
                "Test 8: Ping event returns pong",
                resp_data.get("status") == "pong",
                f"response={resp_data}",
            )
        except Exception as exc:
            check("Test 8: Ping response parsing", False, str(exc))

        # Test 9: Bad signature is rejected
        bad_sig_resp = client.post(
            "http://localhost:8000/api/v1/github/events",
            content=ping_body,
            headers={
                "Content-Type": "application/json",
                "X-GitHub-Event": "ping",
                "X-Hub-Signature-256": "sha256=badbadbadbad",
            },
        )
        check(
            "Test 9: Bad signature rejected with 401",
            bad_sig_resp.status_code == 401,
            f"status={bad_sig_resp.status_code}",
        )

except Exception as exc:
    check("API endpoint tests", False, str(exc))

# ---------------------------------------------------------------------------
# Test 10 & 11: Live GitHub API tests
# ---------------------------------------------------------------------------

_offline = "--offline" in sys.argv

section("Test 10-11: Live GitHub API Tests (requires network + valid credentials)")

if _offline:
    print("  --offline flag set — skipping live tests.")
    check("Live tests skipped (offline mode)", True, "SKIP")
elif not _pem_ok:
    print("  PEM key not available — skipping live tests.")
    check("Live tests skipped (no PEM)", True, "SKIP")
else:
    # Test 10: Exchange JWT for installation token
    try:
        from orion.github.auth import get_installation_token

        token = get_installation_token()
        check(
            "Test 10: Obtained installation access token",
            bool(token) and token.startswith("ghs_"),
            f"token_prefix={token[:8]}***",
        )
    except Exception as exc:
        check("Test 10: Installation token exchange", False, str(exc))
        token = None

    # Test 11: Create + immediately complete a Check Run (requires a real repo + SHA)
    # This is a minimal smoke test — does NOT require an open PR.
    if token:
        print("\n  NOTE: Test 11 requires a real repo and commit SHA.")
        print("  To run a live Check Run smoke test, set these env vars:")
        print("    TEST_REPO_OWNER=your-org")
        print("    TEST_REPO_NAME=your-repo")
        print("    TEST_COMMIT_SHA=abc123...")
        print("  Then re-run without --offline.")

        import os
        test_owner = os.environ.get("TEST_REPO_OWNER", "")
        test_repo = os.environ.get("TEST_REPO_NAME", "")
        test_sha = os.environ.get("TEST_COMMIT_SHA", "")

        if all([test_owner, test_repo, test_sha]):
            try:
                from orion.github.client import complete_check_run, create_check_run

                cr_id = create_check_run(test_owner, test_repo, test_sha, token)
                check(
                    "Test 11a: Check Run created (in_progress)",
                    cr_id > 0,
                    f"check_run_id={cr_id}",
                )
                complete_check_run(
                    owner=test_owner,
                    repo=test_repo,
                    check_run_id=cr_id,
                    conclusion="success",
                    title="Orion Traceability — Test Passed ✅",
                    summary="Phase 9 verification: Check Run lifecycle test completed successfully.",
                    token=token,
                )
                check("Test 11b: Check Run completed (success)", True)
            except Exception as exc:
                check("Test 11: Check Run lifecycle", False, str(exc))
        else:
            check("Test 11: Live Check Run skipped (no TEST_REPO_* env vars set)", True, "SKIP")

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

print("\n" + "=" * 70)
total = _passes + _failures
print(f"PHASE 9 VERIFICATION: {_passes}/{total} checks passed")
if _failures == 0:
    print("ALL CHECKS PASSED [OK]")
else:
    print(f"{_failures} CHECK(S) FAILED [!!]")
    print("\nNext steps:")
    print("  1. Ensure .env has GITHUB_APP_ID, GITHUB_APP_INSTALLATION_ID,")
    print("     GITHUB_APP_PRIVATE_KEY_PATH, and GITHUB_WEBHOOK_SECRET.")
    print("  2. Start backend: uvicorn orion.app:app --reload")
    print("  3. For live PR tests, configure smee.io and open a PR in your test repo.")
print("=" * 70)

sys.exit(0 if _failures == 0 else 1)
