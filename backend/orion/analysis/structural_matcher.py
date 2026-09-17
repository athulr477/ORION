"""Structural matcher — compare requirement constraints against test assertions.

Matches Phase 3 requirement-side constraints (operators, thresholds, units)
against Phase 3 code-side assertions (comparison operators, literal values)
to produce a `structural_score` in [0, 1].

Matching strategy:
1. For each requirement constraint, find the best-matching test assertion.
2. A match is scored based on: operator compatibility, value proximity, and
   keyword/subject overlap.
3. The structural_score is the average best-match score across all constraints.
   If there are no constraints, structural_score defaults to 0.0.
"""

from __future__ import annotations

import logging
import math
import re
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Operator compatibility matrix
# ---------------------------------------------------------------------------

# How well two operators match: 1.0 = exact, 0.5 = compatible direction, 0.0 = incompatible
_OPERATOR_COMPAT: dict[tuple[str, str], float] = {
    # Exact matches
    ("<", "<"): 1.0,
    ("<=", "<="): 1.0,
    (">", ">"): 1.0,
    (">=", ">="): 1.0,
    ("==", "=="): 1.0,
    ("!=", "!="): 1.0,
    # Compatible directions
    ("<", "<="): 0.8,
    ("<=", "<"): 0.8,
    (">", ">="): 0.8,
    (">=", ">"): 0.8,
    # Opposite-but-related (test might check the boundary differently)
    ("<", ">="): 0.3,
    (">=", "<"): 0.3,
    (">", "<="): 0.3,
    ("<=", ">"): 0.3,
    # Equality vs inequality
    ("==", "<="): 0.5,
    ("<=", "=="): 0.5,
    ("==", ">="): 0.5,
    (">=", "=="): 0.5,
    ("==", "<"): 0.4,
    ("<", "=="): 0.4,
    ("==", ">"): 0.4,
    (">", "=="): 0.4,
}


@dataclass
class MatchDetail:
    """Details of a single constraint-to-assertion match."""

    constraint_index: int
    assertion_index: int
    operator_score: float = 0.0
    value_score: float = 0.0
    keyword_score: float = 0.0
    combined_score: float = 0.0


@dataclass
class StructuralMatchResult:
    """Result of structural matching between a requirement and a test."""

    structural_score: float = 0.0
    match_details: list[MatchDetail] = field(default_factory=list)
    requirement_constraint_count: int = 0
    test_assertion_count: int = 0
    matched_count: int = 0

    def to_dict(self) -> dict:
        """Serialize for JSONB storage or API response."""
        return {
            "structural_score": round(self.structural_score, 4),
            "requirement_constraints": self.requirement_constraint_count,
            "test_assertions": self.test_assertion_count,
            "matched": self.matched_count,
            "details": [
                {
                    "constraint_idx": d.constraint_index,
                    "assertion_idx": d.assertion_index,
                    "operator_score": round(d.operator_score, 3),
                    "value_score": round(d.value_score, 3),
                    "keyword_score": round(d.keyword_score, 3),
                    "combined": round(d.combined_score, 3),
                }
                for d in self.match_details
            ],
        }


# ---------------------------------------------------------------------------
# Scoring functions
# ---------------------------------------------------------------------------


def _operator_score(req_op: str | None, test_op: str | None) -> float:
    """Score how well two operators match."""
    if req_op is None or test_op is None:
        return 0.0
    key = (req_op, test_op)
    if key in _OPERATOR_COMPAT:
        return _OPERATOR_COMPAT[key]
    # Reverse lookup
    rev_key = (test_op, req_op)
    if rev_key in _OPERATOR_COMPAT:
        return _OPERATOR_COMPAT[rev_key]
    return 0.0


def _value_score(req_value, test_value) -> float:
    """Score how close two numeric values are.

    Uses exponential decay based on relative difference:
    - Exact match → 1.0
    - 10% off → ~0.9
    - 50% off → ~0.6
    - 100% off → ~0.37
    """
    if req_value is None or test_value is None:
        return 0.0

    try:
        rv = float(req_value)
        tv = float(test_value)
    except (ValueError, TypeError):
        # String comparison
        return 1.0 if str(req_value) == str(test_value) else 0.0

    if rv == tv:
        return 1.0

    # Relative difference
    denom = max(abs(rv), abs(tv), 1e-9)
    rel_diff = abs(rv - tv) / denom
    return math.exp(-2.0 * rel_diff)


def _normalize_unit(unit: str | None) -> str:
    """Normalize unit strings for comparison."""
    if unit is None:
        return ""
    unit = unit.lower().strip()
    mapping = {
        "milliseconds": "ms",
        "seconds": "s",
        "sec": "s",
        "minutes": "min",
        "hours": "h",
        "hrs": "h",
        "percent": "%",
        "megabytes": "mb",
        "kilobytes": "kb",
        "gigabytes": "gb",
        "bytes": "b",
    }
    return mapping.get(unit, unit)


def _keyword_overlap(req_subject: str | None, test_left: str | None) -> float:
    """Score keyword overlap between requirement subject and test expression.

    Extracts words from both and computes Jaccard similarity.
    """
    if not req_subject or not test_left:
        return 0.0

    def _extract_words(text: str) -> set[str]:
        return {w.lower() for w in re.findall(r"[a-zA-Z_]\w*", text) if len(w) >= 2}

    req_words = _extract_words(req_subject)
    test_words = _extract_words(test_left)

    if not req_words or not test_words:
        return 0.0

    intersection = req_words & test_words
    union = req_words | test_words
    return len(intersection) / len(union) if union else 0.0


# ---------------------------------------------------------------------------
# Main matching logic
# ---------------------------------------------------------------------------


def _match_constraint_to_assertion(
    constraint: dict, assertion: dict, c_idx: int, a_idx: int
) -> MatchDetail:
    """Score how well a single constraint matches a single assertion.

    Weights: operator 0.4, value 0.4, keyword 0.2
    """
    # Extract fields from constraint (Phase 3 requirement extractor output)
    req_op = constraint.get("operator")
    req_value = constraint.get("value")
    req_unit = constraint.get("unit")
    req_subject = constraint.get("subject", "")

    # Extract fields from assertion (Phase 3 code extractor output)
    test_op = assertion.get("operator")
    test_value = assertion.get("value")
    test_left = assertion.get("left", "")
    test_right = assertion.get("right", "")

    # Score components
    op_score = _operator_score(req_op, test_op)
    val_score = _value_score(req_value, test_value)
    kw_score = _keyword_overlap(req_subject, test_left)

    # Bonus: if the assertion type is "raises" and the constraint is boolean/negative,
    # give partial credit
    if assertion.get("type") == "raises" and constraint.get("polarity") == "negative":
        op_score = max(op_score, 0.5)
        val_score = max(val_score, 0.3)

    # Weighted combination
    combined = 0.4 * op_score + 0.4 * val_score + 0.2 * kw_score

    return MatchDetail(
        constraint_index=c_idx,
        assertion_index=a_idx,
        operator_score=op_score,
        value_score=val_score,
        keyword_score=kw_score,
        combined_score=combined,
    )


def compute_structural_score(
    requirement_constraints: dict | None,
    test_assertions: dict | None,
) -> StructuralMatchResult:
    """Compute the structural match score between requirement constraints and test assertions.

    For each requirement constraint, finds the best-matching test assertion.
    The structural_score is the average of the best match scores.

    Args:
        requirement_constraints: Phase 3 RequirementExtractionResult.to_dict()
        test_assertions: Phase 3 CodeExtractionResult.to_dict()

    Returns:
        StructuralMatchResult with score and match details.
    """
    result = StructuralMatchResult()

    # Extract the constraint/assertion lists
    constraints = (requirement_constraints or {}).get("constraints", [])
    assertions = (test_assertions or {}).get("assertions", [])

    # Filter to only threshold constraints (most structurally matchable)
    threshold_constraints = [
        c for c in constraints if c.get("type") == "threshold"
    ]
    # Filter to comparison assertions (most structurally matchable)
    comparison_assertions = [
        a for a in assertions if a.get("type") in ("comparison", "raises")
    ]

    result.requirement_constraint_count = len(threshold_constraints)
    result.test_assertion_count = len(comparison_assertions)

    if not threshold_constraints:
        # No constraints to match — can't compute structural score
        # Use a heuristic: if there are any assertions at all, give partial credit
        if comparison_assertions:
            result.structural_score = 0.3  # Some test structure exists
        else:
            result.structural_score = 0.0
        return result

    if not comparison_assertions:
        result.structural_score = 0.0
        return result

    # For each constraint, find the best matching assertion
    best_scores: list[float] = []
    used_assertions: set[int] = set()

    for c_idx, constraint in enumerate(threshold_constraints):
        best_match: MatchDetail | None = None
        best_score = -1.0

        for a_idx, assertion in enumerate(comparison_assertions):
            match = _match_constraint_to_assertion(constraint, assertion, c_idx, a_idx)
            if match.combined_score > best_score:
                best_score = match.combined_score
                best_match = match

        if best_match and best_score > 0.1:  # Minimum threshold to count as a match
            result.match_details.append(best_match)
            best_scores.append(best_score)
            used_assertions.add(best_match.assertion_index)
            result.matched_count += 1

    # Structural score = average of best match scores
    if best_scores:
        result.structural_score = sum(best_scores) / len(threshold_constraints)
    else:
        result.structural_score = 0.0

    # Clamp to [0, 1]
    result.structural_score = max(0.0, min(1.0, result.structural_score))

    return result
