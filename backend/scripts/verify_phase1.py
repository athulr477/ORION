"""Phase 1 verification script.

Connects to the database, inserts a sample requirement + test case with a FK link,
queries the join, inserts a traceability matrix row, and verifies everything works.

Usage:
    python scripts/verify_phase1.py
"""

import asyncio
import sys
import uuid
from pathlib import Path

# Ensure project root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from orion.database import async_session_factory, engine
from orion.models import Requirement, TestCase, TraceabilityMatrix, TraceabilityStatus


async def verify() -> bool:
    """Run all Phase 1 verification checks. Returns True on success."""
    print("=" * 60)
    print("  ORION Phase 1 — Database & Schema Verification")
    print("=" * 60)

    async with async_session_factory() as session:
        session: AsyncSession

        # --- 1. Insert a sample requirement ---
        print("\n[1/5] Inserting sample requirement...")
        req = Requirement(
            id=uuid.uuid4(),
            external_id="REQ-001",
            title="Response time must be less than 200ms",
            description=(
                "The API endpoint must respond within 200 milliseconds "
                "for 95th percentile of requests under normal load."
            ),
            source="jira",
            raw_payload={"issue_key": "PROJ-42", "type": "Story"},
            constraints_extracted=None,  # Phase 3
        )
        session.add(req)
        await session.flush()
        print(f"  ✓ Requirement inserted: {req.external_id} (id={req.id})")

        # --- 2. Insert a sample test case linked to the requirement ---
        print("\n[2/5] Inserting sample test case linked to requirement...")
        test = TestCase(
            id=uuid.uuid4(),
            requirement_id=req.id,  # FK link — the @traces("REQ-001") connection
            external_id="tests/test_api.py::test_response_time",
            function_name="test_response_time",
            file_path="tests/test_api.py",
            source_code=(
                '@traces("REQ-001")\n'
                "def test_response_time(client):\n"
                '    response = client.get("/api/data")\n'
                "    assert response.elapsed.total_seconds() < 0.2\n"
            ),
            docstring="Verify API response time is under 200ms.",
            assertions_extracted=None,  # Phase 3
        )
        session.add(test)
        await session.flush()
        print(f"  ✓ Test case inserted: {test.function_name} (id={test.id})")
        print(f"    Linked to requirement: {req.external_id}")

        # --- 3. Query the join to verify the link ---
        print("\n[3/5] Querying requirement ↔ test_case join...")
        stmt = (
            select(Requirement, TestCase)
            .join(TestCase, TestCase.requirement_id == Requirement.id)
            .where(Requirement.external_id == "REQ-001")
        )
        result = await session.execute(stmt)
        rows = result.all()

        if len(rows) != 1:
            print(f"  ✗ Expected 1 joined row, got {len(rows)}")
            return False

        joined_req, joined_test = rows[0]
        print("  ✓ Join returned 1 row:")
        print(f"    Requirement: {joined_req.external_id} — {joined_req.title}")
        print(f"    Test case:   {joined_test.function_name} ({joined_test.file_path})")
        print(f"    FK match:    {joined_test.requirement_id == joined_req.id}")

        # --- 4. Insert a traceability matrix row ---
        print("\n[4/5] Inserting traceability matrix entry...")
        tm = TraceabilityMatrix(
            id=uuid.uuid4(),
            requirement_id=req.id,
            test_case_id=test.id,
            semantic_score=0.82,
            structural_score=0.91,
            risk_score=0.6 * 0.82 + 0.4 * 0.91,  # = 0.856
            confidence=0.88,
            status=TraceabilityStatus.COVERED,
            requirement_delta=None,
            audit_summary=None,
        )
        session.add(tm)
        await session.flush()
        print("  ✓ Traceability entry inserted:")
        print(f"    semantic_score:   {tm.semantic_score}")
        print(f"    structural_score: {tm.structural_score}")
        print(f"    risk_score:       {tm.risk_score:.3f}")
        print(f"    confidence:       {tm.confidence}")
        print(f"    status:           {tm.status.value}")

        # --- 5. Verify traceability matrix join ---
        print("\n[5/5] Querying full traceability join (req → test → matrix)...")
        stmt = (
            select(Requirement, TestCase, TraceabilityMatrix)
            .join(TestCase, TestCase.requirement_id == Requirement.id)
            .join(
                TraceabilityMatrix,
                (TraceabilityMatrix.requirement_id == Requirement.id)
                & (TraceabilityMatrix.test_case_id == TestCase.id),
            )
            .where(Requirement.external_id == "REQ-001")
        )
        result = await session.execute(stmt)
        rows = result.all()

        if len(rows) != 1:
            print(f"  ✗ Expected 1 full join row, got {len(rows)}")
            return False

        r, t, m = rows[0]
        print("  ✓ Full join returned 1 row:")
        print(f"    {r.external_id} → {t.function_name} → {m.status.value} "
              f"(risk={m.risk_score:.3f})")

        # --- Cleanup: rollback so we don't persist test data ---
        await session.rollback()
        print("\n  ✓ Rolled back test data (no persistent changes).")

    # Close engine
    await engine.dispose()

    print("\n" + "=" * 60)
    print("  ✓ ALL PHASE 1 CHECKS PASSED")
    print("=" * 60)
    return True


if __name__ == "__main__":
    success = asyncio.run(verify())
    sys.exit(0 if success else 1)
