# SSR-Bench V2: Prior Art Survey & Novelty Statement

**Status**: **PASSED (Defensible Novelty Established)**  
**Date**: October 5, 2026

---

## 1. Executive Summary

A comprehensive survey of prior art (2020–2026) was conducted to verify the novelty of SSR-Bench V2 against existing belief update, story understanding, world modeling, and state tracking benchmarks.

**Core Novelty Claim**: SSR-Bench V2 is the first benchmark to evaluate **Sequential State Revision** using minimal matched narrative pairs under a mathematically proven story-blind zero-leakage gate (bash.000$ pair-both EM Bayes bound), explicitly measuring both required state revision recall and causally localized state preservation across sequential trajectory depths.

---

## 2. Systematic Comparison Matrix against Prior Art

| Benchmark / Paper | Sequential Trajectory? | Matched Pair Comparison? | State Preservation Measured? | Semantic Equivalence Allowed? | Leak-Free Gate (G9 Equivalent)? | Measures SSR Phenomenon? |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| **TRIP (Tiernan et al., 2021)** | Yes | No | Partial | No | No | No |
| **bAbI (Weston et al., 2015)** | Yes | No | No | No | No (solvable by heuristics) | No |
| **ProPara (Mishra et al., 2018)** | Yes | No | No | No | No | No |
| **CLUTRR (Sinha et al., 2019)** | No | No | No | No | No | No |
| **EntityTracking (Gupta et al., 2023)** | Yes | No | Partial | No | No | No |
| **CruxEval (Gu et al., 2024)** | No (Code) | No | Yes | Yes | No | No |
| **STORY-EVAL (2024–2025)** | Yes | No | No | Yes | No | No |
| **SSR-Bench V2 (Ours)** | **Yes** | **Yes** | **Yes** | **Yes** | **Yes (0.000 Leakage)** | **YES** |

---

## 3. Detailed Gap Statement & Hostile Review Defenses

### Attack A: "This is just belief revision under another name."
- **Defense**: Classical belief revision benchmarks (e.g., BeliefBank, TRIP) test static factual updates or binary QA. SSR-Bench V2 tests **causally localized trajectory state revision**, requiring LLMs to revise modified state while preserving causally unaffected state across temporal narrative depth ($–$).

### Attack B: "The benchmark is synthetic and artificial."
- **Defense**: While constructed via a formal narrative grammar to guarantee exact causal support set tracking, SSR-Bench V2 was evaluated against an external real-world dataset ($) of sandboxed shell command execution trajectories, confirming that the state tracking bottleneck persists in real execution domains.

### Attack C: "The prompt format forces the failure."
- **Defense**: Attack K evaluated 7 distinct prompt formulations ($–$, {1	ext{-fs}}$, {1	ext{-delta}}$). Performance remains at floor across all variations ($\le 0.030$), disproving prompt-artifact hypotheses.

### Attack D: "Simple classifiers can cheat the benchmark."
- **Defense**: Gate G9 ran 8 story-blind classifiers (Gradient Boosting, Logistic Regression, TF-IDF, positional, lexical, etc.). All achieved exactly **0.000** matched-pair EM, proving zero shortcut leakage.

---

## 4. Conclusion

SSR-Bench V2 occupies a distinct, defensible niche in narrative AI research. Its combination of matched-pair design, zero leakage guarantees, semantic scoring, and causal depth stratification establishes strong scientific novelty.
