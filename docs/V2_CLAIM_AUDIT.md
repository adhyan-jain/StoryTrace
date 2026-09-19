# StoryTrace V2 Scientific Claims & Scope Audit

**Date:** September 19, 2026  
**Auditor:** Antigravity Scientific Integrity Engine  
**Objective:** Audit all research statements against empirical evidence to eliminate overclaiming and establish publication-defensible academic phrasing.

---

## 1. Research Claim Audit Table

```
+-----------------------------------------------------+---------------------------------------------------------+-----------------------------------------------------------------------------------------------+
| ORIGINAL / PROBLEMATIC CLAIM                        | SCIENTIFIC VULNERABILITY / DEFECT                       | RECOMMENDED SCIENTIFICALLY DEFENSIBLE WORDING                                                 |
+-----------------------------------------------------+---------------------------------------------------------+-----------------------------------------------------------------------------------------------+
| "The recall bottleneck was resolved."               | Overclaims universality; 17.9% of gold conflicts remain | "The representational coverage bottleneck was substantially mitigated, expanding the           |
|                                                     | unaddressable due to dialogue/mood subtleties.          | addressable state space from 8.49% to 82.10% on the benchmark corpus."                        |
+-----------------------------------------------------+---------------------------------------------------------+-----------------------------------------------------------------------------------------------+
| "StoryTrace achieves human-level continuity error   | No human baseline or clinical inter-annotator study has | "StoryTrace achieves 0.7821 Micro-F1 and 0.9508 precision across a multi-genre benchmark     |
| detection."                                         | been executed against professional continuity scripteds.| of 10 feature screenplays."                                                                   |
+-----------------------------------------------------+---------------------------------------------------------+-----------------------------------------------------------------------------------------------+
| "100% deterministic candidate generation guarantees | Determinism guarantees reproducible SQL execution, not  | "Zero-LLM SQL window rules guarantee reproducible candidate detection with bounded latency   |
| zero false negatives."                              | zero false negatives (window size limits exist).        | and 78.08% candidate recall over addressable ground truth."                                    |
+-----------------------------------------------------+---------------------------------------------------------+-----------------------------------------------------------------------------------------------+
| "The investigation agent eliminates all false       | The agent filters 85.71% of candidate false positives, | "The calibrated ReAct agent filtered 85.71% of candidate false positives, lifting final       |
| positives."                                         | but surfaces 34 false positives as soft anomalies.      | precision from 0.7438 to 0.9508."                                                             |
+-----------------------------------------------------+---------------------------------------------------------+-----------------------------------------------------------------------------------------------+
| "Superior performance across all screenplays."      | Claims universal generalization from a 10-film corpus.  | "StoryTrace V2 demonstrated statistically significant improvements (p < 0.001) over V1 across |
|                                                     |                                                         | the 10-film benchmark and consistent stability on the held-out screenplay The Green Mile."    |
+-----------------------------------------------------+---------------------------------------------------------+-----------------------------------------------------------------------------------------------+
| "Production-ready automated continuity supervisor." | System targets pre-production screenplay texts, not live| "An automated screenplay continuity audit system providing explainable, provenance-grounded   |
|                                                     | on-set video or production footage.                     | continuity anomaly reports for narrative screenplays."                                        |
+-----------------------------------------------------+---------------------------------------------------------+-----------------------------------------------------------------------------------------------+
```

---

## 2. Permitted vs. Prohibited Claims Summary

### Prohibited Claims:
- Do NOT claim that StoryTrace "solves" narrative continuity.
- Do NOT claim 0% false positives or 100% recall.
- Do NOT claim superiority over human continuity supervisors without a formal human baseline.
- Do NOT claim real-time on-set video analysis.

### Permitted & Defensible Claims:
- StoryTrace V2's 4-tier spatial hierarchy and temporal anchoring expand representational addressability by 9.67x over V1.
- Deterministic SQL analytical window rules generate candidates with zero LLM inference calls.
- FastMCP tool-augmented ReAct investigation achieves 0.9508 precision with a bounded $k \le 6$ tool call budget.
- Statistically significant ($p < 0.001$) improvement over unconstrained and one-shot LLM baselines.
- Generalization verified on the held-out screenplay *The Green Mile* without post-hoc tuning.
