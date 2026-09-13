"""Phase 4 verification script -- Semantic Vector Engine.

Tests:
1. Embed a requirement and its correctly-linked test -> high semantic_score
2. Embed the same requirement with an unrelated test -> lower score
3. Confirm matched score > unrelated score (meaningfully)
4. Test the docstring-less fallback -> non-degenerate score

Usage:
    python scripts/verify_phase4.py
"""

from __future__ import annotations

import sys
import time

from orion.embedding.engine import cosine_similarity, embed_text, embed_texts, get_embedding_dim
from orion.embedding.text_builder import build_requirement_text, build_test_text


# ---------------------------------------------------------------------------
# Test data
# ---------------------------------------------------------------------------

# Requirement: API response time
REQ_TITLE = "API Response Time"
REQ_TEXT = (
    "The API endpoint /api/v1/query must return a response "
    "within 200 milliseconds under normal load conditions. "
    "Response time must not exceed 500ms under peak load."
)

# Matching test (docstring present)
MATCHING_TEST_DOCSTRING = "Verify response time is under 200ms for normal load."
MATCHING_TEST_NAME = "test_response_time_under_normal_load"

# Unrelated test (docstring present)
UNRELATED_TEST_DOCSTRING = "Verify that user profile picture upload accepts PNG format."
UNRELATED_TEST_NAME = "test_profile_picture_upload_png"

# Test WITHOUT docstring (fallback scenario)
NO_DOC_TEST_NAME = "test_response_time_under_peak_load"
NO_DOC_ASSERTIONS = {
    "function_name": "test_response_time_under_peak_load",
    "assertions": [
        {
            "type": "comparison",
            "operator": "==",
            "left": "response.status_code",
            "right": "200",
            "value": 200,
        },
        {
            "type": "comparison",
            "operator": "<",
            "left": "response.elapsed.total_seconds()",
            "right": "0.5",
            "value": 0.5,
            "function_call": "*.total_seconds",
        },
    ],
    "docstring": None,
    "fallback_used": True,
}

# Second unrelated requirement for cross-check
UNRELATED_REQ_TITLE = "User Authentication"
UNRELATED_REQ_TEXT = (
    "The system must support multi-factor authentication using TOTP. "
    "Users must be locked out after 5 failed login attempts."
)


# ---------------------------------------------------------------------------
# Checks
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
    all_ok = True

    # === 1. Embedding dimension ===
    print("=" * 60)
    print("PHASE 4 -- SEMANTIC VECTOR ENGINE VERIFICATION")
    print("=" * 60)

    all_ok &= check(
        "Embedding dimension",
        get_embedding_dim() == 384,
        f"dim={get_embedding_dim()}",
    )

    # === 2. Build embedding texts ===
    print("\n--- Building Embedding Texts ---")

    req_text = build_requirement_text(REQ_TITLE, REQ_TEXT)
    print(f"Requirement text: {req_text[:80]}...")

    matching_text = build_test_text(
        MATCHING_TEST_NAME, MATCHING_TEST_DOCSTRING
    )
    print(f"Matching test text: {matching_text}")

    unrelated_text = build_test_text(
        UNRELATED_TEST_NAME, UNRELATED_TEST_DOCSTRING
    )
    print(f"Unrelated test text: {unrelated_text}")

    # Fallback: no docstring
    fallback_text = build_test_text(
        NO_DOC_TEST_NAME,
        docstring=None,
        assertions_extracted=NO_DOC_ASSERTIONS,
    )
    print(f"Fallback test text: {fallback_text}")

    all_ok &= check(
        "Fallback text is non-empty and meaningful",
        len(fallback_text) > 10 and "response" in fallback_text.lower(),
        f"length={len(fallback_text)}",
    )

    # === 3. Embed everything ===
    print("\n--- Embedding Texts (first call loads model) ---")
    start = time.time()

    all_texts = [req_text, matching_text, unrelated_text, fallback_text]
    embeddings = embed_texts(all_texts)

    elapsed = time.time() - start
    print(f"Embedded {len(all_texts)} texts in {elapsed:.2f}s")

    req_emb, matched_emb, unrelated_emb, fallback_emb = embeddings

    all_ok &= check(
        "All embeddings are 384-dim",
        all(len(e) == 384 for e in embeddings),
    )
    all_ok &= check(
        "Embeddings are non-zero",
        all(any(abs(v) > 0.001 for v in e) for e in embeddings),
    )

    # === 4. Compute cosine similarities ===
    print("\n--- Cosine Similarity Scores ---")

    score_matched = cosine_similarity(req_emb, matched_emb)
    score_unrelated = cosine_similarity(req_emb, unrelated_emb)
    score_fallback = cosine_similarity(req_emb, fallback_emb)

    print(f"  Requirement vs Matching test (docstring):    {score_matched:.4f}")
    print(f"  Requirement vs Unrelated test:               {score_unrelated:.4f}")
    print(f"  Requirement vs Fallback test (no docstring):  {score_fallback:.4f}")

    # === 5. Verify: matched > unrelated ===
    print("\n--- Core Verification ---")

    all_ok &= check(
        "Matched score > Unrelated score",
        score_matched > score_unrelated,
        f"{score_matched:.4f} > {score_unrelated:.4f}, delta={score_matched - score_unrelated:.4f}",
    )
    all_ok &= check(
        "Meaningful gap (delta > 0.05)",
        (score_matched - score_unrelated) > 0.05,
        f"delta={score_matched - score_unrelated:.4f}",
    )

    # === 6. Verify: fallback is non-degenerate ===
    all_ok &= check(
        "Fallback score is non-degenerate (> 0.3)",
        score_fallback > 0.3,
        f"score={score_fallback:.4f}",
    )
    all_ok &= check(
        "Fallback score > Unrelated score",
        score_fallback > score_unrelated,
        f"{score_fallback:.4f} > {score_unrelated:.4f}",
    )

    # === 7. Cross-check with unrelated requirement ===
    print("\n--- Cross-check: Unrelated Requirement ---")
    unrel_req_text = build_requirement_text(UNRELATED_REQ_TITLE, UNRELATED_REQ_TEXT)
    unrel_req_emb = embed_text(unrel_req_text)

    cross_matched = cosine_similarity(unrel_req_emb, matched_emb)
    cross_unrelated = cosine_similarity(unrel_req_emb, unrelated_emb)

    print(f"  Auth requirement vs Response-time test: {cross_matched:.4f}")
    print(f"  Auth requirement vs Upload test:        {cross_unrelated:.4f}")

    all_ok &= check(
        "Auth req scores are both lower than matched pair",
        cross_matched < score_matched and cross_unrelated < score_matched,
        f"cross scores < {score_matched:.4f}",
    )

    # === 8. Single embed consistency ===
    print("\n--- Single vs Batch Consistency ---")
    single_emb = embed_text(req_text)
    consistency = cosine_similarity(single_emb, req_emb)
    all_ok &= check(
        "Single embed == batch embed (cosine > 0.999)",
        consistency > 0.999,
        f"cosine={consistency:.6f}",
    )

    # === Summary ===
    print("\n" + "=" * 60)
    if all_ok:
        print("All Phase 4 verification checks PASSED!")
    else:
        print("Some checks FAILED -- review output above.")
    print("=" * 60)
    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
