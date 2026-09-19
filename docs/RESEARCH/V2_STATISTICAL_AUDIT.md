# StoryTrace V2 Statistical Significance & Methodology Audit

**Date:** September 19, 2026  
**Auditor:** Antigravity Scientific Integrity Engine  
**Dataset Unit:** N = 10 Benchmark Screenplays (989 Verified Ground Truth Items)  

---

## 1. Executive Summary & Significance Summary

StoryTrace V2 achieves statistically significant improvements over all V1 experimental conditions (Condition A Full Pipeline, Condition B Pipeline Only, Condition C Unconstrained LLM, and Condition D One-Shot Baseline) under rigorous two-tailed paired permutation testing (10,000 resamples).

```
========================================================================================================
                                     STATISTICAL SIGNIFICANCE SUMMARY
========================================================================================================
Comparison Pair           Effect Size (Mean ΔF1)   p-value (10k perms)   Significance Level (α = 0.01)
--------------------------------------------------------------------------------------------------------
V2 vs. V1 Condition A      +0.7230                   p = 0.0016               SIGNIFICANT (p < 0.01)
V2 vs. V1 Condition B      +0.6879                   p = 0.0016               SIGNIFICANT (p < 0.01)
V2 vs. V1 Condition C      +0.6572                   p = 0.0016               SIGNIFICANT (p < 0.01)
V2 vs. V1 Condition D      +0.7903                   p = 0.0016               SIGNIFICANT (p < 0.01)
========================================================================================================
```

---

## 2. 95% Bootstrap Confidence Intervals (2,000 Resamples)

- **V1 Condition A (Full Pipeline):** (0.038, 0.0993) (Mean Macro-F1 = 0.0672)
- **V1 Condition B (Pipeline Only):** (0.0556, 0.1509) (Mean Macro-F1 = 0.1024)
- **V1 Condition C (Unconstrained LLM):** (0.0802, 0.1816) (Mean Macro-F1 = 0.1331)
- **V1 Condition D (One-Shot Direct):** (0.0, 0.0) (Mean Macro-F1 = 0.0000)
- **StoryTrace V2 (Calibrated Pipeline):** **(0.769, 0.8119)** (Mean Macro-F1 = **0.7903**)

*Note:* There is zero overlap between V2's 95% confidence interval `[0.769, 0.8119]` and any V1 condition's upper bound (highest V1 upper bound is Condition C at `0.1816`), confirming non-overlapping confidence intervals at the 95% level.

---

## 3. Methodological Audit & Power Caveats

### Paired Comparison Appropriateness:
- **Unit of Pairing:** Screenplay-level Macro-F1 scores across identical film instances.
- **Justification:** Because every condition evaluated the exact same 10 screenplay texts, pairing by film controls for screenplay length, dialogue density, and scene complexity variance.

### Sample Size & Statistical Power:
- **Macro Unit Limitation ($N = 10$):** While the item-level denominator ($N = 989$ gold items) provides substantial micro-statistical power, the macro unit is bounded by the 10 film corpus.
- **Scientific Disclosure:** The research paper must report both micro-level item performance ($N=989$) and film-level paired permutation tests ($N=10$) with conservative confidence intervals.

---

## 4. Audit Conclusion

- **Audit Status:** **PASS**.
- Permutation procedures, seeds, effect sizes, and bootstrap intervals are strictly reproducible from raw experimental outputs.
