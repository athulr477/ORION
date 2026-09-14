"""Delta service — apply requirement deltas to traceability entries.

Phase 6: When a requirement changes and its linked test hasn't been
updated since, write the structured delta to `traceability_matrix.requirement_delta`.

This ensures that stale test↔requirement links are flagged with the
specific changes that caused drift.
"""

from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from orion.analysis.delta_parser import RequirementDelta
from orion.models.requirement import Requirement
from orion.models.test_case import TestCase
from orion.models.traceability_matrix import TraceabilityMatrix

logger = logging.getLogger(__name__)


async def apply_requirement_delta(
    session: AsyncSession,
    requirement: Requirement,
    delta: RequirementDelta,
) -> int:
    """Write a requirement delta to traceability entries with stale tests.

    A test is considered "stale" if its `updated_at` timestamp is older than
    the requirement's `updated_at` timestamp — meaning the test hasn't been
    touched since the requirement changed.

    Args:
        session: Async database session.
        requirement: The requirement that was updated.
        delta: The structured delta from parse_changelog_to_delta().

    Returns:
        Number of traceability entries updated with the delta.
    """
    if not delta.changes:
        logger.info(
            "No delta changes for requirement %s — skipping",
            requirement.external_id,
        )
        return 0

    delta_dict = delta.to_dict()

    # Find all traceability entries for this requirement where the linked
    # test_case has not been updated since the requirement changed.
    stmt = (
        select(TraceabilityMatrix)
        .join(TestCase, TraceabilityMatrix.test_case_id == TestCase.id)
        .where(
            TraceabilityMatrix.requirement_id == requirement.id,
            TestCase.updated_at < requirement.updated_at,
        )
    )

    result = await session.execute(stmt)
    entries = result.scalars().all()

    if not entries:
        # Also check for entries where test_case.updated_at is not available
        # (shouldn't happen, but be defensive)
        stmt_all = select(TraceabilityMatrix).where(
            TraceabilityMatrix.requirement_id == requirement.id,
        )
        result_all = await session.execute(stmt_all)
        all_entries = result_all.scalars().all()

        if all_entries:
            logger.info(
                "Requirement %s has %d traceability entries, but all linked "
                "tests have been updated since — no delta written",
                requirement.external_id,
                len(all_entries),
            )
        else:
            logger.info(
                "Requirement %s has no traceability entries — no delta written",
                requirement.external_id,
            )
        return 0

    # Write delta to each stale entry
    updated_count = 0
    for entry in entries:
        entry.requirement_delta = delta_dict
        updated_count += 1

    await session.flush()

    logger.info(
        "Applied requirement delta to %d/%d traceability entries for %s "
        "(%d changes: %s)",
        updated_count,
        len(entries),
        requirement.external_id,
        len(delta.changes),
        ", ".join(sorted(set(c.type for c in delta.changes))),
    )

    return updated_count
