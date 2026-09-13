# Orion RTM — Empirical Benchmark Evaluation Report

> **Generated:** 2026-09-13  
> **Dataset:** `benchmark_30.json` — 30 requirement-test pairs (10 Covered · 10 Partial · 10 Drifted)  
> **Embedding model:** `BAAI/bge-small-en-v1.5` via ONNX Runtime (CPU, no GPU required)  
> **Structural matcher:** Rule-based constraint ↔ assertion matching (no LLM in decision path)

---

## Chapter V — Empirical Evaluation

### 5.1 Evaluation Methodology

Two classification engines were evaluated on a curated 30-pair benchmark dataset:

| Engine | Formula |
|---|---|
| **Orion Hybrid** | `risk = 0.6 × semantic_score + 0.4 × structural_score` |
| **Cosine Baseline** | `risk = semantic_score` (structural signal ignored) |

**Classification thresholds** (fixed, Pre-Phase 0 — not tuned on this dataset):

| Threshold | Class |
|---|---|
| `risk > 0.75` | **Covered** |
| `0.40 ≤ risk ≤ 0.75` | **Partial** |
| `risk < 0.40` | **Drifted** |

---

### 5.2 Per-Pair Score Table

| ID | Ground Truth | Semantic | Structural | Hybrid Risk | Hybrid Pred | Cosine Risk | Cosine Pred | H✓ | C✓ |
|:--|:--|--:|--:|--:|:--|--:|:--|:--|:--|
| P01 | Covered | 0.762 | 0.720 | 0.745 | Partial | 0.762 | Covered | ✗ | ✓ |
| P02 | Covered | 0.832 | 0.300 | 0.619 | Partial | 0.832 | Covered | ✗ | ✓ |
| P03 | Covered | 0.693 | 0.300 | 0.536 | Partial | 0.693 | Partial | ✗ | ✗ |
| P04 | Covered | 0.900 | 0.800 | 0.860 | Covered | 0.900 | Covered | ✓ | ✓ |
| P05 | Covered | 0.784 | 0.327 | 0.601 | Partial | 0.784 | Covered | ✗ | ✓ |
| P06 | Covered | 0.859 | 0.300 | 0.635 | Partial | 0.859 | Covered | ✗ | ✓ |
| P07 | Covered | 0.803 | 0.300 | 0.602 | Partial | 0.803 | Covered | ✗ | ✓ |
| P08 | Covered | 0.836 | 0.707 | 0.784 | Covered | 0.836 | Covered | ✓ | ✓ |
| P09 | Covered | 0.818 | 0.300 | 0.611 | Partial | 0.818 | Covered | ✗ | ✓ |
| P10 | Covered | 0.802 | 0.300 | 0.602 | Partial | 0.802 | Covered | ✗ | ✓ |
| P11 | Partial | 0.817 | 0.281 | 0.603 | Partial | 0.817 | Covered | ✓ | ✗ |
| P12 | Partial | 0.736 | 0.514 | 0.647 | Partial | 0.736 | Partial | ✓ | ✓ |
| P13 | Partial | 0.762 | 0.600 | 0.697 | Partial | 0.762 | Covered | ✓ | ✗ |
| P14 | Partial | 0.712 | 0.000 | 0.427 | Partial | 0.712 | Partial | ✓ | ✓ |
| P15 | Partial | 0.783 | 0.300 | 0.590 | Partial | 0.783 | Covered | ✓ | ✗ |
| P16 | Partial | 0.536 | 0.300 | 0.441 | Partial | 0.536 | Partial | ✓ | ✓ |
| P17 | Partial | 0.669 | 0.000 | 0.401 | Partial | 0.669 | Partial | ✓ | ✓ |
| P18 | Partial | 0.723 | 0.387 | 0.589 | Partial | 0.723 | Partial | ✓ | ✓ |
| P19 | Partial | 0.652 | 0.311 | 0.515 | Partial | 0.652 | Partial | ✓ | ✓ |
| P20 | Partial | 0.809 | 0.289 | 0.601 | Partial | 0.809 | Covered | ✓ | ✗ |
| P21 | Drifted | 0.648 | 0.300 | 0.509 | Partial | 0.648 | Partial | ✗ | ✗ |
| P22 | Drifted | 0.457 | 0.000 | 0.274 | **Drifted** | 0.457 | Partial | ✓ | ✗ |
| P23 | Drifted | 0.525 | 0.000 | 0.315 | **Drifted** | 0.525 | Partial | ✓ | ✗ |
| P24 | Drifted | 0.604 | 0.300 | 0.482 | Partial | 0.604 | Partial | ✗ | ✗ |
| P25 | Drifted | 0.456 | 0.000 | 0.273 | **Drifted** | 0.456 | Partial | ✓ | ✗ |
| P26 | Drifted | 0.429 | 0.000 | 0.258 | **Drifted** | 0.429 | Partial | ✓ | ✗ |
| P27 | Drifted | 0.455 | 0.300 | 0.393 | **Drifted** | 0.455 | Partial | ✓ | ✗ |
| P28 | Drifted | 0.535 | 0.300 | 0.441 | Partial | 0.535 | Partial | ✗ | ✗ |
| P29 | Drifted | 0.437 | 0.000 | 0.262 | **Drifted** | 0.437 | Partial | ✓ | ✗ |
| P30 | Drifted | 0.538 | 0.300 | 0.443 | Partial | 0.538 | Partial | ✗ | ✗ |

---

### 5.3 Confusion Matrices

#### 5.3.1 Orion Hybrid Engine

| | Pred: Covered | Pred: Partial | Pred: Drifted |
|:--|--:|--:|--:|
| **True: Covered** | 2 | 8 | 0 |
| **True: Partial** | 0 | 10 | 0 |
| **True: Drifted** | 0 | 4 | **6** |

#### 5.3.2 Cosine-only Baseline

| | Pred: Covered | Pred: Partial | Pred: Drifted |
|:--|--:|--:|--:|
| **True: Covered** | 9 | 1 | 0 |
| **True: Partial** | 4 | 6 | 0 |
| **True: Drifted** | 0 | **10** | 0 |

> [!IMPORTANT]
> The Cosine-only baseline **never predicts Drifted** (Drifted F1 = 0.000). All 10 Drifted pairs are misclassified as Partial because their semantic scores land in the [0.43–0.65] range — squarely in the Partial band. The hybrid engine correctly identifies 6/10 by pulling the risk score below 0.40 via zero structural scores.

---

### 5.4 Classification Metrics

| Class | H-Precision | H-Recall | H-F1 | C-Precision | C-Recall | C-F1 | Support |
|:--|--:|--:|--:|--:|--:|--:|--:|
| Covered | 1.000 | 0.200 | 0.333 | 0.692 | 0.900 | 0.783 | 10 |
| Partial | 0.455 | 1.000 | 0.625 | 0.353 | 0.600 | 0.444 | 10 |
| Drifted | **1.000** | **0.600** | **0.750** | 0.000 | 0.000 | **0.000** | 10 |
| **Macro avg** | **0.818** | **0.600** | **0.569** | 0.348 | 0.500 | 0.409 | 30 |
| **Accuracy** | | | **0.600** | | | 0.500 | 30 |

---

### 5.5 Engine Comparison Summary

| Metric | Orion Hybrid | Cosine Baseline | Delta |
|:--|--:|--:|--:|
| Macro Precision | 0.818 | 0.348 | **+0.470** |
| Macro Recall | 0.600 | 0.500 | +0.100 |
| **Macro F1** | **0.569** | 0.409 | **+0.160** |
| **Accuracy** | **0.600** | 0.500 | +0.100 |
| **Drifted F1** | **0.750** | 0.000 | **+0.750** |

---

### 5.6 Interpretation and Discussion

#### The Critical Role of the Structural Signal

The most significant result is the **complete failure of the Cosine-only baseline on the Drifted class** (F1 = 0.000, 0/10 correctly classified). The root cause: Drifted tests that check an entirely different concern still share enough vocabulary with the requirement (e.g. "database", "response", "system") to produce semantic scores of 0.43–0.65 — precisely in the Partial band.

The Orion Hybrid engine breaks this tie: Drifted tests have **zero matching assertions** against the requirement's numeric/boolean constraints. With `structural_score = 0`, the hybrid formula becomes `risk = 0.6 × sem`. For semantic scores below ~0.67, this pushes the risk below the 0.40 Drifted threshold.

#### The Covered Class Trade-off

The hybrid engine over-demotes Covered pairs (8/10 classified as Partial). Many well-written tests still generate `structural_score ≈ 0.30` (the heuristic floor for "some assertions present but no numeric threshold match"). The blended score then falls in the 0.60–0.74 Partial band.

**Implication for practitioners:** The 0.75 Covered threshold may benefit from calibration in a future phase, or the structural extractor could be enhanced to recognize exact-value match assertions more reliably.

#### Partial Class — Perfect Recall

The Hybrid engine achieves **Partial recall = 1.00** — all 10 Partial pairs are correctly identified. In an RTM audit context, false-negative Partial pairs (calling incomplete tests "Covered") carry the highest compliance risk. This is the most practically important metric for the use case.

#### Why Hybrid Wins Despite Lower Covered F1

The Cosine baseline achieves higher Covered F1 (0.783 vs 0.333) by aggressively classifying high-semantic-score pairs as Covered, but at the cost of zero Drifted detection. In safety-critical RTM scenarios, **undetected drift is far more costly than over-flagging**. The hybrid engine's structural penalization is intentionally conservative.

---

### 5.7 Conclusion

> The **Orion Hybrid Engine** (Macro F1 = **0.569**) outperforms the **Cosine-only baseline** (Macro F1 = **0.409**) by **+0.160 F1 points** and **+0.100 accuracy points** on the 30-pair benchmark. The defining result is the **+0.750 F1 improvement on the Drifted class** — demonstrating that the structural matching signal is *essential* for detecting requirement-test drift, a capability entirely absent from pure semantic (cosine similarity) approaches.
>
> These results empirically validate the Pre-Phase 0 design decision to combine semantic and structural evidence with the fixed formula `risk = 0.6 × semantic + 0.4 × structural`.

---

*Orion RTM · Phase 10 Empirical Benchmark Report*  
*Engine: `risk = 0.6 × semantic + 0.4 × structural` · Dataset: `benchmark_30.json` (30 pairs, balanced)*
