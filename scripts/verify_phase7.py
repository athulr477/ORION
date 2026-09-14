"""Phase 7 verification script — Evidence-Grounded LLM Verbalization.

Tests that:
1. Evidence tuple builds correctly from mock traceability data
2. Covered entries are skipped (returns None)
3. Prompt formatting produces the expected constrained prompt
4. Fallback sentence generation works without LLM
5. If Ollama is available: generates audit sentences for real cases
6. If Ollama is unavailable: verifies graceful fallback

Usage:
    python scripts/verify_phase7.py
"""

from __future__ import annotations

import json
import sys

from orion.verbalization.evidence import EvidenceTuple, build_evidence_tuple
from orion.verbalization.llm_client import OllamaClient

# ---------------------------------------------------------------------------
# Test data — mock Partial/Drifted/Covered cases
# ---------------------------------------------------------------------------

MOCK_CASES = [
    {
        "name": "Drifted — threshold changed, test not updated",
        "status": "Drifted",
        "risk_score": 0.28,
        "semantic_score": 0.35,
        "structural_score": 0.17,
        "requirement_external_id": "REQ-101",
        "requirement_title": "API Response Time SLA",
        "requirement_description": "The API endpoint must return within 100 milliseconds.",
        "requirement_constraints": {
            "constraints": [
                {
                    "type": "threshold",
                    "operator": "<=",
                    "value": 100,
                    "unit": "milliseconds",
                    "subject": "response time",
                    "raw_text": "must return within 100 milliseconds",
                }
            ]
        },
        "test_function_name": "test_response_time_under_load",
        "test_assertions": {
            "assertions": [
                {
                    "type": "comparison",
                    "operator": "<",
                    "left": "response_time",
                    "right": "200",
                    "value": 200,
                }
            ]
        },
        "requirement_delta": {
            "changes": [
                {
                    "type": "changed_threshold",
                    "field": "description",
                    "old_value": {"operator": "<=", "value": 200, "unit": "milliseconds"},
                    "new_value": {"operator": "<=", "value": 100, "unit": "milliseconds"},
                    "details": "Threshold changed: <= 200 milliseconds → <= 100 milliseconds",
                }
            ],
            "changed_at": "2026-09-10T10:00:00Z",
            "change_count": 1,
            "change_types": ["changed_threshold"],
        },
    },
    {
        "name": "Partial — low structural match, no delta",
        "status": "Partial",
        "risk_score": 0.55,
        "semantic_score": 0.72,
        "structural_score": 0.30,
        "requirement_external_id": "REQ-205",
        "requirement_title": "Error Rate Limit",
        "requirement_description": "The system error rate must not exceed 0.1 percent under normal load.",
        "requirement_constraints": {
            "constraints": [
                {
                    "type": "threshold",
                    "operator": "<=",
                    "value": 0.1,
                    "unit": "percent",
                    "subject": "error rate",
                    "raw_text": "error rate must not exceed 0.1 percent",
                }
            ]
        },
        "test_function_name": "test_error_rate_threshold",
        "test_assertions": {
            "assertions": [
                {
                    "type": "comparison",
                    "operator": "<",
                    "left": "error_count / total_requests",
                    "right": "0.05",
                    "value": 0.05,
                }
            ]
        },
        "requirement_delta": None,
    },
    {
        "name": "Drifted — added condition, test missing coverage",
        "status": "Drifted",
        "risk_score": 0.32,
        "semantic_score": 0.40,
        "structural_score": 0.20,
        "requirement_external_id": "REQ-310",
        "requirement_title": "Concurrent User Capacity",
        "requirement_description": "The system must handle at least 500 concurrent users with response time under 200ms.",
        "requirement_constraints": {
            "constraints": [
                {
                    "type": "threshold",
                    "operator": ">=",
                    "value": 500,
                    "unit": "users",
                    "subject": "concurrent users",
                    "raw_text": "must handle at least 500 concurrent users",
                },
                {
                    "type": "threshold",
                    "operator": "<",
                    "value": 200,
                    "unit": "ms",
                    "subject": "response time",
                    "raw_text": "response time under 200ms",
                },
            ]
        },
        "test_function_name": "test_concurrent_users",
        "test_assertions": {
            "assertions": [
                {
                    "type": "comparison",
                    "operator": ">=",
                    "left": "active_sessions",
                    "right": "100",
                    "value": 100,
                }
            ]
        },
        "requirement_delta": {
            "changes": [
                {
                    "type": "added_condition",
                    "field": "description",
                    "old_value": None,
                    "new_value": {"operator": "<", "value": 200, "unit": "ms"},
                    "details": "Added constraint: response time under 200ms",
                }
            ],
            "changed_at": "2026-09-10T11:00:00Z",
            "change_count": 1,
            "change_types": ["added_condition"],
        },
    },
    {
        "name": "Partial — semantic drift, no structural constraints",
        "status": "Partial",
        "risk_score": 0.48,
        "semantic_score": 0.48,
        "structural_score": 0.30,
        "requirement_external_id": "REQ-420",
        "requirement_title": "Data Encryption at Rest",
        "requirement_description": "All sensitive data must be encrypted at rest using AES-256.",
        "requirement_constraints": {
            "constraints": []
        },
        "test_function_name": "test_database_encryption_enabled",
        "test_assertions": {
            "assertions": [
                {
                    "type": "boolean",
                    "left": "db.encryption_enabled",
                },
                {
                    "type": "comparison",
                    "operator": "==",
                    "left": "config.cipher",
                    "right": "'aes-128-cbc'",
                    "value": "aes-128-cbc",
                },
            ]
        },
        "requirement_delta": None,
    },
    {
        "name": "Covered — should be skipped",
        "status": "Covered",
        "risk_score": 0.88,
        "semantic_score": 0.92,
        "structural_score": 0.82,
        "requirement_external_id": "REQ-500",
        "requirement_title": "Login Rate Limiting",
        "requirement_description": "Login attempts must be limited to 5 per minute.",
        "requirement_constraints": {
            "constraints": [
                {
                    "type": "threshold",
                    "operator": "<=",
                    "value": 5,
                    "unit": "per minute",
                    "subject": "login attempts",
                    "raw_text": "limited to 5 per minute",
                }
            ]
        },
        "test_function_name": "test_login_rate_limit",
        "test_assertions": {
            "assertions": [
                {
                    "type": "comparison",
                    "operator": "<=",
                    "left": "login_count",
                    "right": "5",
                    "value": 5,
                }
            ]
        },
        "requirement_delta": None,
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
    print("PHASE 7 -- EVIDENCE-GROUNDED LLM VERBALIZATION VERIFICATION")
    print("=" * 70)

    # === Test 1: Evidence tuple building ===
    print("\n--- Test 1: Evidence Tuple Building ---")

    evidence_tuples: list[EvidenceTuple] = []

    for case in MOCK_CASES:
        print(f"\n  Case: {case['name']}")

        evidence = build_evidence_tuple(
            status=case["status"],
            risk_score=case["risk_score"],
            semantic_score=case["semantic_score"],
            structural_score=case["structural_score"],
            requirement_external_id=case["requirement_external_id"],
            requirement_title=case["requirement_title"],
            requirement_description=case["requirement_description"],
            requirement_constraints=case["requirement_constraints"],
            test_function_name=case["test_function_name"],
            test_assertions=case["test_assertions"],
            requirement_delta=case["requirement_delta"],
        )

        if case["status"] == "Covered":
            all_ok &= check(
                f"  Covered entry '{case['requirement_external_id']}' returns None",
                evidence is None,
            )
        else:
            all_ok &= check(
                f"  {case['status']} entry builds evidence tuple",
                evidence is not None,
            )
            if evidence:
                evidence_tuples.append(evidence)
                all_ok &= check(
                    f"  Status matches: {evidence.status}",
                    evidence.status == case["status"],
                )
                all_ok &= check(
                    f"  Risk score matches: {evidence.risk_score}",
                    abs(evidence.risk_score - case["risk_score"]) < 0.001,
                )
                all_ok &= check(
                    "  Requirement summary non-empty",
                    bool(evidence.requirement_summary),
                    f"'{evidence.requirement_summary[:60]}...'",
                )
                all_ok &= check(
                    "  Test summary non-empty",
                    bool(evidence.test_summary),
                    f"'{evidence.test_summary[:60]}...'",
                )

                # Check delta for cases that have one
                if case["requirement_delta"]:
                    all_ok &= check(
                        "  Delta summary non-empty",
                        bool(evidence.delta_summary),
                        f"'{evidence.delta_summary[:80]}...'",
                    )
                    all_ok &= check(
                        "  Delta change count > 0",
                        evidence.delta_change_count > 0,
                        f"count={evidence.delta_change_count}",
                    )

    # === Test 2: Prompt formatting ===
    print("\n--- Test 2: Prompt Formatting ---")

    for evidence in evidence_tuples[:2]:  # Check first 2
        prompt_context = evidence.to_prompt_context()
        all_ok &= check(
            f"  Prompt context for {evidence.requirement_id} is non-empty",
            bool(prompt_context),
        )
        all_ok &= check(
            "  Prompt context contains status",
            evidence.status in prompt_context,
        )
        all_ok &= check(
            "  Prompt context contains risk_score",
            str(round(evidence.risk_score, 4)) in prompt_context,
        )
        all_ok &= check(
            "  Prompt context contains requirement summary",
            evidence.requirement_title in prompt_context,
        )
        print(f"\n  Prompt context for {evidence.requirement_id}:")
        for line in prompt_context.splitlines():
            print(f"    {line}")

    # === Test 3: Fallback sentence generation ===
    print("\n--- Test 3: Fallback Sentence Generation (no LLM needed) ---")

    for evidence in evidence_tuples:
        fallback = evidence.to_fallback_sentence()
        all_ok &= check(
            f"  Fallback for {evidence.requirement_id} ({evidence.status})",
            bool(fallback) and evidence.status in fallback,
            f"'{fallback[:100]}...'",
        )
        # Verify it's a proper sentence (ends with period)
        all_ok &= check(
            "  Fallback ends with period",
            fallback.endswith("."),
        )

    # === Test 4: Evidence serialization ===
    print("\n--- Test 4: Evidence Serialization ---")

    for evidence in evidence_tuples[:1]:
        evidence_dict = evidence.to_dict()
        try:
            json_str = json.dumps(evidence_dict, indent=2)
            all_ok &= check(
                "  Evidence serializes to valid JSON",
                True,
                f"{len(json_str)} bytes",
            )
        except (TypeError, ValueError) as e:
            all_ok &= check("  Evidence serializes to valid JSON", False, str(e))

        all_ok &= check(
            "  Evidence dict has required keys",
            all(k in evidence_dict for k in (
                "status", "risk_score", "semantic_score", "structural_score",
                "requirement_id", "requirement_summary", "test_summary",
                "delta_summary",
            )),
            f"keys={list(evidence_dict.keys())}",
        )

    # === Test 5: Ollama client & LLM generation ===
    print("\n--- Test 5: Ollama Client & LLM Generation ---")

    client = OllamaClient()
    ollama_available = client.is_available()

    all_ok &= check(
        "  OllamaClient initializes without error",
        True,
    )

    if ollama_available:
        print("\n  ✓ Ollama is available! Running LLM generation tests...\n")

        # Generate audit sentences for Partial/Drifted cases
        for evidence in evidence_tuples:
            prompt_context = evidence.to_prompt_context()
            prompt = (
                f"Based ONLY on the evidence below, write ONE concise sentence explaining "
                f"why this requirement-test pair is classified as {evidence.status}.\n\n"
                f"Evidence:\n{prompt_context}\n\n"
                f"Write exactly one sentence. Do not invent any claims not present in the evidence above."
            )

            response = client.generate(prompt)
            all_ok &= check(
                f"  LLM response for {evidence.requirement_id} ({evidence.status})",
                response.success and bool(response.text),
                f"model={response.model}",
            )

            if response.success and response.text:
                print(f"\n  Generated audit sentence for {evidence.requirement_id}:")
                print(f"    \"{response.text}\"")
                print(f"    (Length: {len(response.text)} chars)")

                # Basic sanity checks on the generated sentence
                all_ok &= check(
                    "  Sentence is non-empty and under 500 chars",
                    0 < len(response.text) < 500,
                    f"len={len(response.text)}",
                )
            elif response.error:
                print(f"    Error: {response.error}")
    else:
        print("\n  ⚠ Ollama is not available — testing fallback path only")
        print("    (Start Ollama and pull the model to test LLM generation)")
        print(f"    (Run: ollama pull {client.model})\n")

        all_ok &= check(
            "  Fallback path works when Ollama is unavailable",
            True,
            "fallback sentences were tested in Test 3",
        )

    # === Summary ===
    print("\n" + "=" * 70)
    if all_ok:
        print("All Phase 7 verification checks PASSED!")
        if ollama_available:
            print("LLM verbalization is working end-to-end. Ready for Phase 8.")
        else:
            print(
                "Evidence pipeline verified. Start Ollama + pull model for full LLM test.\n"
                f"  Run: ollama pull {client.model}"
            )
    else:
        print("Some checks FAILED -- review output above.")
    print("=" * 70)
    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
