"""Payload parsers: Jira webhook, GitHub push, and @traces decorator extraction."""

from __future__ import annotations

import ast
import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data classes for parsed output
# ---------------------------------------------------------------------------


@dataclass
class RequirementData:
    """Parsed requirement data from a Jira webhook payload."""

    external_id: str
    title: str
    description: str
    source: str = "jira"
    raw_payload: dict | None = None
    changelog: list[dict] | None = None
    workspace_id: str | None = None


@dataclass
class TestFunctionData:
    """A single test function parsed from a Python source file."""

    function_name: str
    source_code: str
    docstring: str | None
    traced_requirements: list[str] = field(default_factory=list)
    start_line: int = 1
    end_line: int = 1


@dataclass
class TestFileData:
    """All test functions extracted from a single file."""

    file_path: str
    functions: list[TestFunctionData] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Jira payload parsing
# ---------------------------------------------------------------------------


def parse_jira_payload(payload: dict) -> RequirementData:
    """Extract requirement data from a Jira Cloud webhook payload.

    Handles both ``jira:issue_created`` and ``jira:issue_updated`` events.

    Args:
        payload: Raw Jira webhook JSON payload.

    Returns:
        RequirementData with external_id, title, description, and optional changelog.
    """
    issue = payload.get("issue", {})
    fields = issue.get("fields", {})

    external_id = issue.get("key", "")
    title = fields.get("summary", "")
    description = fields.get("description") or ""

    # Parse changelog for issue_updated events
    changelog_items = None
    changelog = payload.get("changelog")
    if changelog and "items" in changelog:
        changelog_items = [
            {
                "field": item.get("field", ""),
                "from": item.get("fromString"),
                "to": item.get("toString"),
            }
            for item in changelog["items"]
        ]

    return RequirementData(
        external_id=external_id,
        title=title,
        description=description,
        source="jira",
        raw_payload=payload,
        changelog=changelog_items,
    )


# ---------------------------------------------------------------------------
# @traces decorator extraction via AST
# ---------------------------------------------------------------------------


class _TracesVisitor(ast.NodeVisitor):
    """AST visitor that finds test functions decorated with @traces("REQ-xxx").

    Extracts:
        - Function name
        - Source code (reconstructed from AST line numbers)
        - Docstring
        - List of requirement IDs from @traces decorators
    """

    def __init__(self, source_lines: list[str]) -> None:
        self.source_lines = source_lines
        self.functions: list[TestFunctionData] = []

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:  # noqa: N802
        """Process function definitions, looking for @traces decorators."""
        if not node.name.startswith("test_"):
            self.generic_visit(node)
            return

        traced_reqs: list[str] = []
        for decorator in node.decorator_list:
            req_id = self._extract_traces_arg(decorator)
            if req_id:
                traced_reqs.append(req_id)

        # Extract source code from line numbers
        start = node.lineno - 1  # 0-indexed
        end = node.end_lineno if node.end_lineno else start + 1
        source_code = "\n".join(self.source_lines[start:end])

        # Extract docstring
        docstring = ast.get_docstring(node)

        self.functions.append(
            TestFunctionData(
                function_name=node.name,
                source_code=source_code,
                docstring=docstring,
                traced_requirements=traced_reqs,
                start_line=node.lineno,
                end_line=node.end_lineno or node.lineno,
            )
        )

        self.generic_visit(node)

    # Also handle async test functions
    visit_AsyncFunctionDef = visit_FunctionDef  # noqa: N815

    @staticmethod
    def _extract_traces_arg(decorator: ast.expr) -> str | None:
        """Extract the requirement ID from a @traces("REQ-123") decorator.

        Handles:
            - @traces("REQ-123")         → Call with string arg
            - @traces(req_id="REQ-123")  → Call with keyword arg
        """
        if not isinstance(decorator, ast.Call):
            return None

        # Check the function being called is named "traces"
        func = decorator.func
        if isinstance(func, ast.Name) and func.id == "traces" or isinstance(func, ast.Attribute) and func.attr == "traces":
            pass
        else:
            return None

        # Positional argument: @traces("REQ-123")
        if decorator.args:
            arg = decorator.args[0]
            if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                return arg.value

        # Keyword argument: @traces(req_id="REQ-123")
        for kw in decorator.keywords:
            if isinstance(kw.value, ast.Constant) and isinstance(kw.value, str):
                return kw.value

        return None


def extract_test_functions(source_code: str) -> list[TestFunctionData]:
    """Parse Python source code and extract test functions with @traces decorators.

    Args:
        source_code: Full Python source file content.

    Returns:
        List of TestFunctionData, one per test function found.
        Functions without @traces are still included (with empty traced_requirements).
    """
    try:
        tree = ast.parse(source_code)
    except SyntaxError:
        logger.warning("Failed to parse Python source — skipping file")
        return []

    source_lines = source_code.splitlines()
    visitor = _TracesVisitor(source_lines)
    visitor.visit(tree)
    return visitor.functions


# ---------------------------------------------------------------------------
# GitHub push payload parsing
# ---------------------------------------------------------------------------


def parse_github_push(payload: dict) -> list[str]:
    """Extract test file paths from a GitHub push event.

    Returns a deduplicated list of `.py` file paths that were added or
    modified and whose name contains "test".

    Args:
        payload: Raw GitHub push webhook JSON payload.

    Returns:
        List of test file paths (strings).
    """
    test_files: set[str] = set()
    for commit in payload.get("commits", []):
        for file_path in commit.get("added", []) + commit.get("modified", []):
            if file_path.endswith(".py") and "test" in file_path.lower():
                test_files.add(file_path)
    return sorted(test_files)
