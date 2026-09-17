"""Verbalization service — orchestrates evidence → prompt → LLM → audit_summary.

This is the main entry point for Phase 7.  It:
1. Loads linked requirement and test_case for a traceability entry.
2. Builds the deterministic evidence tuple (evidence.py).
3. Formats it into a constrained LLM prompt.
4. Calls Ollama to verbalize it into one audit sentence.
5. Writes the result to traceability_matrix.audit_summary.

Only Partial/Drifted entries are processed.  Covered entries are skipped.

IMPORTANT: No LLM in the decision path — only for phrasing.
"""

from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from orion.models.traceability_matrix import TraceabilityMatrix, TraceabilityStatus
from orion.verbalization.evidence import EvidenceTuple, build_evidence_tuple
from orion.verbalization.llm_client import OllamaClient

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Prompt template
# ---------------------------------------------------------------------------

_PROMPT_TEMPLATE = """Based ONLY on the evidence below, write ONE concise sentence explaining why this requirement-test pair is classified as {status}.

Evidence:
{evidence_context}

Write exactly one sentence. Do not invent any claims not present in the evidence above."""


def _build_prompt(evidence: EvidenceTuple) -> str:
    """Format the evidence into the constrained LLM prompt."""
    return _PROMPT_TEMPLATE.format(
        status=evidence.status,
        evidence_context=evidence.to_prompt_context(),
    )


# ---------------------------------------------------------------------------
# Single-entry verbalization
# ---------------------------------------------------------------------------


async def verbalize_entry(
    session: AsyncSession,
    entry: TraceabilityMatrix,
    client: OllamaClient | None = None,
) -> str | None:
    """Verbalize a single traceability entry's classification.

    Builds the evidence tuple from linked requirement/test data, prompts
    the LLM, and writes the result to entry.audit_summary.

    Args:
        session: Async database session.
        entry: The traceability matrix entry to verbalize.
        client: Optional pre-initialized OllamaClient.  If None, one is created.

    Returns:
        The generated audit summary sentence, or None if skipped (Covered).
    """
    # Skip Covered entries — they don't need explanation
    if entry.status == TraceabilityStatus.COVERED:
        logger.debug(
            "Skipping verbalization for Covered entry %s",
            entry.id,
        )
        return None

    # Load linked requirement and test_case if not already loaded
    requirement = entry.requirement
    test_case = entry.test_case

    if requirement is None or test_case is None:
        # Eagerly load relationships
        stmt = (
            select(TraceabilityMatrix)
            .options(
                selectinload(TraceabilityMatrix.requirement),
                selectinload(TraceabilityMatrix.test_case),
            )
            .where(TraceabilityMatrix.id == entry.id)
        )
        result = await session.execute(stmt)
        entry = result.scalar_one()
        requirement = entry.requirement
        test_case = entry.test_case

    if requirement is None or test_case is None:
        logger.error(
            "Cannot verbalize entry %s — missing requirement or test_case",
            entry.id,
        )
        return None

    # Build evidence tuple
    evidence = build_evidence_tuple(
        status=entry.status.value if isinstance(entry.status, TraceabilityStatus) else entry.status,
        risk_score=entry.risk_score or 0.0,
        semantic_score=entry.semantic_score or 0.0,
        structural_score=entry.structural_score or 0.0,
        requirement_external_id=requirement.external_id,
        requirement_title=requirement.title,
        requirement_description=requirement.description or "",
        requirement_constraints=requirement.constraints_extracted,
        test_function_name=test_case.function_name,
        test_assertions=test_case.assertions_extracted,
        requirement_delta=entry.requirement_delta,
    )

    if evidence is None:
        return None

    # Build prompt
    prompt = _build_prompt(evidence)

    # Initialize client if needed
    if client is None:
        client = OllamaClient()

    # Try LLM generation, fall back to deterministic sentence
    if client.is_available():
        response = client.generate(prompt)
        if response.success and response.text:
            audit_summary = response.text
            logger.info(
                "LLM generated audit summary for entry %s: %s",
                entry.id,
                audit_summary[:100],
            )
        else:
            logger.warning(
                "LLM generation failed for entry %s (%s) — using fallback",
                entry.id,
                response.error,
            )
            audit_summary = evidence.to_fallback_sentence()
    else:
        logger.info(
            "Ollama not available — using fallback sentence for entry %s",
            entry.id,
        )
        audit_summary = evidence.to_fallback_sentence()

    # Write to database
    entry.audit_summary = audit_summary
    await session.flush()

    return audit_summary


# ---------------------------------------------------------------------------
# Batch verbalization
# ---------------------------------------------------------------------------


async def verbalize_all_pending(
    session: AsyncSession,
    client: OllamaClient | None = None,
) -> int:
    """Verbalize all Partial/Drifted entries that don't yet have an audit_summary.

    Args:
        session: Async database session.
        client: Optional pre-initialized OllamaClient (reused across entries).

    Returns:
        Number of entries that were verbalized.
    """
    # Find all Partial/Drifted entries with no audit_summary
    stmt = (
        select(TraceabilityMatrix)
        .options(
            selectinload(TraceabilityMatrix.requirement),
            selectinload(TraceabilityMatrix.test_case),
        )
        .where(
            TraceabilityMatrix.status.in_([
                TraceabilityStatus.PARTIAL,
                TraceabilityStatus.DRIFTED,
            ]),
            TraceabilityMatrix.audit_summary.is_(None),
        )
    )

    result = await session.execute(stmt)
    entries = result.scalars().all()

    if not entries:
        logger.info("No pending entries to verbalize")
        return 0

    logger.info("Found %d pending entries to verbalize", len(entries))

    # Initialize client once for the batch
    if client is None:
        client = OllamaClient()

    verbalized_count = 0
    for entry in entries:
        summary = await verbalize_entry(session, entry, client=client)
        if summary is not None:
            verbalized_count += 1

    logger.info(
        "Verbalized %d/%d pending entries",
        verbalized_count,
        len(entries),
    )

    return verbalized_count
