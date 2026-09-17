"""Phase 5 verification script -- Structural Matcher & Hybrid Risk Engine.

Runs end-to-end: requirement text -> constraint extraction -> assertion extraction
-> structural matching -> semantic embedding -> hybrid risk classification.

Tests against a labeled dataset of 15 pairs (5 Covered, 5 Partial, 5 Drifted)
to verify sane, non-random classifications.

Usage:
    python scripts/verify_phase5.py
"""

from __future__ import annotations

import sys
import textwrap
import time

from orion.analysis.risk_engine import classify
from orion.analysis.structural_matcher import compute_structural_score
from orion.embedding.engine import cosine_similarity, embed_texts
from orion.embedding.text_builder import build_requirement_text, build_test_text
from orion.extraction.code_extractor import extract_assertions
from orion.extraction.requirement_extractor import extract_constraints

# ---------------------------------------------------------------------------
# Labeled dataset: 15 pairs (5 Covered, 5 Partial, 5 Drifted)
# ---------------------------------------------------------------------------

LABELED_PAIRS = [
    # ===== COVERED (5) — test directly matches requirement =====
    {
        "label": "Covered",
        "req_title": "API Response Time",
        "req_text": "The API endpoint must return a response within 200 milliseconds under normal load.",
        "test_code": textwrap.dedent('''\
            def test_response_time(api_client):
                """Verify API response time is under 200ms."""
                response = api_client.get("/api/v1/query")
                assert response.status_code == 200
                assert response.elapsed.total_seconds() < 0.2
        '''),
    },
    {
        "label": "Covered",
        "req_title": "Password Minimum Length",
        "req_text": "User passwords must be at least 8 characters long.",
        "test_code": textwrap.dedent('''\
            def test_password_length(user_service):
                """Password must be at least 8 characters."""
                assert len(user_service.validate("short")) >= 8
        '''),
    },
    {
        "label": "Covered",
        "req_title": "Cache Hit Rate",
        "req_text": "The cache must maintain a hit rate of at least 95 percent.",
        "test_code": textwrap.dedent('''\
            def test_cache_hit_rate(cache):
                """Cache hit rate must be at least 95%."""
                stats = cache.get_stats()
                assert stats.hit_rate >= 0.95
        '''),
    },
    {
        "label": "Covered",
        "req_title": "Max Connections",
        "req_text": "The database pool must support up to 100 concurrent connections.",
        "test_code": textwrap.dedent('''\
            def test_max_connections(db_pool):
                """DB pool supports 100 concurrent connections."""
                assert db_pool.max_connections == 100
                assert db_pool.active_connections <= 100
        '''),
    },
    {
        "label": "Covered",
        "req_title": "File Size Limit",
        "req_text": "The system must reject file uploads larger than 50 MB.",
        "test_code": textwrap.dedent('''\
            def test_file_size_limit(upload_service):
                """Reject files over 50 MB."""
                assert upload_service.max_size_mb == 50
                assert upload_service.validate(size_mb=51) is False
                assert upload_service.validate(size_mb=49) is True
        '''),
    },

    # ===== PARTIAL (5) — test covers the topic but misses specifics =====
    {
        "label": "Partial",
        "req_title": "API Throughput",
        "req_text": "The system must handle at least 1000 requests per second with latency under 100ms.",
        "test_code": textwrap.dedent('''\
            def test_api_throughput(load_test):
                """Test that API handles high load."""
                result = load_test.run(duration=60)
                assert result.total_requests > 500
                assert result.error_rate < 0.01
        '''),
    },
    {
        "label": "Partial",
        "req_title": "Session Timeout",
        "req_text": "User sessions must expire after no more than 30 minutes of inactivity.",
        "test_code": textwrap.dedent('''\
            def test_session_management(session_service):
                """Test session timeout behavior."""
                session = session_service.create()
                assert session.is_active is True
                assert session.timeout_minutes > 0
        '''),
    },
    {
        "label": "Partial",
        "req_title": "Error Rate",
        "req_text": "The API error rate must not exceed 0.1 percent under normal load.",
        "test_code": textwrap.dedent('''\
            def test_error_handling(api_client):
                """Test that errors are handled properly."""
                response = api_client.get("/api/invalid")
                assert response.status_code == 404
                assert "error" in response.json()
        '''),
    },
    {
        "label": "Partial",
        "req_title": "Data Retention",
        "req_text": "Audit logs must be retained for at least 90 days.",
        "test_code": textwrap.dedent('''\
            def test_audit_log_exists(audit_service):
                """Test that audit logs are created."""
                audit_service.log_action("test_action")
                logs = audit_service.get_recent(days=7)
                assert len(logs) > 0
        '''),
    },
    {
        "label": "Partial",
        "req_title": "Encryption Standard",
        "req_text": "All data at rest must be encrypted with AES-256.",
        "test_code": textwrap.dedent('''\
            def test_data_encryption(storage):
                """Test that data is encrypted."""
                stored = storage.put("secret_data")
                assert stored.is_encrypted is True
        '''),
    },

    # ===== DRIFTED (5) — test is unrelated to the requirement =====
    {
        "label": "Drifted",
        "req_title": "Response Time SLA",
        "req_text": "API response time must be less than 200 milliseconds.",
        "test_code": textwrap.dedent('''\
            def test_user_avatar_upload(user_service):
                """Test avatar image upload."""
                result = user_service.upload_avatar("photo.png")
                assert result.status == "success"
                assert result.url.endswith(".png")
        '''),
    },
    {
        "label": "Drifted",
        "req_title": "Database Backup",
        "req_text": "Full database backups must run at least every 24 hours.",
        "test_code": textwrap.dedent('''\
            def test_email_notification(notifier):
                """Test email sending."""
                result = notifier.send("user@example.com", "Hello")
                assert result.delivered is True
        '''),
    },
    {
        "label": "Drifted",
        "req_title": "Rate Limiting",
        "req_text": "The API must enforce rate limiting of no more than 100 requests per minute per user.",
        "test_code": textwrap.dedent('''\
            def test_color_theme_preference(ui_service):
                """Test user color theme preference."""
                ui_service.set_theme("dark")
                assert ui_service.current_theme == "dark"
        '''),
    },
    {
        "label": "Drifted",
        "req_title": "Password Complexity",
        "req_text": "Passwords must contain at least one uppercase letter, one digit, and one special character.",
        "test_code": textwrap.dedent('''\
            def test_product_search(catalog):
                """Test product search functionality."""
                results = catalog.search("laptop")
                assert len(results) > 0
                assert results[0].name.lower().find("laptop") >= 0
        '''),
    },
    {
        "label": "Drifted",
        "req_title": "Concurrent Users",
        "req_text": "The system must support at least 500 concurrent users without degradation.",
        "test_code": textwrap.dedent('''\
            def test_csv_export(report_service):
                """Test CSV export of reports."""
                csv_data = report_service.export("monthly", format="csv")
                assert csv_data.startswith("date,")
                assert len(csv_data) > 100
        '''),
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
    print("PHASE 5 -- STRUCTURAL MATCHER & HYBRID RISK ENGINE VERIFICATION")
    print("=" * 70)

    # === Step 1: Extract constraints and assertions ===
    print("\n--- Step 1: Extracting constraints and assertions ---")
    extracted_data = []
    for pair in LABELED_PAIRS:
        req_result = extract_constraints(pair["req_text"], pair["req_title"])
        code_result = extract_assertions(pair["test_code"], "test_func")
        extracted_data.append({
            "label": pair["label"],
            "req_title": pair["req_title"],
            "req_constraints": req_result.to_dict(),
            "test_assertions": code_result.to_dict(),
            "req_text": pair["req_text"],
            "test_code": pair["test_code"],
            "test_docstring": code_result.docstring,
        })
    print(f"  Extracted data for {len(extracted_data)} pairs")

    # === Step 2: Compute structural scores ===
    print("\n--- Step 2: Computing structural scores ---")
    for item in extracted_data:
        match_result = compute_structural_score(
            item["req_constraints"], item["test_assertions"]
        )
        item["structural_score"] = match_result.structural_score
        item["structural_detail"] = match_result.to_dict()

    # === Step 3: Compute semantic scores ===
    print("\n--- Step 3: Computing semantic scores (embedding) ---")
    start = time.time()

    req_texts = [
        build_requirement_text(item["req_title"], item["req_text"])
        for item in extracted_data
    ]
    test_texts = [
        build_test_text("test_func", item["test_docstring"], item["test_code"])
        for item in extracted_data
    ]

    req_embeddings = embed_texts(req_texts)
    test_embeddings = embed_texts(test_texts)

    for i, item in enumerate(extracted_data):
        item["semantic_score"] = cosine_similarity(
            req_embeddings[i], test_embeddings[i]
        )

    elapsed = time.time() - start
    print(f"  Embedded {len(extracted_data) * 2} texts in {elapsed:.2f}s")

    # === Step 4: Classify with hybrid risk engine ===
    print("\n--- Step 4: Classifying with hybrid risk engine ---")
    print(f"\n  {'Label':<10} {'Predicted':<10} {'Risk':>6} {'Sem':>6} {'Str':>6} {'Conf':>6}  Requirement")
    print("  " + "-" * 80)

    correct = 0
    confusion = {"Covered": {"Covered": 0, "Partial": 0, "Drifted": 0},
                 "Partial": {"Covered": 0, "Partial": 0, "Drifted": 0},
                 "Drifted": {"Covered": 0, "Partial": 0, "Drifted": 0}}

    for item in extracted_data:
        result = classify(item["semantic_score"], item["structural_score"])
        item["risk_result"] = result

        match = result.status == item["label"]
        marker = " " if match else " *"
        if match:
            correct += 1
        confusion[item["label"]][result.status] += 1

        print(
            f"  {item['label']:<10} {result.status:<10} "
            f"{result.risk_score:>6.3f} {result.semantic_score:>6.3f} "
            f"{result.structural_score:>6.3f} {result.confidence:>6.3f}  "
            f"{item['req_title'][:30]}{marker}"
        )

    # === Step 5: Evaluate ===
    print("\n--- Step 5: Evaluation ---")
    accuracy = correct / len(extracted_data)
    print(f"  Accuracy: {correct}/{len(extracted_data)} = {accuracy:.1%}")

    print("\n  Confusion matrix:")
    print(f"  {'':>12} {'Pred Cov':>10} {'Pred Par':>10} {'Pred Dri':>10}")
    for true_label in ["Covered", "Partial", "Drifted"]:
        row = confusion[true_label]
        print(f"  {true_label:>12} {row['Covered']:>10} {row['Partial']:>10} {row['Drifted']:>10}")

    # Per-class precision/recall
    print("\n  Per-class metrics:")
    for cls in ["Covered", "Partial", "Drifted"]:
        tp = confusion[cls][cls]
        predicted_total = sum(confusion[lbl][cls] for lbl in confusion)
        actual_total = sum(confusion[cls].values())
        precision = tp / predicted_total if predicted_total > 0 else 0.0
        recall = tp / actual_total if actual_total > 0 else 0.0
        print(f"    {cls}: precision={precision:.2f}, recall={recall:.2f} (TP={tp}, pred={predicted_total}, actual={actual_total})")

    # === Sanity checks ===
    print("\n--- Sanity Checks ---")

    # Average risk score by label should be ordered: Covered > Partial > Drifted
    avg_by_label = {}
    for label in ["Covered", "Partial", "Drifted"]:
        scores = [item["risk_result"].risk_score for item in extracted_data if item["label"] == label]
        avg_by_label[label] = sum(scores) / len(scores) if scores else 0.0
        print(f"  Avg risk_score for {label}: {avg_by_label[label]:.4f}")

    all_ok &= check(
        "Avg Covered > Avg Partial",
        avg_by_label["Covered"] > avg_by_label["Partial"],
        f"{avg_by_label['Covered']:.4f} > {avg_by_label['Partial']:.4f}",
    )
    all_ok &= check(
        "Avg Partial > Avg Drifted",
        avg_by_label["Partial"] > avg_by_label["Drifted"],
        f"{avg_by_label['Partial']:.4f} > {avg_by_label['Drifted']:.4f}",
    )
    all_ok &= check(
        "Classifications are non-random (accuracy > 40%)",
        accuracy > 0.40,
        f"accuracy={accuracy:.1%}",
    )
    all_ok &= check(
        "At least some Covered pairs classified as Covered",
        confusion["Covered"]["Covered"] >= 2,
        f"TP={confusion['Covered']['Covered']}/5",
    )
    all_ok &= check(
        "At least some Drifted pairs classified as Drifted",
        confusion["Drifted"]["Drifted"] >= 2,
        f"TP={confusion['Drifted']['Drifted']}/5",
    )

    # === Summary ===
    print("\n" + "=" * 70)
    if all_ok:
        print("All Phase 5 verification checks PASSED!")
        print("Classifications are sane and non-random. Ready for Phase 6.")
    else:
        print("Some checks FAILED -- review output above.")
        print("The formula/thresholds may need adjustment.")
    print("=" * 70)
    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
