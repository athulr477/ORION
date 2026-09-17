"""Build embedding input text with fallback for docstring-less tests.

Phase 4 spec: when a test has no docstring, embed
`function_name + assertion literals` instead of an empty string.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def build_requirement_text(title: str, description: str) -> str:
    """Build embedding input text for a requirement.

    Concatenates title and description, separated by a period.

    Args:
        title: Requirement title / summary.
        description: Full requirement description text.

    Returns:
        Combined text suitable for embedding.
    """
    parts = []
    if title:
        parts.append(title.strip().rstrip(".") + ".")
    if description:
        parts.append(description.strip())
    return " ".join(parts) if parts else ""


def build_test_text(
    function_name: str,
    docstring: str | None,
    source_code: str = "",
    assertions_extracted: dict | None = None,
) -> str:
    """Build embedding input text for a test case.

    Strategy:
    1. If docstring exists → use docstring (primary signal).
    2. If no docstring → build from function_name + assertion literals
       extracted by Phase 3 code extractor (fallback).

    Args:
        function_name: Test function name (e.g. "test_response_time").
        docstring: Test function docstring (may be None).
        source_code: Full source code of the test function.
        assertions_extracted: Phase 3 extraction result dict (from JSONB).

    Returns:
        Text suitable for embedding. Never empty.
    """
    # Primary: use docstring if available
    if docstring and docstring.strip():
        return docstring.strip()

    # Fallback: function name + assertion literals
    logger.debug(
        "No docstring for %s — using fallback embedding strategy",
        function_name,
    )
    parts: list[str] = []

    # Convert function name: test_response_time_under_load → "response time under load"
    readable_name = _function_name_to_text(function_name)
    if readable_name:
        parts.append(readable_name)

    # Extract assertion literals from Phase 3 data
    if assertions_extracted:
        assertion_text = _assertions_to_text(assertions_extracted)
        if assertion_text:
            parts.append(assertion_text)

    # Last resort: use source code snippets
    if not parts and source_code:
        # Take assert lines from source
        assert_lines = [
            line.strip()
            for line in source_code.splitlines()
            if line.strip().startswith("assert ")
        ]
        if assert_lines:
            parts.append(". ".join(assert_lines[:5]))

    result = ". ".join(parts) if parts else function_name
    return result


def _function_name_to_text(name: str) -> str:
    """Convert a test function name to readable text.

    ``test_response_time_under_load`` → ``response time under load``
    """
    # Strip test_ prefix
    text = name.removeprefix("test_")
    # Replace underscores with spaces
    text = text.replace("_", " ")
    return text.strip()


def _assertions_to_text(assertions_data: dict) -> str:
    """Convert Phase 3 assertion extraction data to readable text for embedding.

    Args:
        assertions_data: Dict from CodeExtractionResult.to_dict()

    Returns:
        Human-readable summary of assertions.
    """
    assertions = assertions_data.get("assertions", [])
    if not assertions:
        return ""

    parts: list[str] = []
    for a in assertions:
        a_type = a.get("type", "")

        if a_type == "comparison":
            left = a.get("left", "")
            op = a.get("operator", "")
            right = a.get("right", "")
            value = a.get("value")
            if left and op and right:
                parts.append(f"{left} {op} {right}")
            elif left and value is not None:
                parts.append(f"{left} {op} {value}")

        elif a_type == "raises":
            exc = a.get("exception_type", "exception")
            parts.append(f"raises {exc}")

        elif a_type == "call":
            func = a.get("function_call", "")
            if func:
                parts.append(f"calls {func}")

    return ". ".join(parts)
