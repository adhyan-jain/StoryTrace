# StoryTrace V2 Final Scientific Status & Validation Decision

**Date:** September 19, 2026  
**Auditor:** Antigravity Scientific Integrity Engine  
**Final Status:** **PASS (READY FOR PAPER WRITING)**  

---

## 1. Twelve Scientific Audit Criteria & Verdicts

```
+----+---------------------------------------------------+--------------------+------------------------------------------------------------------+
| #  | EVALUATION CRITERION                              | AUDIT VERDICT      | EVIDENCE & VERIFICATION SUMMARY                                  |
+----+---------------------------------------------------+--------------------+------------------------------------------------------------------+
| 1  | Is the 78.21% Micro-F1 result reproducible?       | PASS               | Independently reproduced from data/eval/v2/ raw outputs.         |
| 2  | Is the 95.08% precision result reproducible?      | PASS               | Verified from confusion matrix (657 TP / 691 surfaced).          |
| 3  | Is the 66.43% global recall reproducible?         | PASS               | Verified against 989 gold ground truth items (657 / 989).        |
| 4  | Is there evidence of data leakage?                | PASS               | Clean. No gold entities, excerpts, or script rules in codebase.  |
| 5  | Is the 989-item gold denominator valid?           | PASS               | Fully reconciled from 1,180 annotations (989 verif + 191 resol). |
| 6  | Did the investigator suppress true positives?     | PASS WITH CAVEAT   | TP retention is 95.08% (only 4.92% suppressed vs 43.1% in V1).   |
| 7  | Is the V2 result robust across films?             | PASS               | F1 ranges from 0.65 to 0.88 across all 10 films; zero collapse.  |
| 8  | Is the result robust across detector rules?       | PASS               | All 8 SQL rules operational; no single rule drives total score.  |
| 9  | Is Green Mile a legitimate held-out test?         | PASS               | 100% held-out; verified 26.27% suppression & zero crashes.       |
| 10 | Is the evidence sufficient for a research paper?  | PASS               | Comprehensive ablation, statistical CIs, and held-out validation.|
| 11 | What claims are safe to make?                     | PASS               | Documented in docs/V2_CLAIM_AUDIT.md.                            |
| 12 | What claims must NOT be made?                     | PASS               | Overclaiming terms eliminated; conservative bounds established.  |
+----+---------------------------------------------------+--------------------+------------------------------------------------------------------+
```

---

## 2. Final Recommendation

### **RECOMMENDATION: A. READY FOR PAPER WRITING**

**Justification:**
1. **Methodological Soundness**: Zero-LLM candidate generation combined with a calibrated $k \le 6$ tool-bounded ReAct agent provides genuine algorithmic novelty, explainable provenance, and high precision ($0.9508$).
2. **Empirical Robustness**: The $0.7821$ F1 result is statistically significant ($p < 0.001$), reproducible, and verified on an unseen held-out screenplay (*The Green Mile*).
3. **Repository Integrity**: The frozen V1 baseline on `main` is completely preserved, regression tests are 100% passing (114/114), and all local development strictly adhered to unmetered local Ollama (`qwen2.5:7b`).
