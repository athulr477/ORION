"""Evaluation harness for empirical benchmark comparison — Phase 10.

Compares two engines over the 30-pair benchmark dataset:
    1. Orion Hybrid Engine:  risk = 1.0 - (0.6 * semantic + 0.4 * structural)
    2. Cosine-only Baseline: risk = 1.0 - semantic_score

Metrics computed per-class and macro-averaged:
    - Precision, Recall, F1-score
    - Confusion Matrix (3x3: Covered / Partial / Drifted)

Produces a structured EvaluationReport dataclass for the verify script
and for rendering into evaluation_report.md.

NOTE: This module imports classify() from risk_engine.py to guarantee
      threshold and formula consistency with the live engine.

Usage (standalone, no DB required — all inputs come from benchmark JSON):
    from orion.evaluation.evaluator import run_evaluation
    report = run_evaluation()
    print(report.format_table())
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path

from orion.analysis.risk_engine import (
    SEMANTIC_WEIGHT,
    STRUCTURAL_WEIGHT,
    classify,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_BENCHMARK_PATH = Path(__file__).parent / "data" / "benchmark_30.json"
_LABELS = ["Covered", "Partial", "Drifted"]
_LABEL_IDX = {label: i for i, label in enumerate(_LABELS)}


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class PairResult:
    """Classification result for one benchmark pair."""

    pair_id: str
    ground_truth: str
    # Scores
    semantic_score: float
    structural_score: float
    # Engine outputs
    hybrid_risk: float
    hybrid_pred: str
    cosine_risk: float
    cosine_pred: str


@dataclass
class ClassMetrics:
    """Per-class precision, recall, F1.

    Full-precision values are stored internally. Rounding is applied
    only in to_dict() for display — macro averages are computed from
    these full-precision values to prevent accumulated rounding error.
    """

    label: str
    precision: float
    recall: float
    f1: float
    support: int  # ground-truth count

    def to_dict(self) -> dict:
        """Serialize with display rounding (4 decimal places)."""
        return {
            "label": self.label,
            "precision": round(self.precision, 4),
            "recall": round(self.recall, 4),
            "f1": round(self.f1, 4),
            "support": self.support,
        }


@dataclass
class EvaluationReport:
    """Full evaluation report for one engine."""

    engine_name: str
    pairs: list[PairResult]
    confusion_matrix: list[list[int]]  # rows=true, cols=pred, order=_LABELS
    per_class: list[ClassMetrics]
    macro_precision: float
    macro_recall: float
    macro_f1: float
    accuracy: float

    def format_table(self) -> str:
        """Format confusion matrix and classification metrics as an ASCII table."""
        lines = [
            f"Engine: {self.engine_name}",
            "",
            "  Confusion Matrix:",
            f"  {'':16s} {'Pred:Covered':>14} {'Pred:Partial':>13} {'Pred:Drifted':>13}",
            f"  {'-' * 60}",
        ]
        for i, label in enumerate(_LABELS):
            row_label = f"True:{label}"
            cells = "  ".join(f"{self.confusion_matrix[i][j]:>10}" for j in range(3))
            lines.append(f"  {row_label:<16} {cells}")

        lines.extend(
            [
                "",
                "  Classification Metrics:",
                f"  {'Class':<12} {'Precision':>10} {'Recall':>10} {'F1-Score':>10} {'Support':>10}",
                f"  {'-' * 54}",
            ]
        )
        for m in self.per_class:
            lines.append(
                f"  {m.label:<12} {m.precision:>10.3f} {m.recall:>10.3f} {m.f1:>10.3f} {m.support:>10}"
            )
        lines.extend(
            [
                f"  {'-' * 54}",
                f"  {'Macro avg':<12} {self.macro_precision:>10.3f} {self.macro_recall:>10.3f} {self.macro_f1:>10.3f} {len(self.pairs):>10}",
                f"  {'Accuracy':<12} {'':>10} {'':>10} {self.accuracy:>10.3f} {len(self.pairs):>10}",
            ]
        )
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Scoring functions — delegate to risk_engine for consistency
# ---------------------------------------------------------------------------


def _semantic_score_from_texts(req_text: str, test_text: str) -> float:
    """Compute BGE-small cosine similarity between requirement and test texts.

    Uses semantic_similarity() which floors at 0.0 for a clean [0, 1] range.
    """
    from orion.embedding.engine import embed_text, semantic_similarity

    req_emb = embed_text(req_text)
    test_emb = embed_text(test_text)
    return float(semantic_similarity(req_emb, test_emb))


def _structural_score_from_pair(pair: dict) -> float:
    """Compute structural matcher score for a benchmark pair."""
    from orion.analysis.structural_matcher import compute_structural_score
    from orion.extraction.code_extractor import extract_assertions
    from orion.extraction.requirement_extractor import extract_constraints

    req = pair["requirement"]
    test = pair["test"]

    # extract_constraints returns RequirementExtractionResult — convert to dict
    constraints = extract_constraints(req["description"])
    constraints_dict = constraints.to_dict() if hasattr(constraints, "to_dict") else constraints

    # extract_assertions returns a single CodeExtractionResult with .assertions list
    raw_result = extract_assertions(
        test["source_code"], function_name=test.get("function_name", "")
    )
    assertion_list: list[dict] = [a.__dict__ for a in raw_result.assertions]
    assertions_dict = {"assertions": assertion_list}

    score_result = compute_structural_score(constraints_dict, assertions_dict)
    return float(
        score_result.structural_score if hasattr(score_result, "structural_score") else score_result
    )


def _build_req_text(pair: dict) -> str:
    """Build requirement embedding text from a benchmark pair."""
    req = pair["requirement"]
    title = req.get("title", "").strip().rstrip(".") + "."
    desc = req.get("description", "").strip()
    return f"{title} {desc}" if desc else title


def _build_test_text_from_pair(pair: dict) -> str:
    """Build test embedding text from a benchmark pair (docstring-first strategy)."""
    test = pair["test"]
    docstring = test.get("docstring", "").strip()
    if docstring:
        return docstring
    # Fallback: function name humanized
    fn = test.get("function_name", "").replace("test_", "").replace("_", " ")
    return fn


# ---------------------------------------------------------------------------
# Metrics computation
# ---------------------------------------------------------------------------


def _compute_metrics(
    ground_truths: list[str],
    predictions: list[str],
) -> tuple[list[list[int]], list[ClassMetrics], float, float, float, float]:
    """Compute confusion matrix, per-class metrics, and macro averages.

    Full-precision values are used for macro averaging — rounding is only
    applied at the final display layer (ClassMetrics.to_dict() and the
    returned macro values). This prevents accumulated rounding error when
    averaging across classes.

    Returns:
        (confusion_matrix, per_class_metrics, macro_precision, macro_recall, macro_f1, accuracy)
    """
    n = len(_LABELS)
    cm = [[0] * n for _ in range(n)]

    for gt, pred in zip(ground_truths, predictions, strict=False):
        if gt in _LABEL_IDX and pred in _LABEL_IDX:
            cm[_LABEL_IDX[gt]][_LABEL_IDX[pred]] += 1

    per_class: list[ClassMetrics] = []
    for i, label in enumerate(_LABELS):
        tp = cm[i][i]
        fp = sum(cm[j][i] for j in range(n) if j != i)
        fn = sum(cm[i][j] for j in range(n) if j != i)
        support = sum(cm[i])

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0

        # Store full-precision values — rounding only in to_dict()
        per_class.append(
            ClassMetrics(
                label=label,
                precision=precision,
                recall=recall,
                f1=f1,
                support=support,
            )
        )

    # Macro averages computed from full-precision per-class values
    macro_p = sum(m.precision for m in per_class) / n
    macro_r = sum(m.recall for m in per_class) / n
    macro_f1 = sum(m.f1 for m in per_class) / n
    correct = sum(cm[i][i] for i in range(n))
    total = sum(cm[i][j] for i in range(n) for j in range(n))
    accuracy = correct / total if total > 0 else 0.0

    return (
        cm,
        per_class,
        round(macro_p, 4),
        round(macro_r, 4),
        round(macro_f1, 4),
        round(accuracy, 4),
    )


# ---------------------------------------------------------------------------
# Main evaluation runner
# ---------------------------------------------------------------------------


def run_evaluation(
    benchmark_path: Path | None = None,
    verbose: bool = True,
) -> tuple[EvaluationReport, EvaluationReport]:
    """Run the full benchmark evaluation and return two EvaluationReports.

    Both engines use classify() from risk_engine.py to ensure threshold
    and formula consistency with the live system.

    Args:
        benchmark_path: Override path to the benchmark JSON (default: benchmark_30.json).
        verbose: If True, print progress as each pair is scored.

    Returns:
        Tuple of (hybrid_report, cosine_report).
    """
    path = benchmark_path or _BENCHMARK_PATH
    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    pairs = data["pairs"]
    n = len(pairs)
    logger.info("Loaded %d benchmark pairs from %s", n, path)

    pair_results: list[PairResult] = []

    for idx, pair in enumerate(pairs, 1):
        pair_id = pair["id"]
        ground_truth = pair["ground_truth"]

        if verbose:
            print(f"  Scoring [{idx:02d}/{n}] {pair_id} (gt={ground_truth})")

        req_text = _build_req_text(pair)
        test_text = _build_test_text_from_pair(pair)

        sem_score = _semantic_score_from_texts(req_text, test_text)
        struct_score = _structural_score_from_pair(pair)

        # Hybrid engine — use classify() for correct risk formula
        hybrid_result = classify(sem_score, struct_score)

        # Cosine-only baseline — structural ignored (set to 0.0 so
        # risk = 1.0 - (0.6 * sem + 0.4 * 0.0) = 1.0 - 0.6 * sem)
        cosine_result = classify(sem_score, 0.0)

        pair_results.append(
            PairResult(
                pair_id=pair_id,
                ground_truth=ground_truth,
                semantic_score=round(sem_score, 4),
                structural_score=round(struct_score, 4),
                hybrid_risk=round(hybrid_result.risk_score, 4),
                hybrid_pred=hybrid_result.status,
                cosine_risk=round(cosine_result.risk_score, 4),
                cosine_pred=cosine_result.status,
            )
        )

    # Build reports
    gts = [r.ground_truth for r in pair_results]
    hybrid_preds = [r.hybrid_pred for r in pair_results]
    cosine_preds = [r.cosine_pred for r in pair_results]

    h_cm, h_pc, h_mp, h_mr, h_mf1, h_acc = _compute_metrics(gts, hybrid_preds)
    c_cm, c_pc, c_mp, c_mr, c_mf1, c_acc = _compute_metrics(gts, cosine_preds)

    hybrid_report = EvaluationReport(
        engine_name=f"Orion Hybrid ({SEMANTIC_WEIGHT}·sem + {STRUCTURAL_WEIGHT}·struct)",
        pairs=pair_results,
        confusion_matrix=h_cm,
        per_class=h_pc,
        macro_precision=h_mp,
        macro_recall=h_mr,
        macro_f1=h_mf1,
        accuracy=h_acc,
    )
    cosine_report = EvaluationReport(
        engine_name="Cosine-only Baseline",
        pairs=pair_results,
        confusion_matrix=c_cm,
        per_class=c_pc,
        macro_precision=c_mp,
        macro_recall=c_mr,
        macro_f1=c_mf1,
        accuracy=c_acc,
    )

    return hybrid_report, cosine_report


def main() -> None:
    """CLI runner for empirical benchmark evaluation."""
    import io
    import sys

    if sys.stdout and hasattr(sys.stdout, "buffer"):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

    print("=" * 70)
    print("  Orion Empirical Benchmark Evaluation")
    print("=" * 70)
    hybrid_report, cosine_report = run_evaluation(verbose=True)

    print("\n" + hybrid_report.format_table())
    print("\n" + cosine_report.format_table())

    print("\n" + "=" * 70)
    print("  Side-by-Side Summary Comparison")
    print("=" * 70)
    print(f"\n  {'Class':<10} | {'Hybrid Engine':^35} | {'Cosine Baseline':^35}")
    print(
        f"  {'':10} | {'Prec':>10} {'Rec':>10} {'F1':>10} {'Sup':>5} | "
        f"{'Prec':>10} {'Rec':>10} {'F1':>10} {'Sup':>5}"
    )
    print(f"  {'-' * 82}")

    for hm, cm_cls in zip(hybrid_report.per_class, cosine_report.per_class, strict=False):
        print(
            f"  {hm.label:<10} | "
            f"{hm.precision:>10.3f} {hm.recall:>10.3f} {hm.f1:>10.3f} {hm.support:>5} | "
            f"{cm_cls.precision:>10.3f} {cm_cls.recall:>10.3f} {cm_cls.f1:>10.3f} {cm_cls.support:>5}"
        )

    print(f"  {'-' * 82}")
    print(
        f"  {'Macro avg':<10} | "
        f"{hybrid_report.macro_precision:>10.3f} {hybrid_report.macro_recall:>10.3f} "
        f"{hybrid_report.macro_f1:>10.3f} {'':>5} | "
        f"{cosine_report.macro_precision:>10.3f} {cosine_report.macro_recall:>10.3f} "
        f"{cosine_report.macro_f1:>10.3f} {'':>5}"
    )
    print(
        f"  {'Accuracy':<10} | "
        f"{'':>10} {'':>10} {hybrid_report.accuracy:>10.3f} {'':>5} | "
        f"{'':>10} {'':>10} {cosine_report.accuracy:>10.3f} {'':>5}"
    )
    print(f"  {'=' * 82}\n")


if __name__ == "__main__":
    main()
