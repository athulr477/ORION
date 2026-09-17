# Orion RTM — Empirical Benchmark Evaluation Report

> Generated: 2026-09-17 19:43:16
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
| P01 | Covered | 0.762 | 0.320 | 0.585 | Partial | 0.762 | Covered | ✗ | ✓ |
| P02 | Covered | 0.832 | 0.300 | 0.619 | Partial | 0.832 | Covered | ✗ | ✓ |
| P03 | Covered | 0.693 | 0.300 | 0.536 | Partial | 0.693 | Partial | ✗ | ✗ |
| P04 | Covered | 0.900 | 0.400 | 0.700 | Partial | 0.900 | Covered | ✗ | ✓ |
| P05 | Covered | 0.784 | 0.180 | 0.542 | Partial | 0.784 | Covered | ✗ | ✓ |
| P06 | Covered | 0.859 | 0.300 | 0.635 | Partial | 0.859 | Covered | ✗ | ✓ |
| P07 | Covered | 0.803 | 0.300 | 0.602 | Partial | 0.803 | Covered | ✗ | ✓ |
| P08 | Covered | 0.836 | 0.320 | 0.630 | Partial | 0.836 | Covered | ✗ | ✓ |
| P09 | Covered | 0.818 | 0.300 | 0.611 | Partial | 0.818 | Covered | ✗ | ✓ |
| P10 | Covered | 0.802 | 0.300 | 0.602 | Partial | 0.802 | Covered | ✗ | ✓ |
| P11 | Partial | 0.817 | 0.200 | 0.570 | Partial | 0.817 | Covered | ✓ | ✗ |
| P12 | Partial | 0.736 | 0.433 | 0.615 | Partial | 0.736 | Partial | ✓ | ✓ |
| P13 | Partial | 0.762 | 0.200 | 0.537 | Partial | 0.762 | Covered | ✓ | ✗ |
| P14 | Partial | 0.712 | 0.000 | 0.427 | Partial | 0.712 | Partial | ✓ | ✓ |
| P15 | Partial | 0.783 | 0.300 | 0.590 | Partial | 0.783 | Covered | ✓ | ✗ |
| P16 | Partial | 0.536 | 0.300 | 0.441 | Partial | 0.536 | Partial | ✓ | ✓ |
| P17 | Partial | 0.669 | 0.000 | 0.401 | Partial | 0.669 | Partial | ✓ | ✓ |
| P18 | Partial | 0.723 | 0.128 | 0.485 | Partial | 0.723 | Partial | ✓ | ✓ |
| P19 | Partial | 0.652 | 0.200 | 0.471 | Partial | 0.652 | Partial | ✓ | ✓ |
| P20 | Partial | 0.809 | 0.200 | 0.565 | Partial | 0.809 | Covered | ✓ | ✗ |
| P21 | Drifted | 0.648 | 0.300 | 0.509 | Partial | 0.648 | Partial | ✗ | ✗ |
| P22 | Drifted | 0.457 | 0.000 | 0.274 | Drifted | 0.457 | Partial | ✓ | ✗ |
| P23 | Drifted | 0.525 | 0.000 | 0.315 | Drifted | 0.525 | Partial | ✓ | ✗ |
| P24 | Drifted | 0.604 | 0.300 | 0.482 | Partial | 0.604 | Partial | ✗ | ✗ |
| P25 | Drifted | 0.456 | 0.000 | 0.273 | Drifted | 0.456 | Partial | ✓ | ✗ |
| P26 | Drifted | 0.429 | 0.000 | 0.258 | Drifted | 0.429 | Partial | ✓ | ✗ |
| P27 | Drifted | 0.455 | 0.300 | 0.393 | Drifted | 0.455 | Partial | ✓ | ✗ |
| P28 | Drifted | 0.535 | 0.300 | 0.441 | Partial | 0.535 | Partial | ✗ | ✗ |
| P29 | Drifted | 0.437 | 0.000 | 0.262 | Drifted | 0.437 | Partial | ✓ | ✗ |
| P30 | Drifted | 0.538 | 0.300 | 0.443 | Partial | 0.538 | Partial | ✗ | ✗ |

### 5.3 Confusion Matrices

#### 5.3.1 Orion Hybrid Engine

| | Pred: Covered | Pred: Partial | Pred: Drifted |
|:--|--:|--:|--:|
| **True: Covered** | 0 | 10 | 0 |
| **True: Partial** | 0 | 10 | 0 |
| **True: Drifted** | 0 | 4 | 6 |

#### 5.3.2 Cosine-only Baseline

| | Pred: Covered | Pred: Partial | Pred: Drifted |
|:--|--:|--:|--:|
| **True: Covered** | 9 | 1 | 0 |
| **True: Partial** | 4 | 6 | 0 |
| **True: Drifted** | 0 | 10 | 0 |

### 5.4 Classification Metrics

| Class | H-Precision | H-Recall | H-F1 | C-Precision | C-Recall | C-F1 | Support |
|:--|--:|--:|--:|--:|--:|--:|--:|
| Covered | 0.000 | 0.000 | 0.000 | 0.692 | 0.900 | 0.783 | 10 |
| Partial | 0.417 | 1.000 | 0.588 | 0.353 | 0.600 | 0.444 | 10 |
| Drifted | 1.000 | 0.600 | 0.750 | 0.000 | 0.000 | 0.000 | 10 |
| **Macro avg** | **0.472** | **0.533** | **0.446** | 0.348 | 0.500 | 0.409 | 30 |
| **Accuracy** | | | **0.533** | | | 0.500 | 30 |

### 5.5 Analysis

#### Key Findings

- **Hybrid Macro F1 = 0.446** vs Cosine Baseline = 0.409
  (delta = +0.037)
- **Hybrid Accuracy = 0.533** vs Cosine Accuracy = 0.500

#### Engine Comparison

| Metric | Orion Hybrid | Cosine Baseline | Delta |
|:--|--:|--:|--:|
| Macro Precision | 0.472 | 0.348 | +0.124 |
| Macro Recall | 0.533 | 0.500 | +0.033 |
| Macro F1 | 0.446 | 0.409 | +0.037 |
| Accuracy | 0.533 | 0.500 | +0.033 |

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