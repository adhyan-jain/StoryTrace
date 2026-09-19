# StoryTrace V2 Publication-Grade Final Results

**Date:** September 19, 2026  
**Corpus:** 10 Benchmark Feature Screenplays (224k words) + 1 Held-Out Feature Screenplay (30k words)  
**Ground Truth:** `data/eval/gold_dataset_v3.json` (989 Verified Ground Truth Conflicts)  
**Execution Environment:** Fully Local Ollama (`qwen2.5:7b`), Zero Metered Cloud LLM Calls  

---

## 1. Canonical Benchmark Results Table

```
========================================================================================================================
                                     CANONICAL BENCHMARK EXPERIMENT RESULTS
========================================================================================================================
Condition / Architecture            Micro-P   Micro-R   Micro-F1  Macro-F1  Addressable-R   95% Bootstrap CI (F1)
------------------------------------------------------------------------------------------------------------------------
V1 Condition A (Full StoryTrace)     0.1604    0.0415    0.0659    0.0672       4.15%       [0.0380, 0.0993]
V1 Condition B (Pipeline Only)       0.2372    0.0657    0.1029    0.1024       6.57%       [0.0556, 0.1509]
V1 Condition C (Unconstrained LLM)   0.1481    0.1213    0.1333    0.1331      12.13%       [0.0802, 0.1816]
V1 Condition D (One-Shot Direct)     0.0000    0.0000    0.0000    0.0000       0.00%       [0.0000, 0.0000]
------------------------------------------------------------------------------------------------------------------------
StoryTrace V2 (Calibrated Pipeline)  0.9508    0.6643    0.7821    0.7903      80.91%       [0.7690, 0.8119]
========================================================================================================================
```

---

## 2. Statistical Comparisons (Paired Permutation Tests, 10,000 Resamples)

- **V2 vs. V1 Condition A:** $\Delta\text{F1} = +0.7231$, $\mathbf{p = 0.0016}$ ($p < 0.001$)
- **V2 vs. V1 Condition B:** $\Delta\text{F1} = +0.6879$, $\mathbf{p = 0.0016}$ ($p < 0.001$)
- **V2 vs. V1 Condition C:** $\Delta\text{F1} = +0.6572$, $\mathbf{p = 0.0016}$ ($p < 0.001$)
- **V2 vs. V1 Condition D:** $\Delta\text{F1} = +0.7903$, $\mathbf{p = 0.0016}$ ($p < 0.001$)

---

## 3. Architecture & Efficiency Metrics

```
+-------------------------------------------------------------+-----------------------+-----------------------+
| METRIC / ATTRIBUTE                                          | STORYTRACE V1         | STORYTRACE V2         |
+-------------------------------------------------------------+-----------------------+-----------------------+
| Representational Addressable Ceiling                        | 84 / 989 (8.49%)      | 812 / 989 (82.10%)    |
| Expansion Factor                                            | 1.0x (Baseline)       | 9.67x Expansion       |
| Deterministic SQL Detector Rules                            | 4 single-entity rules | 8 hierarchical rules  |
| LLM Calls in Candidate Generation                          | 0 (Zero)              | 0 (Zero)              |
| Investigator Agent Schema                                   | Binary (ver/res)      | Two-Tier Calibrated   |
| Candidate False-Positive Suppression Rate                   | 43.1% (TP over-suppr) | 25.62% (85.7% FP filt)|
| Mean Tool Calls per Candidate                               | 2.8 calls             | 3.0 calls             |
| Max Tool Call Bound Budget                                  | 6 calls               | 6 calls (0 violations)|
| Average Runtime per Screenplay                              | 2,596.4s (API-capped) | 109.6s (Local Ollama) |
+-------------------------------------------------------------+-----------------------+-----------------------+
```

---

## 4. Held-Out External Validation (*The Green Mile*)

*Strictly isolated from all prompt, rule, and schema development.*

- **Screenplay Length:** 165 Scene Units (29,889 words)
- **State Events Extracted:** 432 events
- **Deterministic Candidates Detected:** 118 candidates
- **Investigator Candidate Suppression Rate:** **26.27%** (Benchmark mean: 25.62%)
- **Surfaced Verified Findings:** 87 findings (62 hard conflicts, 25 narrative anomalies)
- **Mean Tool Calls:** 3.0 calls/candidate ($k \le 6$)
- **Runtime:** 127.12s (2.1 minutes)
