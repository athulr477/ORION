"""Evidence tuple builder — deterministic assembly from Phases 5–6 output.

Builds the evidence tuple (requirement_delta, test_implementation_summary, status)
that the LLM will verbalize.  This module is purely deterministic — no LLM calls.

Only called for Partial/Drifted entries; returns None for Covered.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class EvidenceTuple:
    """Deterministic evidence assembled from Phases 5–6 for LLM verbalization.

    This is what the LLM receives as input — nothing more, nothing less.
    The LLM must not invent claims beyond what's in this tuple.
    """

    status: str  # "Partial" or "Drifted"
    risk_score: float
    semantic_score: float
    structural_score: float

    # From requirement
    requirement_id: str
    requirement_title: str
    requirement_summary: str  # title + key constraints

    # From test case
    test_function_name: str
    test_summary: str  # function name + key assertions

    # From Phase 6 delta (may be empty)
    delta_summary: str
    delta_change_count: int = 0
    delta_change_types: list[str] = field(default_factory=list)

    # Structural match info
    constraints_matched: int = 0
    constraints_total: int = 0

    def to_prompt_context(self) -> str:
        """Format evidence as the context block for the LLM prompt.

        This is the exact text the LLM sees — deterministic and constraining.
        """
        delta_text = self.delta_summary if self.delta_summary else "No requirement changes detected"

        match_text = (
            f"{self.constraints_matched}/{self.constraints_total} constraints matched"
            if self.constraints_total > 0
            else "No structural constraints to match"
        )

        return (
            f"- Status: {self.status} (risk_score={self.risk_score:.4f})\n"
            f"- Requirement: \"{self.requirement_summary}\"\n"
            f"- Test: \"{self.test_summary}\"\n"
            f"- Delta: {delta_text}\n"
            f"- Structural match: {self.structural_score:.4f} ({match_text})"
        )

    def to_fallback_sentence(self) -> str:
        """Generate a formatted sentence from evidence without LLM.

        Used when Ollama is unavailable — produces a readable but mechanical
        summary directly from the evidence fields.
        """
        parts = [f"This requirement-test pair is classified as {self.status}"]
        parts.append(f"(risk_score={self.risk_score:.4f})")

        if self.delta_summary:
            parts.append(f"because {self.delta_summary.lower()}")
        elif self.structural_score < 0.4:
            parts.append(
                f"due to low structural match "
                f"({self.constraints_matched}/{self.constraints_total} constraints matched)"
            )
        elif self.semantic_score < 0.5:
            parts.append("due to low semantic similarity between requirement and test")
        else:
            parts.append("based on combined semantic and structural analysis")

        return " ".join(parts) + "."

    def to_dict(self) -> dict:
        """Serialize for logging/debugging."""
        return {
            "status": self.status,
            "risk_score": round(self.risk_score, 4),
            "semantic_score": round(self.semantic_score, 4),
            "structural_score": round(self.structural_score, 4),
            "requirement_id": self.requirement_id,
            "requirement_title": self.requirement_title,
            "requirement_summary": self.requirement_summary,
            "test_function_name": self.test_function_name,
            "test_summary": self.test_summary,
            "delta_summary": self.delta_summary,
            "delta_change_count": self.delta_change_count,
            "delta_change_types": self.delta_change_types,
            "constraints_matched": self.constraints_matched,
            "constraints_total": self.constraints_total,
        }


# ---------------------------------------------------------------------------
# Helper: summarize constraints / assertions for the evidence tuple
# ---------------------------------------------------------------------------


def _summarize_constraints(constraints_data: dict | None) -> str:
    """Build a readable summary of requirement constraints for the evidence tuple."""
    if not constraints_data:
        return ""

    constraints = constraints_data.get("constraints", [])
    if not constraints:
        return ""

    parts: list[str] = []
    for c in constraints[:5]:  # Cap at 5 for prompt brevity
        raw = c.get("raw_text", "")
        if raw:
            parts.append(raw.strip())
        else:
            op = c.get("operator", "")
            val = c.get("value", "")
            unit = c.get("unit", "")
            subject = c.get("subject", "")
            parts.append(f"{subject} {op} {val} {unit}".strip())

    return "; ".join(parts)


def _summarize_assertions(assertions_data: dict | None) -> str:
    """Build a readable summary of test assertions for the evidence tuple."""
    if not assertions_data:
        return ""

    assertions = assertions_data.get("assertions", [])
    if not assertions:
        return ""

    parts: list[str] = []
    for a in assertions[:5]:  # Cap at 5 for prompt brevity
        a_type = a.get("type", "")
        if a_type == "comparison":
            left = a.get("left", "")
            op = a.get("operator", "")
            right = a.get("right", "")
            if left and op and right:
                parts.append(f"assert {left} {op} {right}")
        elif a_type == "raises":
            exc = a.get("exception_type", "exception")
            parts.append(f"pytest.raises({exc})")
        elif a_type == "call":
            func = a.get("function_call", "")
            if func:
                parts.append(f"calls {func}")

    return "; ".join(parts)


def _summarize_delta(delta_data: dict | None) -> str:
    """Build a readable summary of requirement delta for the evidence tuple."""
    if not delta_data:
        return ""

    changes = delta_data.get("changes", [])
    if not changes:
        return ""

    parts: list[str] = []
    for change in changes[:5]:  # Cap at 5 for prompt brevity
        details = change.get("details", "")
        if details:
            parts.append(details)
        else:
            ctype = change.get("type", "unknown")
            parts.append(f"{ctype} detected")

    return "; ".join(parts)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def build_evidence_tuple(
    *,
    status: str,
    risk_score: float,
    semantic_score: float,
    structural_score: float,
    requirement_external_id: str,
    requirement_title: str,
    requirement_description: str,
    requirement_constraints: dict | None,
    test_function_name: str,
    test_assertions: dict | None,
    requirement_delta: dict | None,
    structural_match_details: dict | None = None,
) -> EvidenceTuple | None:
    """Build the deterministic evidence tuple from Phases 5–6 output.

    Only builds for Partial/Drifted entries. Returns None for Covered.

    Args:
        status: Classification from Phase 5 ("Covered", "Partial", "Drifted").
        risk_score: Combined risk score from Phase 5.
        semantic_score: Cosine similarity from Phase 4.
        structural_score: Structural match score from Phase 5.
        requirement_external_id: Source-system requirement ID.
        requirement_title: Requirement title.
        requirement_description: Full requirement description text.
        requirement_constraints: Phase 3 extracted constraints dict.
        test_function_name: Test function name.
        test_assertions: Phase 3 extracted assertions dict.
        requirement_delta: Phase 6 structured delta dict (may be None).
        structural_match_details: Optional match details from structural matcher.

    Returns:
        EvidenceTuple for Partial/Drifted, None for Covered.
    """
    # Short-circuit: Covered entries don't need verbalization
    if status == "Covered":
        logger.debug(
            "Skipping evidence tuple for Covered entry %s",
            requirement_external_id,
        )
        return None

    # Build requirement summary
    constraint_text = _summarize_constraints(requirement_constraints)
    req_summary = requirement_title
    if constraint_text:
        req_summary += f". Constraints: {constraint_text}"

    # Build test summary
    assertion_text = _summarize_assertions(test_assertions)
    test_summary = test_function_name
    if assertion_text:
        test_summary += f". Assertions: {assertion_text}"

    # Build delta summary
    delta_summary = _summarize_delta(requirement_delta)
    delta_change_count = len(requirement_delta.get("changes", [])) if requirement_delta else 0
    delta_change_types = requirement_delta.get("change_types", []) if requirement_delta else []

    # Extract structural match counts
    constraints_matched = 0
    constraints_total = 0
    if structural_match_details:
        constraints_matched = structural_match_details.get("matched", 0)
        constraints_total = structural_match_details.get("requirement_constraints", 0)
    elif requirement_constraints:
        constraints_total = len(requirement_constraints.get("constraints", []))

    evidence = EvidenceTuple(
        status=status,
        risk_score=risk_score,
        semantic_score=semantic_score,
        structural_score=structural_score,
        requirement_id=requirement_external_id,
        requirement_title=requirement_title,
        requirement_summary=req_summary,
        test_function_name=test_function_name,
        test_summary=test_summary,
        delta_summary=delta_summary,
        delta_change_count=delta_change_count,
        delta_change_types=delta_change_types,
        constraints_matched=constraints_matched,
        constraints_total=constraints_total,
    )

    logger.info(
        "Built evidence tuple for %s (%s, risk=%.4f, delta_changes=%d)",
        requirement_external_id,
        status,
        risk_score,
        delta_change_count,
    )

    return evidence
