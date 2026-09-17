"""Service layer for dashboard-related logic."""

import logging
import uuid
from typing import Any
from collections.abc import Callable, Coroutine

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from orion.dashboard.schemas import SimulateRequest
from orion.models.requirement import Requirement
from orion.models.test_case import TestCase
from orion.models.traceability_matrix import TraceabilityMatrix, TraceabilityStatus

logger = logging.getLogger(__name__)


async def simulate_webhook_logic(
    body: SimulateRequest,
    session: AsyncSession,
    update_progress: Callable[[float, str], Coroutine[Any, Any, None]] | None = None
) -> dict[str, Any]:
    """Run the full Phases 2-7 pipeline on synthetic data.
    
    Optionally accepts a progress callback for asynchronous background execution.
    """
    steps: list[str] = []
    
    async def report_progress(prog: float, msg: str) -> None:
        if update_progress:
            await update_progress(prog, msg)
        steps.append(msg)
        logger.info("[Simulate] %s", msg)

    await report_progress(0.1, "Step 1: Upserting requirement")

    # --- Step 1: Upsert requirement ---
    stmt = select(Requirement).where(
        Requirement.external_id == body.requirement_external_id
    )
    result = await session.execute(stmt)
    requirement = result.scalar_one_or_none()

    if requirement is None:
        requirement = Requirement(
            id=uuid.uuid4(),
            external_id=body.requirement_external_id,
            title=body.requirement_title,
            description=body.requirement_description,
            source="simulate",
        )
        session.add(requirement)
        await session.flush()
        await report_progress(0.15, f"Created requirement {body.requirement_external_id}")
    else:
        requirement.title = body.requirement_title
        requirement.description = body.requirement_description
        await session.flush()
        await report_progress(0.15, f"Updated requirement {body.requirement_external_id}")

    await report_progress(0.2, "Step 2: Upserting test case")
    # --- Step 2: Upsert test case ---
    test_external_id = f"{body.test_file_path}::{body.test_function_name}"
    stmt = select(TestCase).where(TestCase.external_id == test_external_id)
    result = await session.execute(stmt)
    test_case = result.scalar_one_or_none()

    if test_case is None:
        test_case = TestCase(
            id=uuid.uuid4(),
            external_id=test_external_id,
            function_name=body.test_function_name,
            file_path=body.test_file_path,
            source_code=body.test_source_code,
            requirement_id=requirement.id,
        )
        session.add(test_case)
        await session.flush()
        await report_progress(0.25, f"Created test case {test_external_id}")
    else:
        test_case.source_code = body.test_source_code
        test_case.requirement_id = requirement.id
        await session.flush()
        await report_progress(0.25, f"Updated test case {test_external_id}")

    await report_progress(0.3, "Step 3: Phase 3 - Structural extraction")
    from orion.extraction.requirement_extractor import extract_constraints
    from orion.extraction.code_extractor import extract_assertions
    
    # --- Step 3: Phase 3 — Structural extraction ---
    try:
        req_extraction = extract_constraints(body.requirement_description)
        requirement.constraints_extracted = req_extraction.to_dict()
        await report_progress(0.35, f"Extracted {len(req_extraction.constraints)} requirement constraints")
    except Exception as e:
        logger.warning("Constraint extraction failed: %s", e)
        requirement.constraints_extracted = {"constraints": [], "keywords": []}
        await report_progress(0.35, "Constraint extraction failed")

    try:
        code_extraction = extract_assertions(body.test_source_code)
        test_case.assertions_extracted = code_extraction.to_dict()
        await report_progress(0.4, f"Extracted {len(code_extraction.assertions)} test assertions")
    except Exception as e:
        logger.warning("Assertion extraction failed: %s", e)
        test_case.assertions_extracted = {"assertions": [], "keywords": []}
        await report_progress(0.4, "Assertion extraction failed")

    await session.flush()

    await report_progress(0.5, "Step 4: Phase 4 - Semantic embedding")
    # --- Step 4: Phase 4 — Semantic embedding ---
    semantic_score = 0.0
    try:
        from orion.embedding.engine import semantic_similarity, embed_text
        from orion.embedding.text_builder import build_requirement_text, build_test_text

        req_text = build_requirement_text(
            title=requirement.title,
            description=requirement.description,
        )
        test_text = build_test_text(
            function_name=test_case.function_name,
            docstring=test_case.docstring,
            assertions_extracted=test_case.assertions_extracted,
        )

        req_embedding = embed_text(req_text)
        test_embedding = embed_text(test_text)

        requirement.embedding = req_embedding
        test_case.embedding = test_embedding

        semantic_score = semantic_similarity(req_embedding, test_embedding)
        await report_progress(0.6, f"Computed semantic_score = {semantic_score:.4f}")
    except Exception as e:
        logger.warning("Embedding failed: %s", e)
        semantic_score = 0.5  # Fallback
        await report_progress(0.6, f"Embedding failed — fallback score {semantic_score}")

    await report_progress(0.7, "Step 5: Phase 5 - Structural matching & classification")
    # --- Step 5: Phase 5 — Structural matching + risk classification ---
    from orion.analysis.structural_matcher import compute_structural_score
    from orion.analysis.risk_engine import classify
    
    match_result = compute_structural_score(
        requirement.constraints_extracted,
        test_case.assertions_extracted,
    )
    structural_score = match_result.structural_score
    await report_progress(0.75, f"Computed structural_score = {structural_score:.4f}")

    risk_result = classify(semantic_score, structural_score)
    await report_progress(0.8, f"Classified: status={risk_result.status}, risk_score={risk_result.risk_score:.4f}")

    await report_progress(0.85, "Step 6: Upsert traceability entry")
    # --- Step 6: Upsert traceability entry ---
    stmt = select(TraceabilityMatrix).where(
        TraceabilityMatrix.requirement_id == requirement.id,
        TraceabilityMatrix.test_case_id == test_case.id,
    )
    result = await session.execute(stmt)
    matrix_entry = result.scalar_one_or_none()

    if matrix_entry is None:
        matrix_entry = TraceabilityMatrix(
            id=uuid.uuid4(),
            requirement_id=requirement.id,
            test_case_id=test_case.id,
        )
        session.add(matrix_entry)

    matrix_entry.semantic_score = semantic_score
    matrix_entry.structural_score = structural_score
    matrix_entry.risk_score = risk_result.risk_score
    matrix_entry.confidence = risk_result.confidence
    matrix_entry.status = TraceabilityStatus(risk_result.status)
    await session.flush()
    await report_progress(0.9, "Upserted traceability matrix entry")

    # --- Step 7: Phase 7 — Verbalization (only for Partial/Drifted) ---
    await report_progress(0.95, "Step 7: Phase 7 - LLM Verbalization")
    if risk_result.status in ("Partial", "Drifted"):
        try:
            from orion.verbalization.service import verbalize_entry

            summary = await verbalize_entry(session, matrix_entry)
            if summary:
                await report_progress(0.98, "Generated LLM audit summary")
            else:
                await report_progress(0.98, "Verbalization returned no summary")
        except Exception as e:
            logger.warning("Verbalization failed: %s", e)
            matrix_entry.audit_summary = (
                f"This pair is classified as {risk_result.status} with "
                f"risk_score={risk_result.risk_score:.2f} "
                f"(semantic={semantic_score:.2f}, structural={structural_score:.2f})."
            )
            await report_progress(0.98, "Verbalization failed — using fallback")
    else:
        await report_progress(0.98, "Skipped verbalization (Covered)")

    await session.commit()
    await report_progress(1.0, "Simulation complete")

    # Reload with relations for response
    stmt = (
        select(TraceabilityMatrix)
        .options(
            selectinload(TraceabilityMatrix.requirement),
            selectinload(TraceabilityMatrix.test_case),
        )
        .where(TraceabilityMatrix.id == matrix_entry.id)
    )
    result = await session.execute(stmt)
    final_entry = result.scalar_one()

    from orion.dashboard.routes import _build_matrix_row
    
    return {
        "status": "ok",
        "requirement_id": str(requirement.id),
        "test_case_id": str(test_case.id),
        "matrix_entry": _build_matrix_row(final_entry).model_dump(),
        "pipeline_steps": steps,
    }
