# StoryTrace V2: Scientific Claim Red-List & Permitted Phrasing

**Project:** StoryTrace V2 Academic & IP Writing Guidelines  
**Date:** September 19, 2026  
**Auditor:** Antigravity Scientific Integrity & Publication Ethics Group  

---

## 1. Prohibited Marketing Phrasing vs. Permitted Scientific Phrasing

```
+------------------------------------+---------------------------------------------------------------+-----------------------------------------------------------------------------------------------+
| PROHIBITED / RED-LIST TERM         | SCIENTIFIC OR LEGAL RISK                                      | APPROVED SCIENTIFICALLY DEFENSIBLE ALTERNATIVE PHRASING                                       |
+------------------------------------+---------------------------------------------------------------+-----------------------------------------------------------------------------------------------+
| "First system to..."               | Vulnerable to obscure historical prior art; unnecessary.     | "We introduce a neurosymbolic approach coupling relational state tracking with bounded agentic|
|                                    |                                                               | investigation..."                                                                             |
+------------------------------------+---------------------------------------------------------------+-----------------------------------------------------------------------------------------------+
| "State of the art (SOTA)"          | No standardized pre-existing competition benchmark exists.    | "StoryTrace V2 achieves 0.7821 Micro-F1, significantly outperforming unconstrained (0.1333)   |
|                                    |                                                               | and one-shot baselines (p < 0.001)."                                                          |
+------------------------------------+---------------------------------------------------------------+-----------------------------------------------------------------------------------------------+
| "Solves narrative continuity"      | Narrative continuity has open-world subjective exceptions.    | "Mitigates representation and recall bottlenecks in automated screenplay continuity auditing."|
+------------------------------------+---------------------------------------------------------------+-----------------------------------------------------------------------------------------------+
| "Human-level continuity detection" | Requires controlled clinical study vs professional scripteds. | "Achieves 0.9508 precision and 80.91% addressable recall across a 10-film benchmark."         |
+------------------------------------+---------------------------------------------------------------+-----------------------------------------------------------------------------------------------+
| "General-purpose story AI"         | Evaluated specifically on formatted screenplays.              | "Evaluated on multi-genre feature-length screenplays."                                        |
+------------------------------------+---------------------------------------------------------------+-----------------------------------------------------------------------------------------------+
| "Zero false positives"             | Final precision is 0.9508 (34 soft anomaly FPs surfaced).     | "Achieves high precision (0.9508) by filtering 85.71% of candidate false positives."          |
+------------------------------------+---------------------------------------------------------------+-----------------------------------------------------------------------------------------------+
| "Guaranteed error detection"       | Determinism applies to SQL execution, not LLM extraction.     | "Zero-LLM analytical window rules guarantee deterministic candidate generation."             |
+------------------------------------+---------------------------------------------------------------+-----------------------------------------------------------------------------------------------+
| "Novel LLM agent / Novel RAG"      | LLM agents and RAG are general foundation model techniques.   | "A FastMCP tool-augmented ReAct investigation agent with a strict k <= 6 call quota."         |
+------------------------------------+---------------------------------------------------------------+-----------------------------------------------------------------------------------------------+
| "Patented / Patentable system"     | Patentability is an official IPO/USPTO legal determination.   | "An inventive technical combination coupling OLAP state stores with bounded tool-calling."    |
+------------------------------------+---------------------------------------------------------------+-----------------------------------------------------------------------------------------------+
```

---

## 2. Mandatory Terminology Standards

1. **Addressable Ceiling:** Always refer to $82.10\%$ as the *Addressable State Space Ceiling* (the proportion of errors representable in the schema), **never** as the system's final recall.
2. **Candidate Recall:** Always cite $78.08\%$ as *Candidate Detector Recall over Addressable Ground Truth* and $64.11\%$ as *Global Candidate Recall*.
3. **System Recall:** Always cite $80.91\%$ as *Addressable System Recall* and $66.43\%$ as *Global System Recall*.
4. **Precision:** Always cite $0.9508$ alongside its denominator (657 True Positives / 691 Surfaced Findings).
5. **Tool Quota:** Always state that the investigation agent is bounded by a hard cap of $k \le 6$ tool calls per candidate.
