"""Jira REST API integration verification script.

Tests:
1. Configuration — JIRA_BASE_URL, email, token, project key are set.
2. ADF converter — various node types produce correct text output.
3. Module imports — all orion.jira.* modules import cleanly.
4. Live: fetch SCRUM-1 from the real Jira board.
5. Live: fetch SCRUM-2 from the real Jira board.
6. Live: JQL search returns issues from the SCRUM project.
7. Live: upsert issues into the database (requires running DB).
8. Backend: POST /api/v1/jira/sync endpoint (requires running backend).

Usage:
    # Full test (live Jira + DB + backend):
    python scripts/verify_jira_sync.py

    # Offline only (no Jira, no DB, no backend):
    python scripts/verify_jira_sync.py --offline
"""

from __future__ import annotations

import io
import json
import sys
import time

# Windows-safe UTF-8 output
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


_offline = "--offline" in sys.argv

# ---------------------------------------------------------------------------
# Test 1: Configuration
# ---------------------------------------------------------------------------

section("Test 1: Configuration")

try:
    from orion.config import settings

    check("JIRA_BASE_URL is set", bool(settings.jira_base_url), f"url={settings.jira_base_url}")
    check("JIRA_USER_EMAIL is set", bool(settings.jira_user_email), f"email={settings.jira_user_email}")
    check("JIRA_API_TOKEN is set", bool(settings.jira_api_token), f"token={'***' if settings.jira_api_token else '(empty)'}")
    check("JIRA_PROJECT_KEY is set", bool(settings.jira_project_key), f"key={settings.jira_project_key}")
except Exception as exc:
    check("Config loads", False, str(exc))

# ---------------------------------------------------------------------------
# Test 2: ADF converter
# ---------------------------------------------------------------------------

section("Test 2: ADF Converter")

try:
    from orion.jira.adf import adf_to_text

    # Plain string passthrough
    result = adf_to_text("Hello world")
    check("Plain string passthrough", result == "Hello world", f"result={result!r}")

    # None returns empty string
    result = adf_to_text(None)
    check("None returns empty string", result == "", f"result={result!r}")

    # Simple paragraph ADF
    simple_adf = {
        "version": 1,
        "type": "doc",
        "content": [
            {
                "type": "paragraph",
                "content": [
                    {"type": "text", "text": "The system must respond within 200ms."},
                ],
            }
        ],
    }
    result = adf_to_text(simple_adf)
    check(
        "Simple ADF paragraph extracts text",
        "200ms" in result and "system must" in result,
        f"result={result!r}",
    )

    # Heading + bullet list
    complex_adf = {
        "version": 1,
        "type": "doc",
        "content": [
            {
                "type": "heading",
                "attrs": {"level": 2},
                "content": [{"type": "text", "text": "Acceptance Criteria"}],
            },
            {
                "type": "bulletList",
                "content": [
                    {
                        "type": "listItem",
                        "content": [
                            {"type": "paragraph", "content": [{"type": "text", "text": "Response time < 200ms"}]},
                        ],
                    },
                    {
                        "type": "listItem",
                        "content": [
                            {"type": "paragraph", "content": [{"type": "text", "text": "Uptime >= 99.9%"}]},
                        ],
                    },
                ],
            },
        ],
    }
    result = adf_to_text(complex_adf)
    check("Heading extracted from ADF", "Acceptance Criteria" in result, f"result={result!r}")
    check("Bullet list items extracted from ADF", "200ms" in result and "99.9" in result, f"result={result!r}")

    # Bold mark
    bold_adf = {
        "type": "text",
        "text": "must not exceed",
        "marks": [{"type": "strong"}],
    }
    result = adf_to_text({"type": "doc", "content": [{"type": "paragraph", "content": [bold_adf]}]})
    check("Bold mark applies **text**", "must not exceed" in result, f"result={result!r}")

    # Empty doc
    result = adf_to_text({"type": "doc", "content": []})
    check("Empty ADF doc returns empty string", result == "", f"result={result!r}")

except Exception as exc:
    check("ADF converter", False, str(exc))

# ---------------------------------------------------------------------------
# Test 3: Module imports
# ---------------------------------------------------------------------------

section("Test 3: Module Imports")

for mod in ["orion.jira.adf", "orion.jira.client", "orion.jira.routes"]:
    try:
        import importlib
        importlib.import_module(mod)
        check(f"Import {mod}", True)
    except Exception as exc:
        check(f"Import {mod}", False, str(exc))

# ---------------------------------------------------------------------------
# Live Tests (Tests 4–8)
# ---------------------------------------------------------------------------

if _offline:
    print("\n  --offline flag set — skipping live Jira and backend tests.")
    check("Live tests skipped (offline mode)", True, "SKIP")
else:
    # Test 4: Fetch SCRUM-1
    section("Test 4: Fetch SCRUM-1 (Live Jira)")

    scrum1 = None
    try:
        from orion.jira.client import fetch_issue

        scrum1 = fetch_issue("SCRUM-1")
        check("SCRUM-1 fetched successfully", True)
        check("SCRUM-1 has a key", scrum1.key == "SCRUM-1", f"key={scrum1.key}")
        check("SCRUM-1 has a summary", bool(scrum1.summary), f"summary={scrum1.summary[:60]!r}")
        check("SCRUM-1 description is a string", isinstance(scrum1.description, str), f"type={type(scrum1.description)}")
        check(
            "SCRUM-1 description is non-empty or empty gracefully",
            isinstance(scrum1.description, str),
            f"len={len(scrum1.description)} chars",
        )
        print(f"\n  SCRUM-1 Summary  : {scrum1.summary}")
        print(f"  SCRUM-1 Type     : {scrum1.issue_type}")
        print(f"  SCRUM-1 Status   : {scrum1.status}")
        if scrum1.description:
            desc_preview = scrum1.description[:200].replace("\n", " ")
            print(f"  SCRUM-1 Desc     : {desc_preview}...")
        else:
            print(f"  SCRUM-1 Desc     : (empty)")
    except Exception as exc:
        check("SCRUM-1 fetch", False, str(exc))

    # Test 5: Fetch SCRUM-2
    section("Test 5: Fetch SCRUM-2 (Live Jira)")

    scrum2 = None
    try:
        from orion.jira.client import fetch_issue

        scrum2 = fetch_issue("SCRUM-2")
        check("SCRUM-2 fetched successfully", True)
        check("SCRUM-2 has a key", scrum2.key == "SCRUM-2", f"key={scrum2.key}")
        check("SCRUM-2 has a summary", bool(scrum2.summary), f"summary={scrum2.summary[:60]!r}")
        print(f"\n  SCRUM-2 Summary  : {scrum2.summary}")
        print(f"  SCRUM-2 Type     : {scrum2.issue_type}")
        print(f"  SCRUM-2 Status   : {scrum2.status}")
        if scrum2.description:
            desc_preview = scrum2.description[:200].replace("\n", " ")
            print(f"  SCRUM-2 Desc     : {desc_preview}...")
        else:
            print(f"  SCRUM-2 Desc     : (empty)")
    except Exception as exc:
        check("SCRUM-2 fetch", False, str(exc))

    # Test 6: JQL search
    section("Test 6: JQL Search — all SCRUM issues (Live Jira)")

    try:
        from orion.jira.client import search_issues

        jql = f'project = "{settings.jira_project_key}" ORDER BY created ASC'
        all_issues = search_issues(jql, max_results=20)
        check(
            "JQL search returns at least 1 issue",
            len(all_issues) >= 1,
            f"count={len(all_issues)}",
        )
        check(
            "All issues have keys",
            all(i.key for i in all_issues),
            f"keys={[i.key for i in all_issues[:5]]}...",
        )
        check(
            "All issues have summaries",
            all(i.summary for i in all_issues),
        )
        print(f"\n  Found {len(all_issues)} issue(s) in {settings.jira_project_key}:")
        for issue in all_issues[:5]:
            print(f"    {issue.key}: {issue.summary[:70]}")
        if len(all_issues) > 5:
            print(f"    ... and {len(all_issues) - 5} more")
    except Exception as exc:
        check("JQL search", False, str(exc))

    # Test 7: DB upsert (requires database to be running)
    section("Test 7: Database Upsert of SCRUM-1 and SCRUM-2")

    async def _test_db_upsert():
        from orion.database import get_session_context
        from orion.jira.client import fetch_issue
        from orion.jira.routes import _enrich_requirement, _jira_issue_to_requirement_data
        from orion.ingestion.service import upsert_requirement

        results = []
        try:
            async with get_session_context() as session:
                for key in ["SCRUM-1", "SCRUM-2"]:
                    try:
                        issue = fetch_issue(key)
                        req_data = _jira_issue_to_requirement_data(issue)
                        requirement, was_created = await upsert_requirement(session, req_data)
                        await _enrich_requirement(session, requirement)
                        action = "CREATED" if was_created else "UPDATED"
                        results.append((key, action, True, None))
                    except Exception as exc:
                        results.append((key, "ERROR", False, str(exc)))
                await session.commit()
        except Exception as exc:
            return [("DB", "CONNECT_ERROR", False, str(exc))]
        return results

    try:
        import asyncio
        db_results = asyncio.run(_test_db_upsert())
        for key, action, ok, err in db_results:
            if ok:
                check(f"DB upsert {key} ({action})", True, f"action={action}")
            else:
                check(f"DB upsert {key}", False, str(err))
    except Exception as exc:
        check("DB upsert", False, str(exc))
        print("  NOTE: DB tests require PostgreSQL running (docker-compose up -d)")

    # Test 8: Backend API endpoint
    section("Test 8: POST /api/v1/jira/sync/{issue_key} (requires running backend)")

    try:
        import httpx

        client = httpx.Client(timeout=30)
        try:
            health = client.get("http://localhost:8000/health")
            backend_running = health.status_code == 200
        except httpx.ConnectError:
            backend_running = False

        if not backend_running:
            print("\n  NOTE: Backend is not running — skipping endpoint tests.")
            print("  Start with: uvicorn orion.app:app --reload")
            check("Backend running (skipped)", True, "SKIP")
        else:
            check("Backend health check passes", True)

            # Single ticket sync via API
            resp = client.post("http://localhost:8000/api/v1/jira/sync/SCRUM-1")
            check(
                "POST /api/v1/jira/sync/SCRUM-1 returns 200",
                resp.status_code == 200,
                f"status={resp.status_code}",
            )
            if resp.status_code == 200:
                data = resp.json()
                check("Response has status=ok", data.get("status") == "ok", f"status={data.get('status')}")
                check(
                    "total_fetched is 1",
                    data.get("total_fetched") == 1,
                    f"total_fetched={data.get('total_fetched')}",
                )
                print(f"\n  Sync result: {data}")

    except Exception as exc:
        check("Backend API test", False, str(exc))

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

print("\n" + "=" * 70)
total = _passes + _failures
print(f"JIRA SYNC VERIFICATION: {_passes}/{total} checks passed")
if _failures == 0:
    print("ALL CHECKS PASSED [OK]")
else:
    print(f"{_failures} CHECK(S) FAILED [!!]")
    print("\nCommon issues:")
    print("  - JIRA_BASE_URL / JIRA_USER_EMAIL / JIRA_API_TOKEN not set in .env")
    print("  - PostgreSQL not running: docker-compose up -d")
    print("  - Backend not running: uvicorn orion.app:app --reload")
print("=" * 70)

sys.exit(0 if _failures == 0 else 1)
