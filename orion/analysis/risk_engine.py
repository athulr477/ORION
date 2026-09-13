"""Hybrid risk engine — combine semantic + structural scores into classification.

Pre-Phase 0 fixed formula (DO NOT CHANGE without explicit approval):
    risk_score = 0.6 x semantic_score + 0.4 x structural_score

Thresholds:
    risk_score > 0.75  -> Covered
    0.4 <= risk_score <= 0.75 -> Partial
    risk_score < 0.4   -> Drifted
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Pre-Phase 0 constants — locked in, not to be re-derived
# ---------------------------------------------------------------------------

SEMANTIC_WEIGHT = 0.6
STRUCTURAL_WEIGHT = 0.4

THRESHOLD_COVERED = 0.75
THRESHOLD_DRIFTED = 0.4

# These are the only valid statuses
STATUS_COVERED = "Covered"
STATUS_PARTIAL = "Partial"
STATUS_DRIFTED = "Drifted"


@dataclass
class RiskResult:
    """Classification result from the hybrid risk engine."""

    semantic_score: float
    structural_score: float
    risk_score: float
    confidence: float
    status: str  # "Covered", "Partial", or "Drifted"

    def to_dict(self) -> dict:
        """Serialize for API response or JSONB storage."""
        return {
            "semantic_score": round(self.semantic_score, 4),
            "structural_score": round(self.structural_score, 4),
            "risk_score": round(self.risk_score, 4),
            "confidence": round(self.confidence, 4),
            "status": self.status,
        }


def classify(
    semantic_score: float,
    structural_score: float,
) -> RiskResult:
    """Compute risk_score, confidence, and classify a requirement-test pair.

    Uses the Pre-Phase 0 fixed formula:
        risk_score = 0.6 x semantic_score + 0.4 x structural_score

    Thresholds:
        risk_score > 0.75  -> Covered
        0.4 <= risk_score <= 0.75 -> Partial
        risk_score < 0.4   -> Drifted

    Confidence is computed as distance from the nearest threshold boundary,
    normalized to [0, 1]. Higher confidence = farther from a decision boundary.

    Args:
        semantic_score: Cosine similarity from Phase 4 (in [0, 1] typically).
        structural_score: Structural match score from Phase 5 matcher (in [0, 1]).

    Returns:
        RiskResult with all scores and classification.
    """
    # Clamp inputs to [0, 1]
    semantic_score = max(0.0, min(1.0, semantic_score))
    structural_score = max(0.0, min(1.0, structural_score))

    # Compute risk score using the fixed formula
    risk_score = SEMANTIC_WEIGHT * semantic_score + STRUCTURAL_WEIGHT * structural_score

    # Classify
    if risk_score > THRESHOLD_COVERED:
        status = STATUS_COVERED
    elif risk_score < THRESHOLD_DRIFTED:
        status = STATUS_DRIFTED
    else:
        status = STATUS_PARTIAL

    # Compute confidence: distance from nearest threshold, normalized
    # Max possible distance from any threshold is 0.5 (midpoint of a band)
    dist_covered = abs(risk_score - THRESHOLD_COVERED)
    dist_drifted = abs(risk_score - THRESHOLD_DRIFTED)
    nearest_boundary = min(dist_covered, dist_drifted)

    # Normalize: 0.0 at boundary, 1.0 at max distance
    # Max distance from any boundary within [0, 1] is 0.6 (at risk_score=1.0)
    confidence = min(1.0, nearest_boundary / 0.35)

    return RiskResult(
        semantic_score=semantic_score,
        structural_score=structural_score,
        risk_score=risk_score,
        confidence=confidence,
        status=status,
    )
