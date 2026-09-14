"""Phase 6 verification script — Requirement-Diff Tracking.

Tests that the delta parser correctly identifies:
1. Changed thresholds (e.g. 200ms → 150ms)
2. Added conditions (new constraints in updated text)
3. Removed conditions (constraints removed from updated text)
4. Changed literals (text-level changes)
5. Non-content fields are ignored (status, assignee, etc.)
6. Delta serialization to JSON for JSONB storage

Usage:
    python scripts/verify_phase6.py
"""

from __future__ import annotations

import json
import sys

from orion.analysis.delta_parser import parse_changelog_to_delta

# ---------------------------------------------------------------------------
# Test scenarios
# ---------------------------------------------------------------------------

SCENARIOS = [
    {
        "name": "Threshold value change (200ms → 150ms)",
        "old_desc": "The API endpoint must return a response within 200 milliseconds under normal load.",
        "new_desc": "The API endpoint must return a response within 150 milliseconds under normal load.",
        "changelog": [
            {
                "field": "description",
                "from": "The API endpoint must return a response within 200 milliseconds under normal load.",
                "to": "The API endpoint must return a response within 150 milliseconds under normal load.",
            }
        ],
        "expected_types": {"changed_threshold"},
        "check_fn": lambda delta: any(
            c.type == "changed_threshold"
            and "200" in str(c.old_value)
            and "150" in str(c.new_value)
            for c in delta.changes
        ),
        "check_label": "Delta captures 200 → 150 threshold change",
    },
    {
        "name": "Condition added (new constraint)",
        "old_desc": "The system must handle at least 500 concurrent users.",
        "new_desc": "The system must handle at least 500 concurrent users. Response time must be less than 100 milliseconds.",
        "changelog": [
            {
                "field": "description",
                "from": "The system must handle at least 500 concurrent users.",
                "to": "The system must handle at least 500 concurrent users. Response time must be less than 100 milliseconds.",
            }
        ],
        "expected_types": {"added_condition"},
        "check_fn": lambda delta: any(
            c.type == "added_condition"
            for c in delta.changes
        ),
        "check_label": "Delta detects added constraint",
    },
    {
        "name": "Condition removed",
        "old_desc": "The API error rate must not exceed 0.1 percent. All requests must be logged.",
        "new_desc": "All requests must be logged.",
        "changelog": [
            {
                "field": "description",
                "from": "The API error rate must not exceed 0.1 percent. All requests must be logged.",
                "to": "All requests must be logged.",
            }
        ],
        "expected_types": {"removed_condition"},
        "check_fn": lambda delta: any(
            c.type == "removed_condition"
            for c in delta.changes
        ),
        "check_label": "Delta detects removed constraint",
    },
    {
        "name": "Operator change (less than → at most)",
        "old_desc": "Latency must be less than 300 milliseconds.",
        "new_desc": "Latency must be at most 300 milliseconds.",
        "changelog": [
            {
                "field": "description",
                "from": "Latency must be less than 300 milliseconds.",
                "to": "Latency must be at most 300 milliseconds.",
            }
        ],
        # The constraint key uses subject+operator, so changing the operator
        # means old key != new key → shows as removed + added
        "expected_types": {"removed_condition", "added_condition"},
        "check_fn": lambda delta: len(delta.changes) >= 2,
        "check_label": "Operator change detected as removed + added constraint pair",
    },
    {
        "name": "Summary field change (via changelog)",
        "old_desc": "The system must perform daily backups.",
        "new_desc": "The system must perform daily backups.",
        "changelog": [
            {
                "field": "summary",
                "from": "Database Backup SLA",
                "to": "Database Backup SLA (Updated)",
            }
        ],
        "expected_types": {"changed_literal"},
        "check_fn": lambda delta: any(
            c.type == "changed_literal" and c.field == "summary"
            for c in delta.changes
        ),
        "check_label": "Summary change captured as changed_literal",
    },
    {
        "name": "Non-content fields ignored (status, assignee)",
        "old_desc": "The cache hit rate must be at least 95 percent.",
        "new_desc": "The cache hit rate must be at least 95 percent.",
        "changelog": [
            {"field": "status", "from": "Open", "to": "In Progress"},
            {"field": "assignee", "from": "alice", "to": "bob"},
            {"field": "priority", "from": "Medium", "to": "High"},
        ],
        "expected_types": set(),
        "check_fn": lambda delta: len(delta.changes) == 0,
        "check_label": "No changes detected for non-content fields",
    },
    {
        "name": "Multiple threshold changes in one update",
        "old_desc": "Response time must be less than 200 milliseconds. Throughput must be at least 1000 requests per second.",
        "new_desc": "Response time must be less than 100 milliseconds. Throughput must be at least 2000 requests per second.",
        "changelog": [
            {
                "field": "description",
                "from": "Response time must be less than 200 milliseconds. Throughput must be at least 1000 requests per second.",
                "to": "Response time must be less than 100 milliseconds. Throughput must be at least 2000 requests per second.",
            }
        ],
        "expected_types": {"changed_threshold"},
        "check_fn": lambda delta: sum(
            1 for c in delta.changes if c.type == "changed_threshold"
        ) >= 2,
        "check_label": "Both threshold changes detected in a single update",
    },
    {
        "name": "No changelog (None)",
        "old_desc": "The system must support pagination.",
        "new_desc": "The system must support pagination with at least 50 items per page.",
        "changelog": None,
        "expected_types": {"added_condition"},
        "check_fn": lambda delta: any(
            c.type == "added_condition"
            for c in delta.changes
        ),
        "check_label": "Constraint diff works even without Jira changelog items",
    },
]


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
    print("PHASE 6 -- REQUIREMENT-DIFF TRACKING VERIFICATION")
    print("=" * 70)

    # === Run each scenario ===
    for i, scenario in enumerate(SCENARIOS, 1):
        print(f"\n--- Scenario {i}: {scenario['name']} ---")

        delta = parse_changelog_to_delta(
            changelog_items=scenario["changelog"],
            old_description=scenario["old_desc"],
            new_description=scenario["new_desc"],
        )

        # Print what we got
        print(f"  Changes detected: {len(delta.changes)}")
        for c in delta.changes:
            print(f"    [{c.type}] {c.details}")

        # Check expected change types
        actual_types = set(c.type for c in delta.changes)
        expected_types = scenario["expected_types"]

        if expected_types:
            type_check = expected_types.issubset(actual_types)
            all_ok &= check(
                f"Expected types {expected_types} present",
                type_check,
                f"actual={actual_types}",
            )
        else:
            type_check = len(delta.changes) == 0
            all_ok &= check(
                "No changes expected and none detected",
                type_check,
                f"actual_count={len(delta.changes)}",
            )

        # Run the scenario-specific check
        all_ok &= check(
            scenario["check_label"],
            scenario["check_fn"](delta),
        )

    # === Serialization check ===
    print("\n--- Serialization Check ---")
    test_delta = parse_changelog_to_delta(
        changelog_items=[{
            "field": "description",
            "from": "Response time must be less than 200 ms.",
            "to": "Response time must be less than 100 ms.",
        }],
        old_description="Response time must be less than 200 ms.",
        new_description="Response time must be less than 100 ms.",
    )
    delta_dict = test_delta.to_dict()

    # Verify it's JSON-serializable (required for JSONB storage)
    try:
        json_str = json.dumps(delta_dict, indent=2)
        all_ok &= check(
            "Delta serializes to valid JSON",
            True,
            f"{len(json_str)} bytes",
        )
        print(f"\n  Serialized delta:\n{json_str}")
    except (TypeError, ValueError) as e:
        all_ok &= check("Delta serializes to valid JSON", False, str(e))

    # Verify expected keys
    all_ok &= check(
        "Delta dict has required keys",
        all(k in delta_dict for k in ("changes", "changed_at", "change_count", "change_types")),
        f"keys={list(delta_dict.keys())}",
    )

    # === Timestamp check ===
    print("\n--- Timestamp Check ---")
    all_ok &= check(
        "changed_at is a non-empty ISO timestamp",
        bool(test_delta.changed_at) and "T" in test_delta.changed_at,
        f"changed_at={test_delta.changed_at}",
    )

    # === Summary ===
    print("\n" + "=" * 70)
    if all_ok:
        print("All Phase 6 verification checks PASSED!")
        print("Requirement-diff tracking is working correctly. Ready for Phase 7.")
    else:
        print("Some checks FAILED -- review output above.")
    print("=" * 70)
    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
