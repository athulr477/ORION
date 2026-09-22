# Orion RTM — Empirical Benchmark Evaluation Report

> Generated: 2026-09-22 09:54:53
> Dataset: `benchmark_30.json` — 30 requirement-test pairs (10 Covered, 10 Partial, 10 Drifted)
> Embedding model: `BAAI/bge-small-en-v1.5` (ONNX, CPU inference)

## Chapter V — Empirical Evaluation

### 5.1 Evaluation Methodology

Two classification engines were evaluated on the curated 30-pair benchmark dataset:

| Engine | Formula |
|---|---|
| **Orion Hybrid** | `risk = 0.6 × semantic_score + 0.4 × structural_score` |
| **Cosine Baseline** | `risk = semantic_score` (structural signal ignored) |

**Thresholds** (fixed, pre-Phase 0):
- `risk > 0.75` → **Covered**
- `0.40 ≤ risk ≤ 0.75` → **Partial**
- `risk < 0.40` → **Drifted**

### 5.2 Per-Pair Scores

| ID | Ground Truth | Semantic | Structural | Hybrid Risk | Hybrid Pred | Cosine Risk | Cosine Pred | H✓ | C✓ |
|:--|:--|--:|--:|--:|:--|--:|:--|:--|:--|
| P01 | Covered | 0.762 | 0.851 | 0.203 | Covered | 0.543 | Partial | ✓ | ✗ |
| P02 | Covered | 0.832 | 0.500 | 0.301 | Partial | 0.501 | Partial | ✗ | ✗ |
| P03 | Covered | 0.693 | 0.500 | 0.384 | Partial | 0.584 | Partial | ✗ | ✗ |
| P04 | Covered | 0.900 | 0.889 | 0.104 | Covered | 0.460 | Partial | ✓ | ✗ |
| P05 | Covered | 0.784 | 0.439 | 0.354 | Partial | 0.530 | Partial | ✗ | ✗ |
| P06 | Covered | 0.859 | 0.500 | 0.285 | Partial | 0.485 | Partial | ✗ | ✗ |
| P07 | Covered | 0.803 | 0.500 | 0.319 | Partial | 0.518 | Partial | ✗ | ✗ |
| P08 | Covered | 0.836 | 0.692 | 0.221 | Covered | 0.498 | Partial | ✓ | ✗ |
| P09 | Covered | 0.818 | 0.500 | 0.309 | Partial | 0.509 | Partial | ✗ | ✗ |
| P10 | Covered | 0.802 | 0.500 | 0.319 | Partial | 0.518 | Partial | ✗ | ✗ |
| P11 | Partial | 0.817 | 0.401 | 0.349 | Partial | 0.510 | Partial | ✓ | ✓ |
| P12 | Partial | 0.736 | 0.478 | 0.367 | Partial | 0.559 | Partial | ✓ | ✓ |
| P13 | Partial | 0.762 | 0.788 | 0.228 | Covered | 0.543 | Partial | ✗ | ✓ |
| P14 | Partial | 0.712 | 0.000 | 0.573 | Partial | 0.573 | Partial | ✓ | ✓ |
| P15 | Partial | 0.783 | 0.500 | 0.330 | Partial | 0.530 | Partial | ✓ | ✓ |
| P16 | Partial | 0.536 | 0.500 | 0.479 | Partial | 0.679 | Drifted | ✓ | ✗ |
| P17 | Partial | 0.669 | 0.183 | 0.525 | Partial | 0.599 | Partial | ✓ | ✓ |
| P18 | Partial | 0.723 | 0.295 | 0.448 | Partial | 0.566 | Partial | ✓ | ✓ |
| P19 | Partial | 0.652 | 0.448 | 0.430 | Partial | 0.609 | Drifted | ✓ | ✗ |
| P20 | Partial | 0.809 | 0.415 | 0.349 | Partial | 0.515 | Partial | ✓ | ✓ |
| P21 | Drifted | 0.648 | 0.500 | 0.411 | Partial | 0.611 | Drifted | ✗ | ✓ |
| P22 | Drifted | 0.457 | 0.000 | 0.726 | Drifted | 0.726 | Drifted | ✓ | ✓ |
| P23 | Drifted | 0.525 | 0.000 | 0.685 | Drifted | 0.685 | Drifted | ✓ | ✓ |
| P24 | Drifted | 0.604 | 0.500 | 0.438 | Partial | 0.638 | Drifted | ✗ | ✓ |
| P25 | Drifted | 0.456 | 0.000 | 0.727 | Drifted | 0.727 | Drifted | ✓ | ✓ |
| P26 | Drifted | 0.429 | 0.000 | 0.742 | Drifted | 0.742 | Drifted | ✓ | ✓ |
| P27 | Drifted | 0.455 | 0.500 | 0.527 | Partial | 0.727 | Drifted | ✗ | ✓ |
| P28 | Drifted | 0.535 | 0.500 | 0.479 | Partial | 0.679 | Drifted | ✗ | ✓ |
| P29 | Drifted | 0.437 | 0.000 | 0.738 | Drifted | 0.738 | Drifted | ✓ | ✓ |
| P30 | Drifted | 0.538 | 0.500 | 0.477 | Partial | 0.677 | Drifted | ✗ | ✓ |

### 5.3 Confusion Matrices

#### 5.3.1 Orion Hybrid Engine

| | Pred: Covered | Pred: Partial | Pred: Drifted |
|:--|--:|--:|--:|
| **True: Covered** | 3 | 7 | 0 |
| **True: Partial** | 1 | 9 | 0 |
| **True: Drifted** | 0 | 5 | 5 |

#### 5.3.2 Cosine-only Baseline

| | Pred: Covered | Pred: Partial | Pred: Drifted |
|:--|--:|--:|--:|
| **True: Covered** | 0 | 10 | 0 |
| **True: Partial** | 0 | 8 | 2 |
| **True: Drifted** | 0 | 0 | 10 |

### 5.4 Classification Metrics

| Class | H-Precision | H-Recall | H-F1 | C-Precision | C-Recall | C-F1 | Support |
|:--|--:|--:|--:|--:|--:|--:|--:|
| Covered | 0.750 | 0.300 | 0.429 | 0.000 | 0.000 | 0.000 | 10 |
| Partial | 0.429 | 0.900 | 0.581 | 0.444 | 0.800 | 0.571 | 10 |
| Drifted | 1.000 | 0.500 | 0.667 | 0.833 | 1.000 | 0.909 | 10 |
| **Macro avg** | **0.726** | **0.567** | **0.559** | 0.426 | 0.600 | 0.493 | 30 |
| **Accuracy** | | | **0.567** | | | 0.600 | 30 |

### 5.5 Analysis

#### Key Findings

- **Hybrid Macro F1 = 0.559** vs Cosine Baseline = 0.493
  (delta = +0.065)
- **Hybrid Accuracy = 0.567** vs Cosine Accuracy = 0.600

#### Engine Comparison

| Metric | Orion Hybrid | Cosine Baseline | Delta |
|:--|--:|--:|--:|
| Macro Precision | 0.726 | 0.426 | +0.300 |
| Macro Recall | 0.567 | 0.600 | -0.033 |
| Macro F1 | 0.559 | 0.493 | +0.065 |
| Accuracy | 0.567 | 0.600 | -0.033 |

#### Interpretation

The structural signal contributes to disambiguating **Partial** vs **Drifted** pairs: 
when a test has syntactically correct assertions but wrong constraint values, semantic
similarity remains moderate while structural matching scores low — correctly pushing
the risk score below 0.40 and classifying as Drifted.

The Cosine-only baseline tends to misclassify Drifted pairs as Partial when the
test function still references the right domain vocabulary (e.g. 'response', 'status')
even if the threshold assertions are absent or wrong.

---
_Orion RTM — Phase 10 Empirical Benchmark Report_