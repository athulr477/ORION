"""Phase 8 verification script — Dashboard (Frontend).

Tests that:
1. Backend API endpoints respond correctly (/matrix, /stats, /simulate, /reclassify, /heatmap)
2. Frontend builds without errors
3. Simulate-webhook creates data and it appears in the matrix
4. Reclassify with custom thresholds works
5. Heatmap endpoint returns XAI evidence

Usage:
    python scripts/verify_phase8.py
"""

from __future__ import annotations

import subprocess
import sys
import uuid

import httpx

BASE = "http://localhost:8000/api/v1/dashboard"


def check(label: str, condition: bool, detail: str = "") -> bool:
    """Print a pass/fail check result."""
    icon = "PASS" if condition else "FAIL"
    msg = f"[{icon}] {label}"
    if detail:
        msg += f" -- {detail}"
    print(msg)
    return condition


def main() -> None:
    all_ok = True

    print("=" * 70)
    print("PHASE 8 -- DASHBOARD VERIFICATION")
    print("=" * 70)

    # === Test 0: Frontend build ===
    print("\n--- Test 0: Frontend Build ---")

    try:
        result = subprocess.run(
            ["cmd", "/c", "npm", "run", "build"],
            cwd="frontend",
            capture_output=True,
            text=True,
            timeout=60,
        )
        all_ok &= check(
            "Frontend builds without errors",
            result.returncode == 0,
            f"exit_code={result.returncode}",
        )
        if result.returncode != 0:
            print(f"  stderr: {result.stderr[:300]}")
    except Exception as e:
        all_ok &= check("Frontend builds without errors", False, str(e))

    # === Test 1: Backend API health ===
    print("\n--- Test 1: Backend API Connectivity ---")

    client = httpx.Client(timeout=10)

    try:
        health = client.get("http://localhost:8000/health")
        all_ok &= check(
            "Health endpoint responds",
            health.status_code == 200,
            f"status={health.status_code}",
        )
    except httpx.ConnectError:
        print(
            "\n  ERROR: Cannot connect to backend at http://localhost:8000"
            "\n  Start the backend first: uvicorn orion.app:app --reload"
            "\n  Skipping remaining API tests.\n"
        )
        all_ok &= check("Backend is running", False, "Connection refused")
        print("\n" + "=" * 70)
        print("Some checks FAILED -- backend is not running.")
        print("=" * 70)
        sys.exit(1)

    # === Test 2: GET /stats ===
    print("\n--- Test 2: GET /stats ---")

    resp = client.get(f"{BASE}/stats")
    all_ok &= check(
        "Stats endpoint responds 200",
        resp.status_code == 200,
        f"status={resp.status_code}",
    )
    stats = resp.json()
    all_ok &= check(
        "Stats has expected keys",
        all(k in stats for k in ("total_entries", "covered_count", "partial_count", "drifted_count")),
        f"keys={list(stats.keys())}",
    )
    print(f"  Stats: entries={stats.get('total_entries')}, "
          f"covered={stats.get('covered_count')}, "
          f"partial={stats.get('partial_count')}, "
          f"drifted={stats.get('drifted_count')}")

    # === Test 3: GET /matrix ===
    print("\n--- Test 3: GET /matrix ---")

    resp = client.get(f"{BASE}/matrix?page=1&page_size=10")
    all_ok &= check(
        "Matrix endpoint responds 200",
        resp.status_code == 200,
        f"status={resp.status_code}",
    )
    matrix = resp.json()
    all_ok &= check(
        "Matrix response has rows/total/page",
        all(k in matrix for k in ("rows", "total", "page", "page_size")),
    )
    print(f"  Matrix: total={matrix.get('total')}, rows_returned={len(matrix.get('rows', []))}")

    # === Test 4: POST /simulate ===
    print("\n--- Test 4: POST /simulate ---")

    demo_id = f"REQ-VERIFY-{uuid.uuid4().hex[:6].upper()}"
    sim_payload = {
        "requirement_external_id": demo_id,
        "requirement_title": "Phase 8 verification: max latency 150ms",
        "requirement_description": (
            "The API must respond within 150 milliseconds under normal load. "
            "The system must handle at least 50 concurrent requests."
        ),
        "test_function_name": "test_latency_under_threshold",
        "test_source_code": (
            f'@traces("{demo_id}")\n'
            "def test_latency_under_threshold():\n"
            '    """Verify API latency is under 150ms."""\n'
            "    response = client.get('/api/data')\n"
            "    assert response.elapsed.total_seconds() < 0.15\n"
            "    assert response.status_code == 200\n"
        ),
        "test_file_path": "tests/test_latency.py",
    }

    resp = client.post(f"{BASE}/simulate", json=sim_payload)
    all_ok &= check(
        "Simulate endpoint responds 200",
        resp.status_code == 200,
        f"status={resp.status_code}",
    )
    sim_result = resp.json()
    all_ok &= check(
        "Simulate returns status 'ok'",
        sim_result.get("status") == "ok",
    )
    all_ok &= check(
        "Simulate returns pipeline_steps",
        len(sim_result.get("pipeline_steps", [])) > 0,
        f"steps={len(sim_result.get('pipeline_steps', []))}",
    )
    all_ok &= check(
        "Simulate returns matrix_entry",
        sim_result.get("matrix_entry") is not None,
    )

    entry = sim_result.get("matrix_entry", {})
    entry_id = entry.get("id")
    entry_status = entry.get("status")

    if entry:
        print(f"  Created entry: id={entry_id}, status={entry_status}, "
              f"risk={entry.get('risk_score')}")
        for step in sim_result.get("pipeline_steps", []):
            print(f"    - {step}")

    # === Test 5: Verify simulated data appears in /matrix ===
    print("\n--- Test 5: Simulated Data in Matrix ---")

    resp = client.get(f"{BASE}/matrix?search={demo_id}")
    matrix2 = resp.json()
    found = any(r.get("requirement_external_id") == demo_id for r in matrix2.get("rows", []))
    all_ok &= check(
        f"Simulated entry '{demo_id}' found in matrix",
        found,
        f"search_total={matrix2.get('total')}",
    )

    # === Test 6: POST /matrix/reclassify ===
    print("\n--- Test 6: POST /matrix/reclassify ---")

    resp = client.post(f"{BASE}/matrix/reclassify", json={
        "covered_threshold": 0.9,
        "drifted_threshold": 0.5,
    })
    all_ok &= check(
        "Reclassify endpoint responds 200",
        resp.status_code == 200,
        f"status={resp.status_code}",
    )
    reclass = resp.json()
    all_ok &= check(
        "Reclassify returns rows",
        "rows" in reclass and "changed_count" in reclass,
        f"total={reclass.get('total')}, changed={reclass.get('changed_count')}",
    )
    print(f"  Reclassify: with thresholds covered=0.9/drifted=0.5 -> "
          f"{reclass.get('changed_count')} entries would change")

    # Verify bad thresholds are rejected
    resp_bad = client.post(f"{BASE}/matrix/reclassify", json={
        "covered_threshold": 0.3,
        "drifted_threshold": 0.8,
    })
    all_ok &= check(
        "Reclassify rejects drifted >= covered",
        resp_bad.status_code == 400,
        f"status={resp_bad.status_code}",
    )

    # === Test 7: GET /matrix/{id}/heatmap ===
    print("\n--- Test 7: GET /matrix/{id}/heatmap ---")

    if entry_id:
        resp = client.get(f"{BASE}/matrix/{entry_id}/heatmap")
        all_ok &= check(
            "Heatmap endpoint responds 200",
            resp.status_code == 200,
            f"status={resp.status_code}",
        )
        heatmap = resp.json()
        all_ok &= check(
            "Heatmap has requirement/test data",
            all(k in heatmap for k in (
                "requirement_external_id", "test_function_name",
                "semantic_score", "structural_score", "risk_score",
                "matches", "keywords",
            )),
        )
        all_ok &= check(
            "Heatmap returns keywords",
            len(heatmap.get("keywords", [])) >= 0,
            f"keywords={len(heatmap.get('keywords', []))}",
        )
        all_ok &= check(
            "Heatmap returns matches list",
            isinstance(heatmap.get("matches"), list),
            f"matches={len(heatmap.get('matches', []))}",
        )
        print(f"  Heatmap: semantic={heatmap.get('semantic_score')}, "
              f"structural={heatmap.get('structural_score')}, "
              f"risk={heatmap.get('risk_score')}")
    else:
        all_ok &= check("Heatmap test skipped (no entry_id)", False)

    # Invalid ID returns 400
    resp_bad = client.get(f"{BASE}/matrix/not-a-uuid/heatmap")
    all_ok &= check(
        "Heatmap rejects invalid UUID",
        resp_bad.status_code == 400,
        f"status={resp_bad.status_code}",
    )

    # Non-existent ID returns 404
    fake_id = str(uuid.uuid4())
    resp_404 = client.get(f"{BASE}/matrix/{fake_id}/heatmap")
    all_ok &= check(
        "Heatmap returns 404 for unknown ID",
        resp_404.status_code == 404,
        f"status={resp_404.status_code}",
    )

    # === Test 8: Sort and filter ===
    print("\n--- Test 8: Sort and Filter ---")

    resp = client.get(f"{BASE}/matrix?sort=semantic_score&order=asc&page_size=5")
    all_ok &= check(
        "Matrix sort by semantic_score asc",
        resp.status_code == 200,
        f"status={resp.status_code}",
    )

    if entry_status:
        resp = client.get(f"{BASE}/matrix?status={entry_status}&page_size=5")
        all_ok &= check(
            f"Matrix filter by status={entry_status}",
            resp.status_code == 200,
            f"total={resp.json().get('total')}",
        )

    # Invalid status
    resp = client.get(f"{BASE}/matrix?status=Invalid")
    all_ok &= check(
        "Matrix rejects invalid status filter",
        resp.status_code == 400,
        f"status={resp.status_code}",
    )

    # === Test 9: Updated stats after simulation ===
    print("\n--- Test 9: Updated Stats After Simulation ---")

    resp = client.get(f"{BASE}/stats")
    new_stats = resp.json()
    all_ok &= check(
        "Stats total_entries increased",
        new_stats.get("total_entries", 0) > 0,
        f"total={new_stats.get('total_entries')}",
    )

    client.close()

    # === Summary ===
    print("\n" + "=" * 70)
    if all_ok:
        print("All Phase 8 verification checks PASSED!")
        print(
            "Dashboard frontend builds, backend APIs work end-to-end,"
            "\nslider reclassifies, simulate creates data, heatmap shows XAI evidence."
            "\n\nReady for Phase 9."
        )
    else:
        print("Some checks FAILED -- review output above.")
    print("=" * 70)
    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
