"""Requirement-side structural extraction — rule-based constraint parsing.

Extracts structured constraints from natural language requirement text:
- Comparison operators: "greater than", "at least", "less than", "no more than", etc.
- Numeric thresholds: integers, floats, percentages, durations
- Boolean conditions: "must", "must not", "shall", "shall not"
- Units: ms, seconds, %, MB, etc.

This is a rule-based/regex approach (no LLM), consistent with the
"no LLM in the decision path" architectural constraint.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class ConstraintData:
    """A single constraint extracted from requirement text."""

    type: str  # "threshold", "boolean", "enum", "range"
    operator: str | None = None  # "==", "<", "<=", ">", ">=", "!="
    value: Any = None  # numeric or string value
    unit: str | None = None  # "ms", "seconds", "%", "MB", etc.
    subject: str | None = None  # what the constraint applies to
    polarity: str = "positive"  # "positive" (must) or "negative" (must not)
    raw_text: str = ""  # original matched text span


@dataclass
class RequirementExtractionResult:
    """All constraints extracted from a single requirement."""

    requirement_id: str = ""
    constraints: list[ConstraintData] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Serialize to a JSON-compatible dict for storage in JSONB."""
        return {
            "requirement_id": self.requirement_id,
            "constraints": [
                {k: v for k, v in c.__dict__.items() if v is not None}
                for c in self.constraints
            ],
            "keywords": self.keywords,
        }


# ---------------------------------------------------------------------------
# Operator patterns — map natural language to comparison operators
# ---------------------------------------------------------------------------

# Order matters: longer patterns first to avoid partial matches
_OPERATOR_PATTERNS: list[tuple[str, str]] = [
    # Negated / upper-bound patterns
    (r"must\s+not\s+exceed", "<="),
    (r"shall\s+not\s+exceed", "<="),
    (r"should\s+not\s+exceed", "<="),
    (r"cannot\s+exceed", "<="),
    (r"no\s+more\s+than", "<="),
    (r"no\s+greater\s+than", "<="),
    (r"no\s+longer\s+than", "<="),
    (r"no\s+larger\s+than", "<="),
    (r"not\s+exceed", "<="),
    (r"at\s+most", "<="),
    (r"up\s+to", "<="),
    (r"within", "<="),
    # Lower-bound patterns
    (r"at\s+least", ">="),
    (r"no\s+less\s+than", ">="),
    (r"no\s+fewer\s+than", ">="),
    (r"minimum\s+of", ">="),
    (r"a\s+minimum\s+of", ">="),
    # Strict inequality
    (r"greater\s+than", ">"),
    (r"more\s+than", ">"),
    (r"exceeds?", ">"),
    (r"above", ">"),
    (r"over", ">"),
    (r"less\s+than", "<"),
    (r"fewer\s+than", "<"),
    (r"under", "<"),
    (r"below", "<"),
    # Equality
    (r"equal\s+to", "=="),
    (r"equals?", "=="),
    (r"exactly", "=="),
    (r"is", "=="),
]

# ---------------------------------------------------------------------------
# Numeric + unit patterns
# ---------------------------------------------------------------------------

# Units we recognize (order: longer first)
_UNIT_PATTERN = (
    r"(?:milliseconds|seconds|minutes|hours|days|"
    r"ms|sec|min|hrs|"
    r"percent|%|"
    r"megabytes|kilobytes|gigabytes|bytes|"
    r"MB|KB|GB|TB|"
    r"requests?\s+per\s+second|req/s|rps|tps|"
    r"users?|connections?|retries|attempts|"
    r"characters?|chars?|items?|records?|rows?)"
)

# A number: integer or float, with optional comma separators
_NUMBER_PATTERN = r"(?:\d{1,3}(?:,\d{3})*(?:\.\d+)?|\d+(?:\.\d+)?)"


# ---------------------------------------------------------------------------
# Boolean condition patterns
# ---------------------------------------------------------------------------

_BOOLEAN_POSITIVE = [
    r"\bmust\b",
    r"\bshall\b",
    r"\bshould\b",
    r"\brequired\s+to\b",
    r"\bneeds?\s+to\b",
    r"\bhas\s+to\b",
    r"\bmandatory\b",
]

_BOOLEAN_NEGATIVE = [
    r"\bmust\s+not\b",
    r"\bshall\s+not\b",
    r"\bshould\s+not\b",
    r"\bmust\s+never\b",
    r"\bshall\s+never\b",
    r"\bprohibited\b",
    r"\bforbidden\b",
    r"\bnot\s+allowed\b",
]


# ---------------------------------------------------------------------------
# Core extraction
# ---------------------------------------------------------------------------


def _extract_threshold_constraints(text: str) -> list[ConstraintData]:
    """Extract numeric threshold constraints from requirement text.

    Looks for patterns like:
        "response time must be less than 200ms"
        "latency must not exceed 500 milliseconds"
        "at least 99.9% uptime"
        "within 150 milliseconds"
    """
    constraints: list[ConstraintData] = []
    text_lower = text.lower()

    for pattern_str, operator in _OPERATOR_PATTERNS:
        # Build regex: operator_pattern + optional words + number + optional unit
        full_pattern = (
            rf"({pattern_str})"
            rf"\s+"
            rf"({_NUMBER_PATTERN})"
            rf"\s*"
            rf"({_UNIT_PATTERN})?"
        )

        for match in re.finditer(full_pattern, text_lower, re.IGNORECASE):
            op_text = match.group(1)
            number_str = match.group(2).replace(",", "")
            unit = match.group(3)

            # Parse the numeric value
            try:
                value: int | float = (
                    float(number_str)
                    if "." in number_str
                    else int(number_str)
                )
            except ValueError:
                continue

            # Try to find the subject (what comes before the operator)
            subject = _find_subject_before(text_lower, match.start())

            constraints.append(
                ConstraintData(
                    type="threshold",
                    operator=operator,
                    value=value,
                    unit=unit,
                    subject=subject,
                    raw_text=match.group(0).strip(),
                )
            )

    return constraints


def _extract_boolean_constraints(text: str) -> list[ConstraintData]:
    """Extract boolean (must/must not) constraints."""
    constraints: list[ConstraintData] = []
    text_lower = text.lower()

    # Negative conditions first (to avoid "must not" matching "must")
    for pattern in _BOOLEAN_NEGATIVE:
        for match in re.finditer(pattern, text_lower):
            # Get context: the clause after the boolean keyword
            after = text_lower[match.end():match.end() + 80].strip()
            clause = after.split(".")[0].split(",")[0].strip()
            if clause:
                constraints.append(
                    ConstraintData(
                        type="boolean",
                        polarity="negative",
                        subject=clause,
                        raw_text=match.group(0) + " " + clause,
                    )
                )

    for pattern in _BOOLEAN_POSITIVE:
        for match in re.finditer(pattern, text_lower):
            # Skip if this is part of a "must not" already captured
            after_text = text_lower[match.end():match.end() + 10].strip()
            if after_text.startswith("not") or after_text.startswith("never"):
                continue

            after = text_lower[match.end():match.end() + 80].strip()
            clause = after.split(".")[0].split(",")[0].strip()
            if clause:
                constraints.append(
                    ConstraintData(
                        type="boolean",
                        polarity="positive",
                        subject=clause,
                        raw_text=match.group(0) + " " + clause,
                    )
                )

    return constraints


def _find_subject_before(text: str, pos: int) -> str | None:
    """Extract the likely subject noun phrase before a constraint operator.

    Heuristic: take the last clause segment before the operator position,
    stripping common verbs and articles.
    """
    before = text[:pos].strip()
    # Take the last sentence fragment
    for sep in [".", ";", ","]:
        idx = before.rfind(sep)
        if idx >= 0:
            before = before[idx + 1:].strip()
            break

    # Strip common leading words
    before = re.sub(
        r"^(?:the|a|an|its|their|all|each|every|this|that)\s+",
        "",
        before,
        flags=re.IGNORECASE,
    )
    # Strip trailing verbs like "must be", "should be", "is"
    before = re.sub(
        r"\s+(?:must|shall|should|is|are|be|been|being|have|has)\s*$",
        "",
        before,
        flags=re.IGNORECASE,
    )

    before = before.strip()
    return before if before else None


def _extract_keywords(text: str) -> list[str]:
    """Extract domain-relevant keywords from requirement text.

    These are used for keyword-overlap scoring and XAI heatmap display.
    """
    # Remove common stop words and extract meaningful terms
    stop_words = {
        "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
        "have", "has", "had", "do", "does", "did", "will", "would", "could",
        "should", "may", "might", "shall", "can", "must", "need", "to", "of",
        "in", "for", "on", "with", "at", "by", "from", "as", "into", "through",
        "during", "before", "after", "and", "but", "or", "nor", "not", "no",
        "so", "if", "then", "than", "that", "this", "these", "those", "it",
        "its", "they", "their", "them", "we", "our", "you", "your", "he", "she",
        "him", "her", "his",
    }

    # Tokenize: keep alphanumeric words 2+ chars
    words = re.findall(r"\b[a-zA-Z_][a-zA-Z0-9_]*\b", text.lower())
    keywords = [w for w in words if w not in stop_words and len(w) >= 2]

    # Deduplicate while preserving order
    seen: set[str] = set()
    unique: list[str] = []
    for kw in keywords:
        if kw not in seen:
            seen.add(kw)
            unique.append(kw)

    return unique


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def extract_constraints(
    text: str, requirement_id: str = ""
) -> RequirementExtractionResult:
    """Extract all structured constraints from a requirement text.

    This is the main entry point for requirement-side extraction.

    Args:
        text: Full requirement description text.
        requirement_id: Optional requirement ID for labeling.

    Returns:
        RequirementExtractionResult with extracted constraints and keywords.
    """
    result = RequirementExtractionResult(requirement_id=requirement_id)

    # Extract threshold constraints (numeric comparisons)
    result.constraints.extend(_extract_threshold_constraints(text))

    # Extract boolean constraints (must/must not)
    result.constraints.extend(_extract_boolean_constraints(text))

    # Extract keywords for semantic overlap
    result.keywords = _extract_keywords(text)

    logger.info(
        "Extracted %d constraints and %d keywords from %s",
        len(result.constraints),
        len(result.keywords),
        requirement_id or "requirement",
    )

    return result
