"""Atlassian Document Format (ADF) to plain text/markdown converter.

Jira Cloud stores rich text (descriptions, acceptance criteria, comments)
in ADF — a nested JSON structure of nodes and marks.

This module converts ADF to clean, readable plain text suitable for:
- Constraint extraction (Phase 3)
- Semantic embedding (Phase 4)
- Requirement delta tracking (Phase 6)

ADF node types handled:
    Blocks: doc, paragraph, bulletList, orderedList, listItem,
            heading, blockquote, codeBlock, rule, panel
    Inline: text, hardBreak, mention, emoji
    Marks:  strong, em, code, underline, strike, link

Reference: https://developer.atlassian.com/cloud/jira/platform/apis/document/structure/
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def adf_to_text(node: dict | str | None) -> str:
    """Convert an ADF document node (or raw string) to plain text.

    Handles legacy string descriptions and nested ADF doc objects gracefully.

    Args:
        node: ADF node dict, raw string description, or None.

    Returns:
        Plain text string. Never returns None.
    """
    if node is None:
        return ""
    if isinstance(node, str):
        # Legacy plain-text description or already-converted text
        return node.strip()
    if not isinstance(node, dict):
        return str(node)

    return _render_node(node).strip()


# ---------------------------------------------------------------------------
# Internal recursive renderer
# ---------------------------------------------------------------------------

def _render_node(node: dict) -> str:
    """Recursively render a single ADF node to text."""
    node_type = node.get("type", "")
    content = node.get("content", [])
    text = node.get("text", "")
    attrs = node.get("attrs", {})

    # -----------------------------------------------------------------------
    # Leaf: text node (inline)
    # -----------------------------------------------------------------------
    if node_type == "text":
        result = text
        marks = node.get("marks", [])
        for mark in marks:
            result = _apply_mark(result, mark)
        return result

    # -----------------------------------------------------------------------
    # Inline: hardBreak
    # -----------------------------------------------------------------------
    if node_type == "hardBreak":
        return "\n"

    # -----------------------------------------------------------------------
    # Inline: mention
    # -----------------------------------------------------------------------
    if node_type == "mention":
        display_name = attrs.get("text") or attrs.get("id", "@unknown")
        return f"@{display_name.lstrip('@')}"

    # -----------------------------------------------------------------------
    # Inline: emoji
    # -----------------------------------------------------------------------
    if node_type == "emoji":
        return attrs.get("text", attrs.get("shortName", ""))

    # -----------------------------------------------------------------------
    # Inline: inlineCard (smart link)
    # -----------------------------------------------------------------------
    if node_type == "inlineCard":
        return attrs.get("url", "")

    # -----------------------------------------------------------------------
    # Block: paragraph
    # -----------------------------------------------------------------------
    if node_type == "paragraph":
        inner = _render_children(content)
        return inner + "\n" if inner else "\n"

    # -----------------------------------------------------------------------
    # Block: heading
    # -----------------------------------------------------------------------
    if node_type == "heading":
        level = attrs.get("level", 1)
        prefix = "#" * level
        inner = _render_children(content)
        return f"{prefix} {inner}\n"

    # -----------------------------------------------------------------------
    # Block: bulletList / orderedList
    # -----------------------------------------------------------------------
    if node_type in ("bulletList", "orderedList"):
        items = []
        for i, child in enumerate(content):
            marker = "-" if node_type == "bulletList" else f"{i + 1}."
            item_text = _render_children(child.get("content", []))
            items.append(f"{marker} {item_text.strip()}")
        return "\n".join(items) + "\n"

    # -----------------------------------------------------------------------
    # Block: listItem — just render children (parent handles markers)
    # -----------------------------------------------------------------------
    if node_type == "listItem":
        return _render_children(content)

    # -----------------------------------------------------------------------
    # Block: blockquote
    # -----------------------------------------------------------------------
    if node_type == "blockquote":
        inner = _render_children(content)
        quoted = "\n".join(f"> {line}" for line in inner.splitlines())
        return quoted + "\n"

    # -----------------------------------------------------------------------
    # Block: codeBlock
    # -----------------------------------------------------------------------
    if node_type == "codeBlock":
        lang = attrs.get("language", "")
        inner = _render_children(content)
        return f"```{lang}\n{inner}\n```\n"

    # -----------------------------------------------------------------------
    # Block: rule (horizontal rule)
    # -----------------------------------------------------------------------
    if node_type == "rule":
        return "\n---\n"

    # -----------------------------------------------------------------------
    # Block: panel (info/warning/success boxes)
    # -----------------------------------------------------------------------
    if node_type == "panel":
        panel_type = attrs.get("panelType", "info").upper()
        inner = _render_children(content)
        lines = "\n".join(f"  {line}" for line in inner.strip().splitlines())
        return f"[{panel_type}]\n{lines}\n"

    # -----------------------------------------------------------------------
    # Block: table
    # -----------------------------------------------------------------------
    if node_type in ("table", "tableRow", "tableCell", "tableHeader"):
        # Simplified: just render cell content separated by spaces
        return _render_children(content) + " "

    # -----------------------------------------------------------------------
    # Block: mediaSingle / media (images/attachments — skip or label)
    # -----------------------------------------------------------------------
    if node_type in ("mediaSingle", "media"):
        alt = attrs.get("alt", attrs.get("fileName", ""))
        return f"[attachment: {alt}]\n" if alt else ""

    # -----------------------------------------------------------------------
    # Default: doc node and any unknown containers — recurse into children
    # -----------------------------------------------------------------------
    return _render_children(content)


def _render_children(content: list) -> str:
    """Render a list of child ADF nodes into a concatenated string."""
    if not content:
        return ""
    parts = [_render_node(child) for child in content if isinstance(child, dict)]
    return "".join(parts)


def _apply_mark(text: str, mark: dict) -> str:
    """Apply an inline mark to text (bold, italic, code, link, etc.).

    For requirement text, marks are mostly irrelevant to semantics,
    so we keep the text and just add minimal Markdown notation.
    """
    mark_type = mark.get("type", "")
    attrs = mark.get("attrs", {})

    if mark_type == "strong":
        return f"**{text}**"
    if mark_type == "em":
        return f"_{text}_"
    if mark_type == "code":
        return f"`{text}`"
    if mark_type == "underline":
        return text  # no standard markdown equivalent — keep text
    if mark_type == "strike":
        return f"~~{text}~~"
    if mark_type == "link":
        href = attrs.get("href", "")
        return f"[{text}]({href})" if href else text
    if mark_type == "textColor":
        return text  # ignore colour — keep text
    if mark_type == "subsup":
        return text  # keep text

    return text
