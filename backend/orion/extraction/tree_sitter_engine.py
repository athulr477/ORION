"""Tree-sitter based polyglot code extraction engine.

Supports Python, JavaScript, TypeScript, Java, and Go.
Extracts function names, docstrings/comments, and assertions.
"""

from __future__ import annotations

import logging

import tree_sitter
import tree_sitter_go
import tree_sitter_java
import tree_sitter_javascript
import tree_sitter_python
import tree_sitter_typescript

from orion.extraction.code_extractor import AssertionData, CodeExtractionResult

logger = logging.getLogger(__name__)

# Cache language instances
_LANGUAGES = {
    "python": tree_sitter.Language(tree_sitter_python.language()),
    "javascript": tree_sitter.Language(tree_sitter_javascript.language()),
    "typescript": tree_sitter.Language(tree_sitter_typescript.language_typescript()),
    "java": tree_sitter.Language(tree_sitter_java.language()),
    "go": tree_sitter.Language(tree_sitter_go.language()),
}

# Determine language from extension
_EXTENSION_MAP = {
    ".py": "python",
    ".js": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".java": "java",
    ".go": "go",
}

# --- Tree-sitter Queries ---

# Python Queries
_PY_QUERY = """
(function_definition
  name: (identifier) @func_name
  body: (block
    (expression_statement (string) @docstring)?
  )
) @function

(assert_statement
  (comparison_operator
    (_) @left
    ["==" "!=" "<" "<=" ">" ">=" "is" "is not" "in" "not in"] @op
    (_) @right
  )
) @assert.comparison

(assert_statement
  (call
    function: (_) @func_call
  )
) @assert.call

(assert_statement
  (identifier) @bool_var
) @assert.boolean
"""

# JavaScript / TypeScript Queries (Jest / Mocha / Chai / Node assert)
_JS_TS_QUERY = """
(call_expression
  function: (identifier) @test_func (#match? @test_func "^(it|test)$")
  arguments: (arguments
    (string) @func_name
    (arrow_function)
  )
) @function

(function_declaration
  name: (identifier) @func_name
) @function

(expression_statement
  (call_expression
    function: (member_expression
      object: (call_expression
        function: (identifier) @expect_func (#eq? @expect_func "expect")
        arguments: (arguments (_) @left)
      )
      property: (property_identifier) @matcher
    )
    arguments: (arguments (_) @right)?
  )
) @assert.jest

(call_expression
  function: (member_expression
    object: (identifier) @assert_mod (#eq? @assert_mod "assert")
    property: (property_identifier) @assert_meth
  )
  arguments: (arguments (_) @left (_) @right?)
) @assert.node
"""

# Java Queries (JUnit)
_JAVA_QUERY = """
(method_declaration
  name: (identifier) @func_name
) @function

(method_invocation
  name: (identifier) @assert_meth (#match? @assert_meth "^assert")
  arguments: (argument_list (_) @left (_) @right?)
) @assert.junit
"""

# Go Queries (testing)
_GO_QUERY = """
(function_declaration
  name: (identifier) @func_name
) @function

(call_expression
  function: (selector_expression
    operand: (identifier) @pkg (#match? @pkg "^(t|assert)$")
    field: (field_identifier) @assert_meth
  )
  arguments: (argument_list (_) @left (_) @right?)
) @assert.go
"""

_QUERIES = {
    "python": _PY_QUERY,
    "javascript": _JS_TS_QUERY,
    "typescript": _JS_TS_QUERY,
    "java": _JAVA_QUERY,
    "go": _GO_QUERY,
}


def _get_node_text(node: tree_sitter.Node, source_code: bytes) -> str:
    """Extract text from a node."""
    return source_code[node.start_byte:node.end_byte].decode("utf8")


class PolyglotExtractor:
    """Extracts structural AST features across multiple languages using Tree-sitter."""

    @classmethod
    def get_language(cls, filename: str | None = None) -> str:
        """Detect language from filename, defaulting to python."""
        if not filename:
            return "python"
        
        import os
        _, ext = os.path.splitext(filename)
        return _EXTENSION_MAP.get(ext.lower(), "python")

    @classmethod
    def extract(cls, source_code: str, filename: str = "", target_function: str = "") -> list[CodeExtractionResult]:
        """Extract assertions and metadata from code.
        
        Returns a list of CodeExtractionResult. If target_function is specified,
        only returns results for that function.
        """
        language_name = cls.get_language(filename)
        language = _LANGUAGES[language_name]
        parser = tree_sitter.Parser(language)
        
        source_bytes = source_code.encode("utf8")
        tree = parser.parse(source_bytes)
        
        query_str = _QUERIES.get(language_name, _PY_QUERY)
        try:
            query = tree_sitter.Query(language, query_str)
        except ValueError as e:
            logger.error("Tree-sitter query failed for %s: %s", language_name, e)
            return []
            
        cursor = tree_sitter.QueryCursor(query)
        captures_dict = cursor.captures(tree.root_node)
        
        # We need to map captures to the specific function they belong to
        functions: dict[tree_sitter.Node, CodeExtractionResult] = {}
        
        # 1. Identify all functions
        if "function" in captures_dict:
            for node in captures_dict["function"]:
                func_name = "<unknown>"
                
                # We need to find the specific captures for this node
                # query.matches or cursor.captures on the node itself
                node_cursor = tree_sitter.QueryCursor(query)
                node_captures = node_cursor.captures(node)
                
                if "func_name" in node_captures and node_captures["func_name"]:
                    func_name = _get_node_text(node_captures["func_name"][0], source_bytes)
                
                if target_function and func_name != target_function:
                    continue
                    
                docstring = None
                if "docstring" in node_captures and node_captures["docstring"]:
                    docstring = _get_node_text(node_captures["docstring"][0], source_bytes)
                    docstring = docstring.strip('\"\'')
                        
                functions[node] = CodeExtractionResult(
                    function_name=func_name,
                    docstring=docstring,
                    assertions=[]
                )
                
        # 2. Map assertions to functions
        for capture_name, nodes in captures_dict.items():
            if not capture_name.startswith("assert."):
                continue
                
            for node in nodes:
                # Walk up to find the parent function
                parent = node
                parent_func = None
                while parent:
                    if parent in functions:
                        parent_func = functions[parent]
                        break
                    parent = parent.parent
                    
                if not parent_func:
                    continue
                    
                # Extract assertion details
                node_cursor = tree_sitter.QueryCursor(query)
                sub_caps = node_cursor.captures(node)
                
                op_str = None
                left_str = None
                right_str = None
                
                for sub_cap_name, sub_nodes in sub_caps.items():
                    if not sub_nodes:
                        continue
                    text = _get_node_text(sub_nodes[0], source_bytes)
                    if sub_cap_name in ("op", "matcher", "assert_meth"):
                        op_str = text
                    elif sub_cap_name == "left":
                        left_str = text
                    elif sub_cap_name == "right":
                        right_str = text
                        
                parent_func.assertions.append(
                    AssertionData(
                        type="comparison" if right_str else "call",
                        operator=op_str,
                        left=left_str,
                        right=right_str,
                    )
                )
            
        return list(functions.values())

