# StoryTrace V2: Claim-Element Overlap Matrix

**Project:** StoryTrace V2 Technical IP Evaluation  
**Date:** September 19, 2026  
**Auditor:** Antigravity IP & Novelty Analysis Group  

---

## 1. Atomic Technical Elements (E1 – E15)

- **E1:** Hierarchical screenplay scene segmentation (sluglines, narrative units, sequence numbers).
- **E2:** Controlled semantic state grammar (4-tier spatial hierarchy, temporal anchors, typed state transitions).
- **E3:** Append-only temporal narrative state database.
- **E4:** Normalized tuple representation `(entity_id, attribute, value, sequence_number, raw_excerpt)`.
- **E5:** Scene-level co-presence tracking (disjoint simultaneous presence detection).
- **E6:** Deterministic analytical candidate generation (zero LLM inference during candidate discovery).
- **E7:** Parameterized SQL analytical window functions (`lagInFrame`, temporal bounds) for anomaly discovery.
- **E8:** Candidate-first selective investigation architecture (decoupling candidate discovery from adjudication).
- **E9:** Targeted retrieval tool bridge for intervening narrative units and temporal trajectories.
- **E10:** Strictly bounded tool-call ReAct agent investigation ($k \le 6$ calls per candidate).
- **E11:** Automated duplicate tool-call and infinite loop prevention.
- **E12:** Closed calibrated two-tier verdict schema (`verified_hard_conflict`, `verified_narrative_anomaly`, `resolved`, `uncertain`).
- **E13:** Verbatim textual provenance linking with character-level substring grounding.
- **E14:** Investigation agent executing *exclusively* on surfaced candidates rather than full-script scans.
- **E15:** Verdict generation grounded strictly in retrieved tool observations before categorical enum selection.

---

## 2. Claim-Element Prior Art Comparison Matrix

```
+---------------------+----+----+----+----+----+----+----+----+----+-----+-----+-----+-----+-----+-----+
| SYSTEM / PRIOR ART  | E1 | E2 | E3 | E4 | E5 | E6 | E7 | E8 | E9 | E10 | E11 | E12 | E13 | E14 | E15 |
+---------------------+----+----+----+----+----+----+----+----+----+-----+-----+-----+-----+-----+-----+
| US 10,489,482       |YES |PART| NO |PART| NO | NO | NO | NO | NO | NO  | NO  | NO  |PART | NO  | NO  |
| (Scheduling Parser) |    |    |    |    |    |    |    |    |    |     |     |     |     |     |     |
+---------------------+----+----+----+----+----+----+----+----+----+-----+-----+-----+-----+-----+-----+
| US 11,256,928       |YES |PART| NO | NO | NO |PART| NO | NO | NO | NO  | NO  |PART | NO  | NO  | NO  |
| (Script AI NLP)     |    |    |    |    |    |    |    |    |    |     |     |     |     |     |     |
+---------------------+----+----+----+----+----+----+----+----+----+-----+-----+-----+-----+-----+-----+
| US 2024/0119280     |PART|PART|PART|PART|PART| NO | NO | NO |PART| NO  | NO  | NO  | NO  | NO  | NO  |
| (Narrative KG)      |    |    |    |    |    |    |    |    |    |     |     |     |     |     |     |
+---------------------+----+----+----+----+----+----+----+----+----+-----+-----+-----+-----+-----+-----+
| STAGE (2026)        |YES |PART| NO |PART|PART| NO | NO | NO | NO | NO  | NO  | NO  |PART | NO  | NO  |
| (Screenplay Bench)  |    |    |    |    |    |    |    |    |    |     |     |     |     |     |     |
+---------------------+----+----+----+----+----+----+----+----+----+-----+-----+-----+-----+-----+-----+
| ATLAS (2025)        |PART|PART|PART|PART|PART| NO | NO |PART|PART| NO  | NO  | NO  | NO  | NO  | NO  |
| (Temporal Graph)    |    |    |    |    |    |    |    |    |    |     |     |     |     |     |     |
+---------------------+----+----+----+----+----+----+----+----+----+-----+-----+-----+-----+-----+-----+
| ConStory (ACL 2026) | NO | NO | NO | NO | NO | NO | NO | NO |PART|PART | NO  |PART |PART | NO  | NO  |
| (Monolithic Judge)  |    |    |    |    |    |    |    |    |    |     |     |     |     |     |     |
+---------------------+----+----+----+----+----+----+----+----+----+-----+-----+-----+-----+-----+-----+
| E²RAG (2026)        | NO |PART| NO |PART| NO | NO | NO |PART|YES | NO  | NO  | NO  |PART | NO  |PART |
| (Event RAG QA)      |    |    |    |    |    |    |    |    |    |     |     |     |     |     |     |
+---------------------+----+----+----+----+----+----+----+----+----+-----+-----+-----+-----+-----+-----+
| CANVAS (2026)       | NO | NO | NO | NO | NO | NO | NO |PART|YES |PART |PART | NO  |YES  | NO  |PART |
| (Agent Provenance)  |    |    |    |    |    |    |    |    |    |     |     |     |     |     |     |
+---------------------+----+----+----+----+----+----+----+----+----+-----+-----+-----+-----+-----+-----+
| STORYTRACE V2       |YES |YES |YES |YES |YES |YES |YES |YES |YES |YES  |YES  |YES  |YES  |YES  |YES  |
+---------------------+----+----+----+----+----+----+----+----+----+-----+-----+-----+-----+-----+-----+
```

---

## 3. Element Overlap Insights

1. **Common Elements (Non-Claimable in Isolation):**
   - `E1` (Scene segmentation) and `E4` (Tuple extraction) are standard in natural language processing and screenplay management software.
   - `E9` (RAG retrieval) and `E10` (ReAct agents) are general foundation model concepts.
2. **Distinctive Individual Elements:**
   - `E6` / `E7` (Deterministic zero-LLM SQL analytical window functions for continuity candidate generation over screenplay state). No prior art uses OLAP window queries (`lagInFrame`) to find narrative contradictions.
   - `E12` (Two-tier calibrated verdict classification separating physical impossibility from soft anomaly).
   - `E14` (Confining agent execution exclusively to pre-filtered deterministic candidates, preventing full-corpus scanning).
3. **The Synergistic Inventive Combination:**
   - The specific operational bridge: $\mathbf{E2} \land \mathbf{E3} \land \mathbf{E7} \land \mathbf{E8} \land \mathbf{E10} \land \mathbf{E12} \land \mathbf{E14}$ (Hierarchical State $\to$ Append-Only Store $\to$ SQL Window Detection $\to$ Selective Bounded Agent Investigation $\to$ Calibrated Verdict).
