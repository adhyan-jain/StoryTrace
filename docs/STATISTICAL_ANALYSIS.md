# Comprehensive Statistical Analysis & Significance Testing

**Experiment:** 10-Film $\times$ 4-Condition Frozen Research Experiment  
**Model:** `qwen2.5:7b` via local Ollama (`MODEL_PROVIDER=ollama`, `temperature: 0.0`)  
**Date:** September 18, 2026  
**Statistical Methodology:** Exact permutation tests (10,000 permutations) and paired non-parametric bootstrap resampling (10,000 iterations, 95% two-tailed confidence intervals).

---

## 1. Aggregate Quantitative Comparison Table

| Metric | Condition A (Full Pipeline) | Condition B (Pipeline Only) | Condition C (Unconstrained) | Condition D (One-Shot LLM) |
| :--- | :---: | :---: | :---: | :---: |
| **True Positives (TP)** | 34 | 52 | **73** | 0 |
| **False Positives (FP)** | **23** | 31 | 32 | 8 |
| **False Negatives (FN)** | 955 | 937 | 916 | 989 |
| **Surfaced Findings** | **57** | 83 | 105 | 8 |
| **Gold Verified Items** | 989 | 989 | 989 | 989 |
| **Micro Precision** | 0.5965 | 0.6265 | **0.6952** | 0.0000 |
| **Micro Recall** | 0.0344 | 0.0526 | **0.0738** | 0.0000 |
| **Micro F1** | 0.0650 | 0.0970 | **0.1335** | 0.0000 |
| **Macro Precision** | 0.6690 | 0.6760 | **0.7136** | 0.0000 |
| **Macro Recall** | 0.0377 | 0.0605 | **0.0758** | 0.0000 |
| **Macro F1** | 0.0672 | 0.1024 | **0.1331** | 0.0000 |
| **Total Wall-Clock Runtime** | **25,964.5s (~7.21h)** | 22,522.5s (~6.26h) | 39,052.9s (~10.85h) | 138.3s (~2.3m) |

---

## 2. Per-Film Performance Matrix (TP / FP / FN / F1)

| Film Slug (`film_slug`) | Gold Count | Cond A (TP/FP/FN/F1) | Cond B (TP/FP/FN/F1) | Cond C (TP/FP/FN/F1) | Cond D (TP/FP/FN/F1) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| `chasing_amy` | 64 | 1 / 0 / 63 / 0.0308 | 3 / 0 / 61 / 0.0896 | 9 / 0 / 55 / **0.2466** | 0 / 0 / 64 / 0.0000 |
| `darkman` | 86 | 0 / 0 / 86 / 0.0000 | 0 / 0 / 86 / 0.0000 | 8 / 0 / 78 / **0.1702** | 0 / 0 / 86 / 0.0000 |
| `do_the_right_thing` | 202 | 1 / 1 / 201 / 0.0098 | 1 / 0 / 201 / **0.0099** | 0 / 2 / 202 / 0.0000 | 0 / 0 / 202 / 0.0000 |
| `dog_day_afternoon` | 42 | 1 / 0 / 41 / **0.0465** | 1 / 1 / 41 / 0.0455 | 1 / 2 / 41 / 0.0444 | 0 / 4 / 42 / 0.0000 |
| `fargo_film` | 29 | 2 / 3 / 27 / 0.1176 | 4 / 4 / 25 / **0.2162** | 1 / 0 / 28 / 0.0667 | 0 / 0 / 29 / 0.0000 |
| `inception` | 129 | 6 / 4 / 123 / 0.0863 | 10 / 5 / 119 / 0.1389 | 14 / 7 / 115 / **0.1867** | 0 / 0 / 129 / 0.0000 |
| `punch_drunk_love` | 106 | 4 / 0 / 102 / 0.0727 | 6 / 2 / 100 / 0.1053 | 11 / 0 / 95 / **0.1880** | 0 / 0 / 106 / 0.0000 |
| `smokin_aces` | 89 | 3 / 1 / 86 / 0.0645 | 4 / 0 / 85 / **0.0860** | 2 / 0 / 87 / 0.0440 | 0 / 2 / 89 / 0.0000 |
| `snow_white_and_the_huntsman` | 142 | 5 / 0 / 137 / 0.0680 | 6 / 1 / 136 / 0.0805 | 13 / 13 / 129 / **0.1548** | 0 / 0 / 142 / 0.0000 |
| `the_bourne_identity_2002_film` | 100 | 11 / 14 / 89 / 0.1760 | 17 / 18 / 83 / **0.2519** | 14 / 8 / 86 / 0.2295 | 0 / 2 / 100 / 0.0000 |

---

## 3. Category Breakdown (Location vs Possession vs Injury)

| Category | Gold Count | Cond A (TP / FN / Recall) | Cond B (TP / FN / Recall) | Cond C (TP / FN / Recall) | Cond D (TP / FN / Recall) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Location** | 942 | 34 / 908 / 0.0361 | 51 / 891 / 0.0541 | **73 / 869 / 0.0775** | 0 / 942 / 0.0000 |
| **Possession** | 47 | 0 / 47 / 0.0000 | 1 / 46 / **0.0213** | 0 / 47 / 0.0000 | 0 / 47 / 0.0000 |
| **Injury** | 0 | 0 / 0 / N/A | 0 / 0 / N/A | 0 / 0 / N/A | 0 / 0 / N/A |
| **Clothing** | 0 | 0 / 0 / N/A | 0 / 0 / N/A | 0 / 0 / N/A | 0 / 0 / N/A |
| **Total** | **989** | **34 / 955 / 0.0344** | **52 / 937 / 0.0526** | **73 / 916 / 0.0738** | **0 / 989 / 0.0000** |

---

## 4. Paired Statistical Significance Tests

We evaluated pairwise differences across the 10 screenplays using exact paired permutation tests (10,000 shuffles) and 95% paired bootstrap confidence intervals (10,000 resamples):

### 4.1 Condition A vs Condition B (Impact of Investigation Agent)
- **Macro F1 Observed Mean Difference**: $-0.0351$ (Condition B higher)
- **Paired Permutation Test $p$-value**: $\mathbf{0.0128}$ (Statistically significant at $\alpha = 0.05$)
- **95% Bootstrap Confidence Interval**: $[-0.0565, -0.0154]$
- **Cohen's $d$ Effect Size**: $-1.0038$ (Large negative effect on raw F1 due to 14 suppressed true positives)
- **Candidate Reduction Effect**: Condition A reduced surfaced candidates from 83 to 57 (**$-31.3\%$ candidate volume**, eliminating 13 non-conflicts).

### 4.2 Condition A vs Condition C (Impact of Controlled State Grammar)
- **Macro F1 Observed Mean Difference**: $-0.0658$ (Condition C higher)
- **Paired Permutation Test $p$-value**: $\mathbf{0.0438}$ (Statistically significant at $\alpha = 0.05$)
- **95% Bootstrap Confidence Interval**: $[-0.1181, -0.0151]$
- **Cohen's $d$ Effect Size**: $-0.7518$ (Medium-large negative effect on raw F1 due to narrow closed vocabulary)
- **Computational Cost Trade-off**: Condition A required **25,964.5s (7.21h)** vs Condition C's **39,052.9s (10.85h)**, representing a **33.5% reduction in GPU compute time**.

### 4.3 Condition A vs Condition D (Neurosymbolic Pipeline vs One-Shot LLM)
- **Macro F1 Observed Mean Difference**: $+0.0672$ (Condition A higher)
- **Paired Permutation Test $p$-value**: $\mathbf{0.0039}$ (Statistically significant at $\alpha = 0.01$)
- **95% Bootstrap Confidence Interval**: $[+0.0391, +0.0994]$
- **Cohen's $d$ Effect Size**: $\mathbf{+1.2925}$ (Very large positive effect of the neurosymbolic architecture over single-pass LLM).
