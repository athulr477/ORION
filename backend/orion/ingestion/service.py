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


async def enrich_requirement(session: AsyncSession, requirement: Requirement) -> None:
    """Compute and persist embedding + structural constraints for a requirement.

    This is the single canonical implementation shared across the Jira sync,
    GitHub PR analysis, and simulate-webhook pipelines.

    Skips fields that are already populated to avoid redundant computation on
    every sync cycle.

    Args:
        session: Active async database session.
        requirement: A flushed Requirement ORM instance.
    """
    updated = False

    if requirement.constraints_extracted is None:
        from orion.extraction.requirement_extractor import extract_constraints
        constraints = extract_constraints(requirement.description or "")
        requirement.constraints_extracted = (
            constraints.to_dict() if hasattr(constraints, "to_dict") else constraints
        )
        updated = True

    if requirement.embedding is None:
        from orion.embedding.engine import embed_text
        from orion.embedding.text_builder import build_requirement_text
        req_text = build_requirement_text(requirement.title, requirement.description or "")
        requirement.embedding = embed_text(req_text)
        updated = True

    if updated:
        await session.flush()


async def get_default_workspace_id(session: AsyncSession) -> uuid.UUID:
    """Retrieve or create the Default Workspace ID."""
    from orion.models.workspace import Workspace
    stmt = select(Workspace.id).where(Workspace.name == "Default Workspace")
    result = await session.execute(stmt)
    ws_id = result.scalar_one_or_none()
    if not ws_id:
        stmt2 = select(Workspace.id).limit(1)
        res2 = await session.execute(stmt2)
        ws_id = res2.scalar_one_or_none()
    if not ws_id:
        ws = Workspace(id=uuid.uuid4(), name="Default Workspace")
        session.add(ws)
        await session.flush()
        ws_id = ws.id
    return ws_id


async def upsert_requirement(
    session: AsyncSession,
    data: RequirementData | dict,
) -> tuple[Requirement, bool]:
    """Insert or update a requirement based on ``external_id``.

    On update, if changelog data is present, triggers Phase 6 delta tracking:
    1. Saves the old description before overwriting.
    2. Parses the changelog into a structured delta via Phase 3 constraint diffing.
    3. Writes the delta to traceability entries where the linked test is stale.

    Args:
        session: Async database session.
        data: Parsed requirement data (RequirementData or dict).

    Returns:
        Tuple of (Requirement instance, was_created: bool).
    """
    if isinstance(data, dict):
        ext_id = data.get("external_id")
        title = data.get("title", "")
        desc = data.get("description", "")
        source = data.get("source", "jira")
        raw_payload = data.get("raw_payload")
        changelog = data.get("changelog")
        ws_id = data.get("workspace_id")
    else:
        ext_id = data.external_id
        title = data.title
        desc = data.description
        source = data.source
        raw_payload = data.raw_payload
        changelog = data.changelog
        ws_id = getattr(data, "workspace_id", None)

    if not ws_id:
        ws_id = await get_default_workspace_id(session)
    elif isinstance(ws_id, str):
        ws_id = uuid.UUID(ws_id)

    stmt = select(Requirement).where(
        Requirement.external_id == ext_id,
        Requirement.workspace_id == ws_id,
    )
    result = await session.execute(stmt)
    existing = result.scalar_one_or_none()

    if existing:
        # Phase 6: Save old description before update for delta tracking
        old_description = existing.description or ""

        existing.title = title
        existing.description = desc
        existing.raw_payload = raw_payload
        logger.info("Updated requirement %s", ext_id)
        await session.flush()

        # Phase 6: Track requirement delta if changelog is available
        if changelog:
            try:
                delta = parse_changelog_to_delta(
                    changelog_items=changelog,
                    old_description=old_description,
                    new_description=desc,
                )
                if delta.changes:
                    updated_count = await apply_requirement_delta(
                        session, existing, delta,
                    )
                    logger.info(
                        "Phase 6: Applied delta with %d changes to %d entries for %s",
                        len(delta.changes),
                        updated_count,
                        ext_id,
                    )
            except Exception:
                logger.exception(
                    "Phase 6: Failed to process delta for %s — "
                    "requirement update was still applied",
                    ext_id,
                )

        return existing, False

    requirement = Requirement(
        id=uuid.uuid4(),
        workspace_id=ws_id,
        external_id=ext_id,
        title=title,
        description=desc,
        source=source,
        raw_payload=raw_payload,
    )
    session.add(requirement)
    await session.flush()
    logger.info("Created requirement %s", ext_id)
    return requirement, True


async def upsert_test_cases(
    session: AsyncSession,
    file_path: str,
    functions: list[TestFunctionData],
    workspace_id: uuid.UUID | None = None,
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
        workspace_id: Optional workspace UUID. If omitted, falls back to Default Workspace.

    Returns:
        Tuple of (created_count, updated_count, linked_count, unlinked_count).
    """
    if not workspace_id:
        workspace_id = await get_default_workspace_id(session)

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
                Requirement.external_id == req_external_id,
                Requirement.workspace_id == workspace_id,
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
        stmt = select(TestCase).where(
            TestCase.external_id == external_id,
            TestCase.workspace_id == workspace_id,
        )
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
                workspace_id=workspace_id,
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

