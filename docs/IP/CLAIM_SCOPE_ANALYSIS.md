# Patent Claim Scope Analysis: StoryTrace System

**Project:** StoryTrace (Multi-Document Narrative Continuity Verification Engine)  
**Author:** Adhyan Jain (VIT Vellore)  
**Date:** September 18, 2026  
**Status:** IP Scope Analysis for Patent Attorney & Faculty Review  

---

## 1. Multi-Tier Claim Scope Definitions

```
+--------------------------------------------------------------------------------------------------+
|                                    CLAIM HIERARCHY & SCOPE                                       |
+--------------------------------------------------------------------------------------------------+
|                                                                                                  |
|   [CLAIM SCOPE A: BROAD]                                                                         |
|   Two-tier continuity verification: (1) Deterministic state filter + (2) Agentic verification    |
|   ├── Vulnerability: High 103 Obviousness risk if decoupled from specific data structures        |
|                                                                                                  |
|   [CLAIM SCOPE B: MEDIUM]                                                                        |
|   Closed-vocabulary state logging + SQL window functions (lagInFrame) + Bounded ReAct agent      |
|   ├── Defensive: Strong novelty in combining closed state grammars with OLAP window analytics    |
|                                                                                                  |
|   [CLAIM SCOPE C: NARROW / MECHANISM-SPECIFIC]                                                   |
|   ClickHouse MergeTree event store + Exact SQL window partition + FastMCP stdio tool interface   |
|   + Bounded ReAct loop (max k calls) with verbatim character-offset provenance validation        |
|   └── Strongest: Highly defensible against 102/103; directly mapped to shipped codebase          |
+--------------------------------------------------------------------------------------------------+
```

---

## 2. Detailed Claim Element Breakdown & 35 U.S.C. 102/103 Risk Analysis

### Claim Scope A (Broad System Claim)
> *A computer-implemented method for narrative verification comprising: parsing a narrative manuscript into an ordered sequence of narrative units; extracting state assertions for resolved entities; storing state assertions in a database; evaluating state transitions to generate candidate contradictions; and deploying an artificial intelligence agent to verify said candidate contradictions against narrative context.*

* **Supporting Implementation:** [`backend/pipeline/run_pipeline.py`](file:///home/adhyan/Desktop/StoryTrace/backend/pipeline/run_pipeline.py)
* **Prior Art Overlap:** Substantially overlaps with general narrative RAG systems, ConStory-Checker, and US Patent 11,256,928.
* **Novelty Weakness (35 U.S.C. § 102):** High risk of anticipation if interpreted broadly as standard NLP extraction followed by LLM review.
* **Obviousness Weakness (35 U.S.C. § 103):** Obvious to combine text extraction with LLM verification without narrowing constraints.
* **Recommendation:** **Do NOT file Scope A alone; too vulnerable to rejection under 101/102/103.**

---

### Claim Scope B (Medium Architectural Claim)
> *A neurosymbolic system for narrative continuity verification comprising: an extraction engine that maps narrative units to temporal state events constrained to a predefined closed semantic vocabulary for physical attributes; an append-only temporal database storing said state events ordered by entity identifier, attribute, and temporal sequence; an analytical engine executing SQL analytical window functions over said database to identify candidate conflicting state transitions without invoking a generative language model; and an investigation agent communicating via a structured tool protocol with said database, bounded by a maximum tool-call quota, to adjudicate candidate conflicts into a closed verdict taxonomy citing verbatim textual evidence.*

* **Supporting Implementation:** [`backend/pipeline/state_extraction.py`](file:///home/adhyan/Desktop/StoryTrace/backend/pipeline/state_extraction.py), [`backend/candidate_detection/detector.py`](file:///home/adhyan/Desktop/StoryTrace/backend/candidate_detection/detector.py), [`backend/agent/investigator.py`](file:///home/adhyan/Desktop/StoryTrace/backend/agent/investigator.py).
* **Prior Art Overlap:** No single reference discloses the combination of closed-vocabulary state extraction, SQL window candidate detection (`lagInFrame`), and bounded agentic adjudication.
* **Novelty Weakness (35 U.S.C. § 102):** Low.
* **Obviousness Weakness (35 U.S.C. § 103):** Moderate. An examiner may argue that using window functions over a database is standard database engineering. The rebuttal is that the closed-vocabulary extraction schema is specifically engineered to make exact-match window queries functional on creative narrative text.
* **Recommendation:** **Preferred primary independent claim for commercial utility and defensibility.**

---

### Claim Scope C (Narrow / Mechanism-Specific Independent Claim)
> *A system for verifiable narrative continuity verification comprising:*
> 1. *A segmentation parser segmenting screenplay text into `NarrativeUnit` records with temporal sequence indices $\text{seq}_i \in \mathbb{N}$ and physical page offsets;*
> 2. *An extraction module utilizing a large language model with strict JSON grammar schema enforcement to generate `EntityStateEvent` tuples $(e, a, v, \text{seq}_i, \text{excerpt})$, wherein values for possession attributes are strictly constrained to $\Sigma_{\text{possession}} = \{\text{held}, \text{acquired}, \text{lost}\}$ and injury attributes to $\Sigma_{\text{injury}} = \{\text{injured}, \text{healed}, \text{dead}\}$;*
> 3. *An append-only ClickHouse database persisting said tuples into a MergeTree engine ordered by `(entity_id, attribute, sequence_number)`;*
> 4. *A deterministic candidate detector executing a single SQL query utilizing `lagInFrame(value, 1)` partitioned by `(entity_id, attribute)` to identify invalid consecutive transitions with zero runtime language model inference calls;*
> 5. *A Model Context Protocol (MCP) server exposing `get_entity_timeline`, `get_unit_text`, `get_state_at_unit`, and `find_attribute_changes` tools over a local standard input/output (stdio) transport;*
> 6. *A ReAct investigation agent constrained to a maximum bound of $k \le 6$ tool invocations, wherein malformed tool calls are reflected as observations to enable parameter self-correction, producing an immutable `InvestigationVerdict` classified into `verified`, `resolved`, `uncertain`, or `intentional` with verbatim supporting text citations.*

* **Supporting Implementation:** Shipped 1:1 in StoryTrace repository (`backend/` directory).
* **Prior Art Overlap:** Negligible. Fully distinctive in its specific combination and concrete implementation constraints.
* **Novelty Weakness (35 U.S.C. § 102):** Very Low.
* **Obviousness Weakness (35 U.S.C. § 103):** Very Low. Provides concrete technical synergy across storage, query optimization, and bounded agentic reasoning.
* **Recommendation:** **Strongest fall-back position to guarantee allowable subject matter during patent prosecution.**

---

## 3. Narrowest Defensible Technical Claim

The narrowest technically meaningful claim that completely captures the inventive core is:

> **The integration of closed-vocabulary physical state extraction with OLAP temporal window anomaly detection (`lagInFrame`) and a bounded MCP-interfaced ReAct investigation agent that grounds verdicts in immutable, sequence-indexed verbatim database records.**
