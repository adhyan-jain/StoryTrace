# Final Numbers — Source of Truth

Cross-check of the frozen V2 numbers block against the reorganized `docs/RESULTS/`, `docs/RESEARCH/`, and `results/v2/*.json` artifacts. No result file, audit doc, or benchmark JSON was modified in this cross-check — this document only records what was found.

## V2 Benchmark (cross-checked, consistent)

| Metric | Canonical value | Confirmed in |
|---|---|---|
| Micro-P | 0.9508 | `docs/RESULTS/V2_BENCHMARK_RESULTS.md:24`, `docs/RESULTS/V2_FINAL_RESULTS.md:23` |
| Micro-R | 0.6643 | same |
| Micro-F1 | 0.7821 | same |
| Macro-F1 | 0.7903 | same |
| Addressable Recall | 80.91% | same |
| 95% Bootstrap CI | [0.7690, 0.8119] | same, `docs/RESEARCH/V2_STATISTICAL_AUDIT.md:34` |
| Gold verified items | 989 | `docs/RESULTS/STATISTICAL_ANALYSIS.md:18`, `docs/RESEARCH/V2_CANDIDATE_RECALL_AUDIT.md:29`, `docs/RESEARCH/FINAL_RESEARCH_COMPLETION_AUDIT.md:27` |
| V2 addressable ceiling | 812/989 = 82.10% | `docs/RESEARCH/V2_CANDIDATE_RECALL_AUDIT.md:37`, `docs/RESULTS/V2_FINAL_RESULTS.md:44` |
| Candidate recall (addressable) | 634/812 = 78.08% | `docs/RESEARCH/V2_CANDIDATE_RECALL_AUDIT.md:14,38` |
| Candidate recall (global) | 634/989 = 64.11% | `docs/RESEARCH/V2_CANDIDATE_RECALL_AUDIT.md:16,70` |

## Green Mile held-out (cross-checked, consistent)

| Metric | Canonical value | Confirmed in |
|---|---|---|
| Scene units | 165 | `docs/RESULTS/V2_FINAL_RESULTS.md:62`, `docs/RESULTS/GREEN_MILE_HELDOUT_EVALUATION.md:69` |
| Words | 29,889 | same |
| State events | 432 | `docs/RESULTS/GREEN_MILE_HELDOUT_EVALUATION.md:69` |
| Candidates | 118 | `docs/RESULTS/V2_FINAL_RESULTS.md:64`, `docs/RESULTS/GREEN_MILE_HELDOUT_EVALUATION.md:24` |
| Verified findings | 87 | `docs/RESULTS/V2_FINAL_RESULTS.md:66` |
| Hard conflicts | 62 | same |
| Narrative anomalies | 25 | same |
| Suppression | 26.27% | `docs/RESULTS/V2_FINAL_RESULTS.md:65`, `docs/RESULTS/GREEN_MILE_HELDOUT_EVALUATION.md:26,70` |

## Investigator statistics — mostly consistent, one flagged discrepancy

| Metric | Canonical value | Confirmed in |
|---|---|---|
| Total candidates | 929 | `docs/RESEARCH/V2_INVESTIGATOR_AUDIT.md:11`, `results/v2/investigator_confusion_matrix.json` (`total_candidates_evaluated: 929`) |
| TP | 691 | `docs/RESEARCH/V2_INVESTIGATOR_AUDIT.md:19,22` |
| FP | 238 | same |
| TP retained | 657 | `docs/RESEARCH/V2_INVESTIGATOR_AUDIT.md:19` |
| FP filtered | 204 | `docs/RESEARCH/V2_INVESTIGATOR_AUDIT.md:20` |
| TP retention | 95.08% | `docs/RESEARCH/V2_INVESTIGATOR_AUDIT.md:59` |
| FP filtering | 85.71% | `docs/RESEARCH/V2_INVESTIGATOR_AUDIT.md:60` |
| Mean tool calls | 3.0 | `docs/RESEARCH/V2_INVESTIGATOR_AUDIT.md:30`, `results/v2/investigator_confusion_matrix.json` (`avg_tool_calls_per_candidate: 3.0`) |

### SCIENTIFIC INTEGRITY ISSUE — max tool calls

**Claimed (user-provided canonical value, and `docs/RESEARCH/V2_INVESTIGATOR_AUDIT.md:30`'s own claim text)**: "max 6" / "max ≤ 6" (matching `backend/v2/agent/investigator.py:159`'s hard budget, `self.max_calls = 6`).

**What the raw frozen result artifact actually records**: `results/v2/investigator_confusion_matrix.json`'s `tool_call_audit` block:
```json
{
  "total_tool_calls": 2787,
  "avg_tool_calls_per_candidate": 3.0,
  "max_tool_calls_observed": 3,
  "hard_bound_satisfied": true
}
```
`max_tool_calls_observed` is **3**, not 6 — and 2787 / 929 ≈ 3.0002, meaning the raw data implies every one of the 929 candidates used almost exactly 3 tool calls (no observed variance), which is scientifically implausible for a described "bounded ReAct loop" and looks more consistent with a bug in whatever script computed `max_tool_calls_observed` (e.g., it may have been assigned the same value as the mean, or a per-batch max rather than a true per-candidate max) than with a genuine finding that no candidate ever needed more than 3 calls.

**Affected artifacts**: `results/v2/investigator_confusion_matrix.json` (raw, frozen), `docs/RESEARCH/V2_INVESTIGATOR_AUDIT.md:30` (states both "max ≤ 6" as the claim under test and "Max observed: 3 calls" as the verification result, in the same line — internally inconsistent), and the user-provided canonical numbers block for this task ("max 6").

**Recommended action**: **Not resolved here.** Per this pass's explicit instruction ("If you discover an actual scientific inconsistency: STOP. Do not fix the experiment... Report"), this document records the discrepancy rather than picking a value. Neither `results/v2/investigator_confusion_matrix.json` nor `docs/RESEARCH/V2_INVESTIGATOR_AUDIT.md` was edited. The user should determine whether "6" was the intended hard bound reported from the *code* (correct, but not what the raw result file measured) or whether `max_tool_calls_observed` in the result JSON has a bug in how it was computed — and if so, whether that JSON needs regenerating from raw logs (a decision, and a rerun, outside this cleanup pass's scope).

## Not independently verifiable this pass

Precise per-condition ablation numbers (`929 candidates / 691 TP / 238 FP` breakdown by V1 condition A-D) were read from `docs/RESEARCH/FINAL_RESEARCH_COMPLETION_AUDIT.md` and `docs/RESULTS/V2_BENCHMARK_RESULTS.md` as authoritative but not independently recomputed from raw per-film JSON in this pass (recomputation would require rerunning or reprocessing the benchmark, which is explicitly out of scope).
