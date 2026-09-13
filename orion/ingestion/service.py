"""Ingestion service — upsert requirements and test cases with FK linkage."""

from __future__ import annotations

import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from orion.analysis.delta_parser import parse_changelog_to_delta
from orion.analysis.delta_service import apply_requirement_delta
from orion.ingestion.parsers import RequirementData, TestFunctionData
from orion.models.requirement import Requirement
from orion.models.test_case import TestCase

logger = logging.getLogger(__name__)


async def upsert_requirement(
    session: AsyncSession,
    data: RequirementData,
) -> tuple[Requirement, bool]:
    """Insert or update a requirement based on ``external_id``.

    On update, if changelog data is present, triggers Phase 6 delta tracking:
    1. Saves the old description before overwriting.
    2. Parses the changelog into a structured delta via Phase 3 constraint diffing.
    3. Writes the delta to traceability entries where the linked test is stale.

    Args:
        session: Async database session.
        data: Parsed requirement data.

    Returns:
        Tuple of (Requirement instance, was_created: bool).
    """
    stmt = select(Requirement).where(Requirement.external_id == data.external_id)
    result = await session.execute(stmt)
    existing = result.scalar_one_or_none()

    if existing:
        # Phase 6: Save old description before update for delta tracking
        old_description = existing.description or ""

        existing.title = data.title
        existing.description = data.description
        existing.raw_payload = data.raw_payload
        logger.info("Updated requirement %s", data.external_id)
        await session.flush()

        # Phase 6: Track requirement delta if changelog is available
        if data.changelog:
            try:
                delta = parse_changelog_to_delta(
                    changelog_items=data.changelog,
                    old_description=old_description,
                    new_description=data.description,
                )
                if delta.changes:
                    updated_count = await apply_requirement_delta(
                        session, existing, delta,
                    )
                    logger.info(
                        "Phase 6: Applied delta with %d changes to %d entries for %s",
                        len(delta.changes),
                        updated_count,
                        data.external_id,
                    )
            except Exception:
                logger.exception(
                    "Phase 6: Failed to process delta for %s — "
                    "requirement update was still applied",
                    data.external_id,
                )

        return existing, False

    requirement = Requirement(
        id=uuid.uuid4(),
        external_id=data.external_id,
        title=data.title,
        description=data.description,
        source=data.source,
        raw_payload=data.raw_payload,
    )
    session.add(requirement)
    await session.flush()
    logger.info("Created requirement %s", data.external_id)
    return requirement, True


async def upsert_test_cases(
    session: AsyncSession,
    file_path: str,
    functions: list[TestFunctionData],
) -> tuple[int, int, int, int]:
    """Insert or update test cases from a parsed test file and link to requirements.

    For each test function:
    1. Build ``external_id`` as ``file_path::function_name``
    2. Upsert into ``test_cases``
    3. Look up requirement by ``external_id`` matching ``@traces`` value
    4. Set ``requirement_id`` FK if found

    Args:
        session: Async database session.
        file_path: Path to the test file in the repository.
        functions: Parsed test function data.

    Returns:
        Tuple of (created_count, updated_count, linked_count, unlinked_count).
    """
    created = 0
    updated = 0
    linked = 0
    unlinked = 0

    for func_data in functions:
        external_id = f"{file_path}::{func_data.function_name}"

        # Resolve requirement FK from @traces decorator
        requirement_id = None
        if func_data.traced_requirements:
            # Use the first @traces value (a test links to one requirement)
            req_external_id = func_data.traced_requirements[0]
            stmt = select(Requirement.id).where(
                Requirement.external_id == req_external_id
            )
            result = await session.execute(stmt)
            req_row = result.scalar_one_or_none()
            if req_row:
                requirement_id = req_row
                linked += 1
            else:
                logger.warning(
                    "Test %s traces requirement %s which does not exist yet",
                    external_id,
                    req_external_id,
                )
                unlinked += 1

        # Upsert test case
        stmt = select(TestCase).where(TestCase.external_id == external_id)
        result = await session.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            existing.source_code = func_data.source_code
            existing.docstring = func_data.docstring
            existing.requirement_id = requirement_id
            updated += 1
            logger.info("Updated test case %s", external_id)
        else:
            test_case = TestCase(
                id=uuid.uuid4(),
                external_id=external_id,
                function_name=func_data.function_name,
                file_path=file_path,
                source_code=func_data.source_code,
                docstring=func_data.docstring,
                requirement_id=requirement_id,
            )
            session.add(test_case)
            created += 1
            logger.info("Created test case %s", external_id)

    await session.flush()
    return created, updated, linked, unlinked

