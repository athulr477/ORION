"""Code-side structural extraction — parse test source with Python's ast module.

Extracts from test functions:
- Assertion comparisons: operators and literal values (assert x < 0.2)
- Function-call targets inside assertions (assert response.status_code == 200)
- pytest.raises exception types
- Fallback to docstring-only when AST parse fails
"""

from __future__ import annotations

import ast
import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

# Map AST comparison operators to human-readable strings
_CMP_OP_MAP: dict[type, str] = {
    ast.Eq: "==",
    ast.NotEq: "!=",
    ast.Lt: "<",
    ast.LtE: "<=",
    ast.Gt: ">",
    ast.GtE: ">=",
    ast.Is: "is",
    ast.IsNot: "is not",
    ast.In: "in",
    ast.NotIn: "not in",
}


@dataclass
class AssertionData:
    """A single assertion extracted from test code."""

    type: str  # "comparison", "call", "raises", "boolean"
    operator: str | None = None  # e.g. "<", "==", ">="
    left: str | None = None  # left-hand expression as string
    right: str | None = None  # right-hand expression as string
    value: Any = None  # literal numeric/string value if present
    function_call: str | None = None  # function/method being called
    exception_type: str | None = None  # for pytest.raises


@dataclass
class CodeExtractionResult:
    """All structural data extracted from a single test function."""

    function_name: str
    assertions: list[AssertionData] = field(default_factory=list)
    docstring: str | None = None
    fallback_used: bool = False

    def to_dict(self) -> dict:
        """Serialize to a JSON-compatible dict for storage in JSONB."""
        return {
            "function_name": self.function_name,
            "assertions": [
                {k: v for k, v in a.__dict__.items() if v is not None}
                for a in self.assertions
            ],
            "docstring": self.docstring,
            "fallback_used": self.fallback_used,
        }


# ---------------------------------------------------------------------------
# AST Helpers
# ---------------------------------------------------------------------------


def _expr_to_str(node: ast.expr) -> str:
    """Convert an AST expression node to a readable string representation."""
    try:
        return ast.unparse(node)
    except Exception:
        return "<unknown>"


def _extract_literal_value(node: ast.expr) -> Any:
    """Extract a literal value from an AST node, or None if not a literal."""
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        # Handle negative literals: -0.2, -100
        if isinstance(node.operand, ast.Constant) and isinstance(
            node.operand.value, (int, float)
        ):
            return -node.operand.value
    return None


def _extract_function_calls(node: ast.expr) -> list[str]:
    """Extract function/method call names from an expression."""
    calls: list[str] = []

    class _CallVisitor(ast.NodeVisitor):
        def visit_Call(self, n: ast.Call) -> None:  # noqa: N802
            if isinstance(n.func, ast.Attribute):
                calls.append(f"*.{n.func.attr}")
            elif isinstance(n.func, ast.Name):
                calls.append(n.func.id)
            self.generic_visit(n)

    _CallVisitor().visit(node)
    return calls


# ---------------------------------------------------------------------------
# Core extraction
# ---------------------------------------------------------------------------


class _AssertionVisitor(ast.NodeVisitor):
    """Walk a function body and extract assertion data."""

    def __init__(self) -> None:
        self.assertions: list[AssertionData] = []

    def visit_Assert(self, node: ast.Assert) -> None:  # noqa: N802
        """Process ``assert`` statements."""
        test = node.test
        self._extract_from_test_expr(test)
        self.generic_visit(node)

    def visit_With(self, node: ast.With) -> None:  # noqa: N802
        """Process ``with pytest.raises(...)`` blocks."""
        for item in node.items:
            ctx = item.context_expr
            if isinstance(ctx, ast.Call):
                func_str = _expr_to_str(ctx.func)
                if "pytest.raises" in func_str or "raises" in func_str:
                    exc_type = None
                    if ctx.args:
                        exc_type = _expr_to_str(ctx.args[0])
                    self.assertions.append(
                        AssertionData(
                            type="raises",
                            exception_type=exc_type,
                        )
                    )
        self.generic_visit(node)

    def _extract_from_test_expr(self, node: ast.expr) -> None:
        """Recursively extract assertions from a test expression."""
        # Comparison: assert x < 0.2, assert a == b
        if isinstance(node, ast.Compare):
            left = node.left
            for op, comparator in zip(node.ops, node.comparators, strict=False):
                op_str = _CMP_OP_MAP.get(type(op), str(type(op).__name__))
                left_str = _expr_to_str(left)
                right_str = _expr_to_str(comparator)
                literal_val = _extract_literal_value(comparator)
                if literal_val is None:
                    literal_val = _extract_literal_value(left)

                func_calls = _extract_function_calls(left) + _extract_function_calls(
                    comparator
                )

                self.assertions.append(
                    AssertionData(
                        type="comparison",
                        operator=op_str,
                        left=left_str,
                        right=right_str,
                        value=literal_val,
                        function_call=func_calls[0] if func_calls else None,
                    )
                )
                left = comparator  # For chained comparisons

        # Boolean operations: assert a and b, assert a or b
        elif isinstance(node, ast.BoolOp):
            for value in node.values:
                self._extract_from_test_expr(value)

        # Unary not: assert not x
        elif isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
            self._extract_from_test_expr(node.operand)

        # Bare call: assert some_function()
        elif isinstance(node, ast.Call):
            func_str = _expr_to_str(node.func)
            self.assertions.append(
                AssertionData(
                    type="call",
                    function_call=func_str,
                )
            )

        # Any other expression (bare name, attribute, etc.)
        else:
            self.assertions.append(
                AssertionData(
                    type="boolean",
                    left=_expr_to_str(node),
                )
            )


def _extract_assertions_python_ast(source_code: str, function_name: str = "") -> CodeExtractionResult:
    """Primary Python extraction path using the native ast.NodeVisitor.

    Parses the given source code with Python's built-in ``ast`` module and
    walks the function body with ``_AssertionVisitor``.  This is the canonical
    v1.0.0 extraction strategy for Python test files — deterministic, no
    external dependencies.

    Args:
        source_code: Source code of the test function (or full file slice).
        function_name: Expected function name (used in the result).

    Returns:
        CodeExtractionResult populated by the AST walk.
    """
    try:
        tree = ast.parse(source_code)
    except SyntaxError as exc:
        logger.warning(
            "ast.parse failed for function %r (%s) — using fallback",
            function_name, exc,
        )
        return CodeExtractionResult(function_name=function_name, fallback_used=True)

    # Walk the parsed tree for function definitions
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if function_name and node.name != function_name:
                continue
            docstring = ast.get_docstring(node)
            visitor = _AssertionVisitor()
            visitor.visit(node)
            return CodeExtractionResult(
                function_name=node.name,
                assertions=visitor.assertions,
                docstring=docstring,
                fallback_used=False,
            )

    # No matching function found — fall back gracefully
    visitor = _AssertionVisitor()
    visitor.visit(tree)
    return CodeExtractionResult(
        function_name=function_name,
        assertions=visitor.assertions,
        fallback_used=bool(not visitor.assertions),
    )


def extract_assertions(source_code: str, function_name: str = "", filename: str = "") -> CodeExtractionResult:
    """Parse a test function's source code and extract structural assertion data.

    **Primary path (Python):** uses the native ``ast.NodeVisitor`` (``_AssertionVisitor``)
    for deterministic, dependency-free extraction.  This is the v1.0.0 canonical mechanism.

    **Polyglot fallback:** for non-Python files (JS/TS/Java/Go), delegates to
    ``PolyglotExtractor`` (Tree-sitter) since the Python ``ast`` module cannot
    parse those languages.

    Args:
        source_code: Source code of the test function.
        function_name: Name of the test function.
        filename: Optional filename used to detect language for polyglot files.

    Returns:
        CodeExtractionResult with extracted assertions and metadata.
    """
    import os
    _, ext = os.path.splitext(filename or "")
    ext = ext.lower()

    # --- Primary path: native Python AST (v1.0.0 deterministic architecture) ---
    if ext in ("", ".py"):
        return _extract_assertions_python_ast(source_code, function_name=function_name)

    # --- Polyglot path: Tree-sitter for non-Python languages ---
    from orion.extraction.tree_sitter_engine import PolyglotExtractor
    results = PolyglotExtractor.extract(source_code, filename=filename, target_function=function_name)
    if results:
        return results[0]

    return CodeExtractionResult(function_name=function_name, fallback_used=True)


def extract_assertions_from_file(source_code: str, filename: str = "") -> list[CodeExtractionResult]:
    """Parse an entire test file and extract assertions for each test function.

    **Primary path (Python):** walks the AST with ``_AssertionVisitor`` per function.
    **Polyglot path:** delegates to Tree-sitter for JS/TS/Java/Go files.

    Args:
        source_code: Full source code of a test file.
        filename: Filename used to detect language.

    Returns:
        List of CodeExtractionResult, one per test function found.
    """
    import os
    _, ext = os.path.splitext(filename or "")
    ext = ext.lower()

    # --- Primary path: native Python AST ---
    if ext in ("", ".py"):
        try:
            tree = ast.parse(source_code)
        except SyntaxError as exc:
            logger.warning("ast.parse failed for file %r: %s", filename, exc)
            return []

        results: list[CodeExtractionResult] = []
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if not node.name.startswith("test_"):
                    continue
                docstring = ast.get_docstring(node)
                visitor = _AssertionVisitor()
                visitor.visit(node)
                results.append(
                    CodeExtractionResult(
                        function_name=node.name,
                        assertions=visitor.assertions,
                        docstring=docstring,
                        fallback_used=False,
                    )
                )
        return results

    # --- Polyglot path ---
    from orion.extraction.tree_sitter_engine import PolyglotExtractor
    return PolyglotExtractor.extract(source_code, filename=filename)
