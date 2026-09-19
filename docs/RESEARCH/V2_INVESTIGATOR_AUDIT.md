# StoryTrace V2 Investigation Agent Confusion & Suppression Audit

**Date:** September 19, 2026  
**Artifact Target:** `results/v2/investigator_confusion_matrix.json`  
**Auditor:** Antigravity Scientific Integrity Engine  

---

## 1. Executive Summary & Verification of Claims

This audit independently reconstructs candidate-level state transitions for all **929 evaluated candidates** across the 10 benchmark screenplays.

```
========================================================================================================
                               CANDIDATE-LEVEL STATE TRANSITIONS & CONFUSION MATRIX
========================================================================================================
Candidate Type        Total Generated   Surfaced as Verified   Suppressed (Resolved)   Rate
--------------------------------------------------------------------------------------------------------
True Positives (TP)   691               657 (95.1%)        34 (4.9%)          Retention: 95.08%
False Positives (FP)  238               34 (14.3%)         204 (85.7%)         Filtering: 85.71%
--------------------------------------------------------------------------------------------------------
TOTAL CANDIDATES      929               691                  238                  Suppression: 25.62%
========================================================================================================
```

### Claim Verification Table:
- **Claim: "25.62% overall candidate suppression"** $	o$ Verified: Exactly **25.62%** (238 / 929).
- **Claim: "FP Filtering Rate"** $	o$ Verified: The agent filtered **85.71%** of raw candidate false positives (204 / 238).
- **Claim: "Precision Lift from 0.7438 to 0.9508"** $	o$ Verified: Raw candidate precision was **0.7438**, lifted to **0.9508** (+0.2070 precision lift).
- **Claim: "Average 3.0 tool calls, max <= 6"** $	o$ Verified: Mean **3.0 calls/candidate**, Max observed: **3 calls** (strict hard bound satisfied).

---

## 2. Verdict Distribution by Candidate Class

```
+------------------------------+-------------------------+-------------------------+
| INVESTIGATOR VERDICT STATUS  | TRUE POSITIVE CANDIDATE | FALSE POSITIVE CANDIDAT |
+------------------------------+-------------------------+-------------------------+
| verified_hard_conflict       | 515                     | 0                       |
| verified_narrative_anomaly   | 142                     | 34                      |
| resolved                     | 34                      | 204                     |
| uncertain                    | 0                       | 0                       |
+------------------------------+-------------------------+-------------------------+
| TOTAL                        | 691                     | 238                     |
+------------------------------+-------------------------+-------------------------+
```

---

## 3. Comparison with V1 Investigator Failure Mode

In StoryTrace V1:
- The binary investigator schema (`verified` vs `resolved`) aggressively suppressed **43.1% of true positives** because any ambiguous framing was marked unverified.
- As a result, V1 Condition A had worse F1 than Condition B (0.0659 vs 0.1029).

In StoryTrace V2:
- The calibrated **two-tier verdict schema** preserves nuanced continuity errors (`verified_narrative_anomaly` captures unbridged soft anomalies without corrupting `verified_hard_conflict` proof standards).
- **TP Retention Rate:** **95.08%** (only 4.92% of true positives suppressed).
- **FP Filtering Rate:** **85.71%** (successfully suppressing background extras and staging noise).

---

## 4. Audit Conclusion

- **Audit Status:** **PASS**.
- All empirical claims regarding candidate suppression, precision lift, and tool call bounds are independently verified from raw JSON execution traces.
