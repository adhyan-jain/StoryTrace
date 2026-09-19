# StoryTrace V2: Inventive Core & Technical Novelty Analysis

**Project:** StoryTrace V2 Patent & Novelty Assessment  
**Date:** September 19, 2026  
**Auditor:** Antigravity IP Strategy Group  

---

## 1. Multi-Level Abstraction Evaluation

```
+---------+-----------------------------------+---------------------------------------------+---------------------------------+
| LEVEL   | DESCRIPTION                       | PRIOR ART STATUS                            | PATENTABILITY DEFICIENCY        |
+---------+-----------------------------------+---------------------------------------------+---------------------------------+
| Level 1 | Individual Components             | KNOWN (LLM, SQL, ClickHouse, MCP, ReAct)    | Obvious / Non-novel             |
+---------+-----------------------------------+---------------------------------------------+---------------------------------+
| Level 2 | Pairwise Combinations             | KNOWN (RAG + Agent, LLM + SQL)              | Conventional software patterns  |
+---------+-----------------------------------+---------------------------------------------+---------------------------------+
| Level 3 | Linear Pipeline                   | PARTIALLY DISCLOSED (Extract->Store->Search)| Broad / Likely Anticipated      |
+---------+-----------------------------------+---------------------------------------------+---------------------------------+
| Level 4 | Operational Interaction           | POTENTIALLY DISTINCTIVE                     | Strong defensibility            |
+---------+-----------------------------------+---------------------------------------------+---------------------------------+
| Level 5 | Specific Technical Mechanism      | **DISTINCTIVE & EMPIRICALLY SUPPORTED**     | **HIGHLY DEFENSIBLE CORE**      |
+---------+-----------------------------------+---------------------------------------------+---------------------------------+
```

---

## 2. Detailed Abstraction Analysis

### Level 1 & 2 (Individual Components & Pairwise Patterns):
- Claiming "an LLM that checks screenplays", "using an MCP server for agents", or "storing screenplay states in ClickHouse" is **wholly invalid**. These are generic tools disclosed across hundreds of prior publications and open-source packages.

### Level 3 (Generic Pipeline):
- "Extracting states from a screenplay, storing them in a database, detecting conflicts, and asking an agent to review them" is too broad and risks rejection under prior-art narrative graph papers (ATLAS, E²RAG) and US 11,256,928.

### Level 4 & 5 (The Defensible Technical Inventive Core):
The genuine technical invention consists of the **tight operational coupling between a deterministic relational anomaly generator and a tool-bounded evidence investigator**:

1. **Structured Temporal-Spatial State Ingestion:** Extracting discrete 4-tier spatial hierarchy (`setting_type`, `environment`, `specific_room`, `city_region`), temporal anchors, and co-presence tuples into an append-only OLAP relational table.
2. **Zero-LLM Deterministic Candidate Detection:** Executing parameterized SQL window functions (`lagInFrame`, temporal bounds) directly over the relational state to surface candidate anomalies in $O(1)$ LLM calls (eliminating quadratic LLM comparison costs).
3. **Selective Bounded Investigation:** The LLM agent is **never invoked over the full script**; instead, it is selectively dispatched *only* to investigate deterministic candidate conflicts via a FastMCP tool bridge with a hard call quota ($k \le 6$), loop detection, and a calibrated two-tier verdict schema.

---

## 3. Empirical Support for the Inventive Core

The experimental ablation across 10 benchmark films directly proves the causal necessity of this Level 5 mechanism:
- **Without Hierarchical State (V1 Condition A):** System suffered an $8.49\%$ recall ceiling ($0.0659$ F1).
- **Without Deterministic SQL Filter (V1 Condition C):** Unconstrained LLM extraction resulted in low precision ($0.1481$) and unverified hallucinations.
- **Without Calibrated Investigation Agent (V1 Condition B):** Surfacing raw candidates directly caused a precision collapse ($0.2372$).
- **With the Synergistic Inventive Core (V2 Pipeline):** System achieves **$0.9508$ Precision**, **$0.7821$ F1**, and **$80.91\%$ Addressable Recall** with $p < 0.001$ statistical significance.
