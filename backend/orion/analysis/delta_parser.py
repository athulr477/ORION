"""Requirement-diff tracking — parse Jira changelogs into structured deltas.

Phase 6: When a requirement is updated, this module compares the old and new
descriptions by re-running Phase 3 constraint extraction on both versions and
diffing the results.  The output is a structured delta describing:

- Added conditions (new constraints not in the old version)
- Removed conditions (old constraints no longer present)
- Changed thresholds (same subject/operator but different numeric value)
- Changed literals (text-level changes outside of constraints)

This is entirely rule-based/regex — no LLM in the decision path.
"""

from __future__ import annotations

import difflib
import logging
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from orion.extraction.requirement_extractor import extract_constraints

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class DeltaChange:
    """A single structured change detected between two requirement versions."""

    type: str  # "added_condition" | "removed_condition" | "changed_threshold" | "changed_literal" | "text_change"
    field: str = ""  # which field changed (e.g. "description", "summary")
    old_value: Any = None
    new_value: Any = None
    details: str = ""  # human-readable summary of the change

    def to_dict(self) -> dict:
        """Serialize for JSONB storage."""
        return {
            "type": self.type,
            "field": self.field,
            "old_value": self.old_value,
            "new_value": self.new_value,
            "details": self.details,
        }


@dataclass
class RequirementDelta:
    """Aggregated structured diff for a requirement update."""

    changes: list[DeltaChange] = field(default_factory=list)
    changed_at: str = ""  # ISO timestamp of when the change was detected
    changelog_raw: list[dict] | None = None  # original Jira changelog items

    def to_dict(self) -> dict:
        """Serialize for JSONB storage in traceability_matrix.requirement_delta."""
        return {
            "changes": [c.to_dict() for c in self.changes],
            "changed_at": self.changed_at,
            "change_count": len(self.changes),
            "change_types": sorted(set(c.type for c in self.changes)),
        }


# ---------------------------------------------------------------------------
# Constraint diffing
# ---------------------------------------------------------------------------


def _constraint_key(constraint: dict) -> str:
    """Build a comparison key for a constraint based on subject + operator.

    Two constraints are considered "the same constraint" if they share
    the same subject (or raw_text prefix) and operator.  A change in
    the value means the threshold was modified rather than a wholly new
    condition being added.
    """
    subject = (constraint.get("subject") or "").strip().lower()
    operator = constraint.get("operator") or ""
    ctype = constraint.get("type") or ""
    polarity = constraint.get("polarity") or "positive"

    if ctype == "boolean":
        return f"bool:{polarity}:{subject}"
    return f"threshold:{operator}:{subject}"


def _diff_constraints(
    old_constraints: list[dict],
    new_constraints: list[dict],
) -> list[DeltaChange]:
    """Diff two sets of extracted constraints and produce DeltaChange items.

    Strategy:
    1. Key each constraint by (subject, operator).
    2. Constraints only in old → removed_condition.
    3. Constraints only in new → added_condition.
    4. Constraints in both with different values → changed_threshold.
    """
    changes: list[DeltaChange] = []

    old_by_key: dict[str, dict] = {}
    new_by_key: dict[str, dict] = {}

    for c in old_constraints:
        key = _constraint_key(c)
        old_by_key[key] = c

    for c in new_constraints:
        key = _constraint_key(c)
        new_by_key[key] = c

    all_keys = set(old_by_key.keys()) | set(new_by_key.keys())

    for key in sorted(all_keys):
        old_c = old_by_key.get(key)
        new_c = new_by_key.get(key)

        if old_c and not new_c:
            # Removed condition
            raw = old_c.get("raw_text", "")
            changes.append(DeltaChange(
                type="removed_condition",
                field="description",
                old_value=_constraint_summary(old_c),
                new_value=None,
                details=f"Removed constraint: {raw}" if raw else "Removed constraint",
            ))

        elif new_c and not old_c:
            # Added condition
            raw = new_c.get("raw_text", "")
            changes.append(DeltaChange(
                type="added_condition",
                field="description",
                old_value=None,
                new_value=_constraint_summary(new_c),
                details=f"Added constraint: {raw}" if raw else "Added constraint",
            ))

        elif old_c and new_c:
            # Both exist — check for value changes
            old_val = old_c.get("value")
            new_val = new_c.get("value")
            old_unit = old_c.get("unit") or ""
            new_unit = new_c.get("unit") or ""

            if old_val != new_val or old_unit != new_unit:
                changes.append(DeltaChange(
                    type="changed_threshold",
                    field="description",
                    old_value=_constraint_summary(old_c),
                    new_value=_constraint_summary(new_c),
                    details=(
                        f"Threshold changed: "
                        f"{old_c.get('operator', '')} {old_val} {old_unit}"
                        f" → {new_c.get('operator', '')} {new_val} {new_unit}"
                    ).strip(),
                ))

    return changes


def _constraint_summary(constraint: dict) -> dict:
    """Create a concise summary dict of a constraint for delta storage."""
    return {
        "type": constraint.get("type"),
        "operator": constraint.get("operator"),
        "value": constraint.get("value"),
        "unit": constraint.get("unit"),
        "subject": constraint.get("subject"),
        "raw_text": constraint.get("raw_text"),
    }


# ---------------------------------------------------------------------------
# Text-level diffing (sentence-level)
# ---------------------------------------------------------------------------


def _split_sentences(text: str) -> list[str]:
    """Split text into sentences for diffing."""
    # Split on sentence-ending punctuation, keeping non-empty results
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    return [s.strip() for s in sentences if s.strip()]


def _diff_text(old_text: str, new_text: str) -> list[DeltaChange]:
    """Produce text-level DeltaChange items for non-constraint changes.

    Uses sentence-level diffing to find added/removed/changed sentences.
    """
    changes: list[DeltaChange] = []

    old_sentences = _split_sentences(old_text)
    new_sentences = _split_sentences(new_text)

    matcher = difflib.SequenceMatcher(None, old_sentences, new_sentences)

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            continue

        old_chunk = " ".join(old_sentences[i1:i2]) if i1 < i2 else ""
        new_chunk = " ".join(new_sentences[j1:j2]) if j1 < j2 else ""

        if tag == "delete":
            changes.append(DeltaChange(
                type="text_change",
                field="description",
                old_value=old_chunk,
                new_value=None,
                details=f"Removed text: \"{old_chunk[:100]}\"",
            ))
        elif tag == "insert":
            changes.append(DeltaChange(
                type="text_change",
                field="description",
                old_value=None,
                new_value=new_chunk,
                details=f"Added text: \"{new_chunk[:100]}\"",
            ))
        elif tag == "replace":
            changes.append(DeltaChange(
                type="changed_literal",
                field="description",
                old_value=old_chunk,
                new_value=new_chunk,
                details=f"Changed: \"{old_chunk[:60]}\" → \"{new_chunk[:60]}\"",
            ))

    return changes


# ---------------------------------------------------------------------------
# Changelog item processing
# ---------------------------------------------------------------------------

# Fields in Jira changelogs that contain requirement content we care about
_CONTENT_FIELDS = {"description", "summary"}


def _process_changelog_items(changelog_items: list[dict]) -> list[DeltaChange]:
    """Process raw Jira changelog items for non-description fields.

    For fields like 'summary', produce simple changed_literal deltas.
    Description field changes are handled separately via constraint diffing.
    """
    changes: list[DeltaChange] = []

    for item in changelog_items:
        field_name = (item.get("field") or "").lower()

        # Skip description — handled by constraint diffing
        if field_name == "description":
            continue

        # Skip non-content fields (status, assignee, priority, etc.)
        if field_name not in _CONTENT_FIELDS:
            continue

        old_val = item.get("from") or item.get("fromString")
        new_val = item.get("to") or item.get("toString")

        if old_val != new_val:
            changes.append(DeltaChange(
                type="changed_literal",
                field=field_name,
                old_value=old_val,
                new_value=new_val,
                details=f"{field_name} changed: \"{old_val or ''}\" → \"{new_val or ''}\"",
            ))

    return changes


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def parse_changelog_to_delta(
    changelog_items: list[dict] | None,
    old_description: str,
    new_description: str,
) -> RequirementDelta:
    """Parse a Jira changelog into a structured RequirementDelta.

    This is the main entry point for Phase 6 delta tracking.

    Strategy:
    1. Run Phase 3 extract_constraints() on both old and new descriptions.
    2. Diff the constraint sets to find added/removed/changed constraints.
    3. Sentence-level diff for remaining text changes.
    4. Process other changelog fields (e.g. summary changes).

    Args:
        changelog_items: Raw Jira changelog items (list of {field, from, to} dicts).
            Can be None if the changelog is not available.
        old_description: Previous requirement description text.
        new_description: Updated requirement description text.

    Returns:
        RequirementDelta with all structured changes.
    """
    delta = RequirementDelta(
        changed_at=datetime.now(UTC).isoformat(),
        changelog_raw=changelog_items,
    )

    # Step 1: Extract constraints from both versions
    old_result = extract_constraints(old_description, "old")
    new_result = extract_constraints(new_description, "new")

    old_constraint_dicts = old_result.to_dict().get("constraints", [])
    new_constraint_dicts = new_result.to_dict().get("constraints", [])

    # Step 2: Diff the constraint sets
    constraint_changes = _diff_constraints(old_constraint_dicts, new_constraint_dicts)
    delta.changes.extend(constraint_changes)

    # Step 3: Sentence-level text diff (captures changes not covered by constraints)
    if old_description.strip() != new_description.strip():
        text_changes = _diff_text(old_description, new_description)
        # Only add text changes that aren't already covered by constraint changes
        if not constraint_changes and text_changes:
            delta.changes.extend(text_changes)
        elif text_changes and constraint_changes:
            # If we already have constraint-level changes, only add text changes
            # that seem genuinely different (not just reformulations of the same thing)
            for tc in text_changes:
                if tc.type == "text_change":
                    # Pure additions/removals of whole sentences are worth tracking
                    delta.changes.append(tc)

    # Step 4: Process other changelog fields (summary, etc.)
    if changelog_items:
        other_changes = _process_changelog_items(changelog_items)
        delta.changes.extend(other_changes)

    logger.info(
        "Parsed requirement delta: %d changes (%s)",
        len(delta.changes),
        ", ".join(sorted(set(c.type for c in delta.changes))) or "none",
    )

    return delta
