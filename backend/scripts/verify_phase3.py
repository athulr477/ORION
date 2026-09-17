"""Phase 3 verification script — tests structural extraction (both sides).

Runs against 5 real test code samples and 5 real requirement texts,
then prints the extracted structure for manual inspection.

Usage:
    python scripts/verify_phase3.py
"""

from __future__ import annotations

import json
import sys
import textwrap

from orion.extraction.code_extractor import extract_assertions, extract_assertions_from_file
from orion.extraction.requirement_extractor import extract_constraints

# ---------------------------------------------------------------------------
# Sample test code (5 real-world-like test functions)
# ---------------------------------------------------------------------------

TEST_FILE_1 = textwrap.dedent('''\
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
''')

TEST_CODE_2 = textwrap.dedent('''\
    @traces("REQ-202")
    def test_password_minimum_length(user_service):
        """Password must be at least 8 characters."""
        with pytest.raises(ValueError):
            user_service.set_password("short")
        user_service.set_password("validpass")
        assert len(user_service.current_password) >= 8
''')

TEST_CODE_3 = textwrap.dedent('''\
    @traces("REQ-303")
    def test_cache_hit_rate(cache_service, test_data):
        """Cache hit rate must be at least 95%."""
        for item in test_data:
            cache_service.get(item.key)
        stats = cache_service.get_stats()
        assert stats.hit_rate >= 0.95
        assert stats.miss_rate <= 0.05
        assert stats.total_requests > 0
''')

TEST_CODE_4 = textwrap.dedent('''\
    @traces("REQ-404")
    def test_concurrent_connections(db_pool):
        """Database pool supports up to 100 concurrent connections."""
        assert db_pool.max_connections == 100
        assert db_pool.active_connections <= db_pool.max_connections
        assert db_pool.is_healthy()
''')

TEST_CODE_5_NO_DOCSTRING = textwrap.dedent('''\
    @traces("REQ-505")
    def test_file_upload_size_limit(upload_service):
        max_size_mb = 50
        result = upload_service.upload(large_file)
        assert result.accepted is True
        assert result.file_size_mb <= max_size_mb
        with pytest.raises(FileTooLargeError):
            upload_service.upload(oversized_file)
''')


# ---------------------------------------------------------------------------
# Sample requirement texts (5 real-world-like requirements)
# ---------------------------------------------------------------------------

REQUIREMENTS = [
    {
        "id": "REQ-101",
        "title": "API Response Time",
        "text": (
            "The API endpoint /api/v1/query must return a response "
            "within 200 milliseconds under normal load conditions. "
            "Response time must not exceed 500ms under peak load. "
            "The system must handle at least 1000 requests per second."
        ),
    },
    {
        "id": "REQ-202",
        "title": "Password Policy",
        "text": (
            "User passwords must be at least 8 characters long. "
            "Passwords must not contain the user's username. "
            "The system shall reject passwords shorter than 8 characters "
            "with an appropriate error message."
        ),
    },
    {
        "id": "REQ-303",
        "title": "Cache Performance",
        "text": (
            "The caching layer must maintain a hit rate of at least 95% "
            "under standard workload patterns. Cache miss rate should not "
            "exceed 5%. The cache must support no fewer than 10000 entries."
        ),
    },
    {
        "id": "REQ-404",
        "title": "Database Connection Pool",
        "text": (
            "The database connection pool must support up to 100 concurrent "
            "connections. The pool must be able to handle at least 50 "
            "simultaneous queries. Connection timeout must be less than "
            "5 seconds."
        ),
    },
    {
        "id": "REQ-505",
        "title": "File Upload Limits",
        "text": (
            "The system shall accept file uploads no larger than 50 MB. "
            "Upload processing time must not exceed 30 seconds. "
            "The system must reject files over 50 megabytes with a "
            "413 status code."
        ),
    },
]


# ---------------------------------------------------------------------------
# Pretty printers
# ---------------------------------------------------------------------------


def print_code_result(result, label: str = "") -> None:
    """Print a code extraction result in a readable format."""
    hdr = f"  Function: {result.function_name}"
    if label:
        hdr = f"  [{label}] {hdr}"
    print(hdr)
    print(f"  Docstring: {result.docstring or '(none)'}")
    print(f"  Fallback used: {result.fallback_used}")
    print(f"  Assertions ({len(result.assertions)}):")
    for i, a in enumerate(result.assertions, 1):
        parts = [f"type={a.type}"]
        if a.operator:
            parts.append(f"op={a.operator}")
        if a.left:
            parts.append(f"left={a.left}")
        if a.right:
            parts.append(f"right={a.right}")
        if a.value is not None:
            parts.append(f"value={a.value}")
        if a.function_call:
            parts.append(f"call={a.function_call}")
        if a.exception_type:
            parts.append(f"exception={a.exception_type}")
        print(f"    {i}. {', '.join(parts)}")
    print()


def print_req_result(result, req: dict) -> None:
    """Print a requirement extraction result in a readable format."""
    print(f"  [{req['id']}] {req['title']}")
    print(f"  Constraints ({len(result.constraints)}):")
    for i, c in enumerate(result.constraints, 1):
        parts = [f"type={c.type}"]
        if c.operator:
            parts.append(f"op={c.operator}")
        if c.value is not None:
            parts.append(f"value={c.value}")
        if c.unit:
            parts.append(f"unit={c.unit}")
        if c.subject:
            parts.append(f"subject={c.subject}")
        if c.polarity != "positive":
            parts.append(f"polarity={c.polarity}")
        parts.append(f"raw='{c.raw_text}'")
        print(f"    {i}. {', '.join(parts)}")
    print(f"  Keywords: {', '.join(result.keywords[:15])}...")
    print()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    all_ok = True

    # === CODE-SIDE EXTRACTION ===
    print("=" * 60)
    print("CODE-SIDE EXTRACTION (AST)")
    print("=" * 60)

    # Test file with multiple functions
    print("\n--- Test File 1: Response Time Tests (full file) ---")
    results = extract_assertions_from_file(TEST_FILE_1)
    for r in results:
        print_code_result(r)
    if len(results) < 2:
        print("  [FAIL] Expected at least 2 test functions")
        all_ok = False
    else:
        # Check that comparison assertions were found
        total_assertions = sum(len(r.assertions) for r in results)
        if total_assertions >= 4:
            print(f"  [PASS] Found {total_assertions} assertions across {len(results)} functions")
        else:
            print(f"  [FAIL] Expected >=4 assertions, got {total_assertions}")
            all_ok = False

    # Individual test functions
    test_samples = [
        ("Test 2: Password Policy", TEST_CODE_2, {"raises": True, "comparison": True}),
        ("Test 3: Cache Hit Rate", TEST_CODE_3, {"comparison": True}),
        ("Test 4: Connection Pool", TEST_CODE_4, {"comparison": True, "call": True}),
        ("Test 5: No Docstring (fallback)", TEST_CODE_5_NO_DOCSTRING, {"raises": True}),
    ]

    for label, code, expected in test_samples:
        print(f"\n--- {label} ---")
        result = extract_assertions(code, function_name=label)
        print_code_result(result, label)

        types_found = {a.type for a in result.assertions}
        for exp_type, should_exist in expected.items():
            if should_exist and exp_type not in types_found:
                print(f"  [FAIL] Expected assertion type '{exp_type}' not found")
                all_ok = False
            elif should_exist:
                print(f"  [PASS] Found expected assertion type '{exp_type}'")

    # Test 5 should show no docstring
    result5 = extract_assertions(TEST_CODE_5_NO_DOCSTRING, "test_no_doc")
    if result5.docstring is None:
        print("  [PASS] No docstring detected -- fallback scenario confirmed")
    else:
        print(f"  [FAIL] Expected no docstring, got: {result5.docstring}")
        all_ok = False

    # === REQUIREMENT-SIDE EXTRACTION ===
    print("\n" + "=" * 60)
    print("REQUIREMENT-SIDE EXTRACTION (Rule-based)")
    print("=" * 60)

    for req in REQUIREMENTS:
        print(f"\n--- {req['id']}: {req['title']} ---")
        result = extract_constraints(req["text"], requirement_id=req["id"])
        print_req_result(result, req)

        if len(result.constraints) >= 2:
            print(f"  [PASS] Extracted {len(result.constraints)} constraints")
        else:
            print(f"  [FAIL] Expected >=2 constraints, got {len(result.constraints)}")
            all_ok = False

        if len(result.keywords) >= 3:
            print(f"  [PASS] Extracted {len(result.keywords)} keywords")
        else:
            print(f"  [FAIL] Expected >=3 keywords, got {len(result.keywords)}")
            all_ok = False

    # === SERIALIZATION CHECK ===
    print("\n" + "=" * 60)
    print("SERIALIZATION CHECK (to_dict / JSONB)")
    print("=" * 60)

    code_result = extract_assertions(TEST_CODE_3, "test_cache")
    code_dict = code_result.to_dict()
    print(f"\nCode extraction to_dict:\n{json.dumps(code_dict, indent=2)}")

    req_result = extract_constraints(REQUIREMENTS[2]["text"], "REQ-303")
    req_dict = req_result.to_dict()
    print(f"\nRequirement extraction to_dict:\n{json.dumps(req_dict, indent=2)}")

    try:
        json.dumps(code_dict)
        json.dumps(req_dict)
        print("\n  [PASS] Both results are JSON-serializable (JSONB-ready)")
    except (TypeError, ValueError) as e:
        print(f"\n  [FAIL] Serialization error: {e}")
        all_ok = False

    # === SUMMARY ===
    print("\n" + "=" * 60)
    if all_ok:
        print("All Phase 3 verification checks PASSED!")
    else:
        print("Some checks FAILED -- review output above.")
    print("=" * 60)
    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
