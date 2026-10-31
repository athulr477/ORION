"""Structural matcher — compare requirement constraints against test assertions.

Matches Phase 3 requirement-side constraints (operators, thresholds, units)
against Phase 3 code-side assertions (comparison operators, literal values)
to produce a `structural_score` in [0, 1].

Matching strategy:
1. For each requirement constraint, find the best-matching test assertion.
2. A match is scored based on: operator compatibility, value proximity, and
   keyword/subject overlap.
3. Optimal assignment is found via the Hungarian algorithm (Kuhn-Munkres)
   to maximize total match score across all constraint-assertion pairs.
4. structural_score is the F1 harmonic mean of match_quality (avg of matched
   scores) and match_coverage (fraction of constraints matched), providing
   a balanced measure that separates *how well* matches align from *how many*
   constraints are covered.
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
    match_quality: float = 0.0
    match_coverage: float = 0.0
    match_details: list[MatchDetail] = field(default_factory=list)
    requirement_constraint_count: int = 0
    test_assertion_count: int = 0
    matched_count: int = 0

    def to_dict(self) -> dict:
        """Serialize for JSONB storage or API response."""
        return {
            "structural_score": round(self.structural_score, 4),
            "match_quality": round(self.match_quality, 4),
            "match_coverage": round(self.match_coverage, 4),
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


def _value_score(
    req_value, test_value, req_unit: str | None = None, test_unit: str | None = None
) -> float:
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

    r_unit = _normalize_unit(req_unit)
    t_unit = _normalize_unit(test_unit)

    def to_base(val: float, unit: str) -> float:
        if unit == "s":
            return val * 1000.0
        if unit == "min":
            return val * 60000.0
        if unit == "h":
            return val * 3600000.0
        if unit == "kb":
            return val * 1024.0
        if unit == "mb":
            return val * 1048576.0
        if unit == "gb":
            return val * 1073741824.0
        return val

    rv_base = to_base(rv, r_unit)
    tv_base = to_base(tv, t_unit)

    def get_rel_diff(v1: float, v2: float) -> float:
        if v1 == v2:
            return 0.0
        return abs(v1 - v2) / max(abs(v1), abs(v2), 1e-9)

    rel_diff = min(get_rel_diff(rv, tv), get_rel_diff(rv_base, tv_base))

    # Fallbacks for implicit units
    if not t_unit and r_unit == "ms":
        rel_diff = min(rel_diff, get_rel_diff(rv, tv * 1000.0))
    if not t_unit and r_unit == "b":
        rel_diff = min(rel_diff, get_rel_diff(rv, tv * 1024.0))

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

    Uses Dice coefficient (2·|R∩T| / (|R|+|T|)) instead of Jaccard.
    Dice is less sensitive to vocabulary expansion — important because
    code identifiers and natural language diverge in token sets.

    Reference: van Rijsbergen, C.J. (1979). Information Retrieval.
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
    denominator = len(req_words) + len(test_words)
    return (2.0 * len(intersection)) / denominator if denominator > 0 else 0.0


# ---------------------------------------------------------------------------
# Hungarian (Kuhn-Munkres) algorithm — pure Python, no scipy dependency
# ---------------------------------------------------------------------------


def _hungarian_maximize(score_matrix: list[list[float]]) -> list[tuple[int, int]]:
    """Find the maximum-weight matching in a bipartite graph.

    Uses the Hungarian (Kuhn-Munkres) algorithm on a cost matrix.
    Since we want to *maximize* total score, we negate the scores
    and solve the standard minimum-cost assignment.

    Args:
        score_matrix: n×m matrix where score_matrix[i][j] is the score
                      of assigning row i to column j. Values in [0, 1].

    Returns:
        List of (row, col) pairs forming the optimal assignment.
        Length = min(n, m).
    """
    if not score_matrix or not score_matrix[0]:
        return []

    n = len(score_matrix)
    m = len(score_matrix[0])

    # Pad to square matrix if needed
    size = max(n, m)
    # Convert to cost matrix (negate for minimization), pad with zeros
    cost = [[0.0] * size for _ in range(size)]
    max_val = 0.0
    for i in range(n):
        for j in range(m):
            max_val = max(max_val, score_matrix[i][j])

    for i in range(n):
        for j in range(m):
            cost[i][j] = max_val - score_matrix[i][j]

    # Hungarian algorithm (Kuhn-Munkres) for square cost matrix
    INF = float("inf")

    # u[i], v[j] — potentials for rows and columns
    u = [0.0] * (size + 1)
    v = [0.0] * (size + 1)
    # p[j] — which row is assigned to column j (1-indexed, 0 = unassigned)
    p = [0] * (size + 1)
    # way[j] — which column leads to column j in the shortest augmenting path
    way = [0] * (size + 1)

    for i in range(1, size + 1):
        p[0] = i
        j0 = 0  # virtual column
        min_v = [INF] * (size + 1)
        used = [False] * (size + 1)

        while True:
            used[j0] = True
            i0 = p[j0]
            delta = INF
            j1 = -1

            for j in range(1, size + 1):
                if not used[j]:
                    cur = cost[i0 - 1][j - 1] - u[i0] - v[j]
                    if cur < min_v[j]:
                        min_v[j] = cur
                        way[j] = j0
                    if min_v[j] < delta:
                        delta = min_v[j]
                        j1 = j

            for j in range(size + 1):
                if used[j]:
                    u[p[j]] += delta
                    v[j] -= delta
                else:
                    min_v[j] -= delta

            j0 = j1
            if p[j0] == 0:
                break

        # Reconstruct path
        while j0:
            p[j0] = p[way[j0]]
            j0 = way[j0]

    # Extract assignments (only those within original matrix bounds)
    result: list[tuple[int, int]] = []
    for j in range(1, size + 1):
        if p[j] != 0:
            row = p[j] - 1
            col = j - 1
            if row < n and col < m:
                result.append((row, col))

    return result


# ---------------------------------------------------------------------------
# Main matching logic
# ---------------------------------------------------------------------------


def _match_constraint_to_assertion(
    constraint: dict, assertion: dict, c_idx: int, a_idx: int
) -> MatchDetail:
    """Score how well a single constraint matches a single assertion.

    Weights: operator 0.3, value 0.5, keyword 0.2

    Value proximity receives the highest weight because in real-world
    requirement tracing, the numeric threshold is the most discriminative
    signal (e.g., "< 200ms" vs "< 500ms" are fundamentally different
    requirements even with identical operators and subjects).
    """
    # Extract fields from constraint (Phase 3 requirement extractor output)
    req_op = constraint.get("operator")
    req_value = constraint.get("value")
    req_unit = constraint.get("unit")
    req_subject = constraint.get("subject", "")

    # Extract fields from assertion (Phase 3 code extractor output)
    test_op = assertion.get("operator")
    test_value = assertion.get("value")
    test_unit = assertion.get("unit")
    test_left = assertion.get("left", "")

    # Score components
    op_score = _operator_score(req_op, test_op)
    val_score = _value_score(req_value, test_value, req_unit, test_unit)
    kw_score = _keyword_overlap(req_subject, test_left)

    # Bonus: if the assertion type is "raises" and the constraint is boolean/negative,
    # give partial credit
    if assertion.get("type") == "raises" and constraint.get("polarity") == "negative":
        op_score = max(op_score, 0.5)
        val_score = max(val_score, 0.3)

    # Weighted combination: value-dominant split (0.3 op / 0.5 val / 0.2 kw)
    combined = 0.3 * op_score + 0.5 * val_score + 0.2 * kw_score

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

    Uses the Hungarian algorithm for optimal bipartite matching, then computes
    structural_score as the F1 harmonic mean of match_quality and match_coverage.

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
    threshold_constraints = [c for c in constraints if c.get("type") == "threshold"]
    # Filter to comparison assertions (most structurally matchable)
    comparison_assertions = [a for a in assertions if a.get("type") in ("comparison", "raises")]

    result.requirement_constraint_count = len(threshold_constraints)
    result.test_assertion_count = len(comparison_assertions)

    if not threshold_constraints:
        # No threshold constraints to match — structural alignment is indeterminate.
        # Use 0.5 as a neutral prior so the semantic score dominates classification.
        # Returning 1.0 here would falsely collapse Drifted pairs (whose boolean-only
        # requirements produce no threshold constraints) into the Partial band.
        result.structural_score = 0.5
        return result

    if not comparison_assertions:
        result.structural_score = 0.0
        return result

    # Build the full score matrix: constraints × assertions
    n_constraints = len(threshold_constraints)
    score_matrix: list[list[float]] = []
    match_cache: dict[tuple[int, int], MatchDetail] = {}

    for c_idx, constraint in enumerate(threshold_constraints):
        row: list[float] = []
        for a_idx, assertion in enumerate(comparison_assertions):
            match = _match_constraint_to_assertion(constraint, assertion, c_idx, a_idx)
            match_cache[(c_idx, a_idx)] = match
            row.append(match.combined_score)
        score_matrix.append(row)

    # Find optimal assignment via Hungarian algorithm
    assignment = _hungarian_maximize(score_matrix)

    # Collect matched pairs (only those above the minimum threshold)
    matched_scores: list[float] = []
    for c_idx, a_idx in assignment:
        score = score_matrix[c_idx][a_idx]
        if score > 0.1:  # Minimum threshold to count as a match
            match_detail = match_cache[(c_idx, a_idx)]
            result.match_details.append(match_detail)
            matched_scores.append(score)
            result.matched_count += 1

    # Compute structural score from match quality and coverage
    if matched_scores:
        match_quality = sum(matched_scores) / len(matched_scores)
        match_coverage = len(matched_scores) / n_constraints

        result.match_quality = match_quality
        result.match_coverage = match_coverage

        # Balanced structural alignment:
        # Emphasizes quality of the verified constraint, with coverage weight
        result.structural_score = 0.7 * match_quality + 0.3 * match_coverage
    else:
        result.structural_score = 0.0

    # Clamp to [0, 1]
    result.structural_score = max(0.0, min(1.0, result.structural_score))

    return result
