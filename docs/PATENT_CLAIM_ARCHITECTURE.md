# StoryTrace V2: Patent Claim Architecture & Strategy

**Project:** StoryTrace V2 Patent Application Drafting Framework  
**Date:** September 19, 2026  
**Auditor:** Antigravity IP & Patent Architecture Group  
**Disclaimer:** *This document provides technical claim architecture and structural analysis for patent drafting. It does not constitute formal legal counsel.*

---

## 1. Terms Explicitly Excluded from Standalone Novelty Claims

To ensure high patent examination robustness across USPTO, EPO, and Indian Patent Office (IPO), the following generic concepts and buzzwords **must not** be claimed as standalone inventive elements:
- ❌ "Large Language Model (LLM)"
- ❌ "Retrieval-Augmented Generation (RAG)"
- ❌ "Model Context Protocol (MCP)"
- ❌ "ClickHouse Database"
- ❌ "Structured Query Language (SQL)"
- ❌ "ReAct Prompting"
- ❌ "Screenplay Parsing via Regular Expressions"

The patent claims must focus strictly on the **specific data structures, transformation steps, relational window operations, and bounded tool-adjudication control loops**.

---

## 2. System Claim Architecture

### Claim 1 (Broad Independent System Claim)
A computer-implemented system for verifying temporal narrative continuity across sequential text units, comprising:
1. **A Narrative Segmentation Subsystem** configured to partition input narrative text into an ordered sequence of discrete narrative units indexed by temporal sequence numbers;
2. **A Structured State Extraction Engine** configured to parse each narrative unit to extract normalized state events comprising a multi-tier spatial hierarchy, a temporal anchor, a set of co-present entities, and state transition tuples;
3. **An Append-Only Relational State Store** storing the normalized state events indexed by sequence numbers;
4. **A Deterministic Candidate Conflict Detector** configured to execute parameterized analytical window queries over the state store to identify candidate narrative contradictions across sequence units without generative language model inference;
5. **A Tool-Augmented Investigation Subsystem** comprising a language model configured to investigate the candidate contradictions, wherein the language model is constrained to:
   - selectively retrieve intervening state events and verbatim text excerpts exclusively via a standardized tool interface;
   - execute within a predefined maximum tool call budget per candidate; and
   - classify each candidate into a closed multi-tier verdict space distinguishing physical impossibilities from unbridged narrative anomalies; and
6. **A Provenance Generation Engine** outputting verified continuity reports linking each classified verdict to sequence-indexed verbatim text excerpts.

---

### Dependent System Claims (Optional Narrowing Elements)

- **Claim 2 (Hierarchical Spatial Structure):** The system of Claim 1, wherein the multi-tier spatial hierarchy comprises setting type (interior/exterior), environment, specific room, and geographic region.
- **Claim 3 (Possession Machine Rule):** The system of Claim 1, wherein the deterministic candidate conflict detector identifies disjoint simultaneous entity possession of unique physical assets using analytical window queries.
- **Claim 4 (Co-Presence Collision Rule):** The system of Claim 1, wherein the deterministic candidate conflict detector detects an entity concurrently appearing across disjoint scene units sharing overlapping temporal anchors.
- **Claim 5 (Bounded Tool Budget & Loop Detection):** The system of Claim 1, wherein the tool-augmented investigation subsystem enforces a hard bound of $k \le 6$ tool calls per candidate and terminates execution upon detecting duplicate query arguments.
- **Claim 6 (Reasoning-First Schema Enforcement):** The system of Claim 1, wherein the investigation subsystem requires generation of step-by-step natural language reasoning grounded in retrieved excerpts prior to emitting the categorical verdict classification.
- **Claim 7 (Automated Bridging Fix Generation):** The system of Claim 1, further comprising a repair module configured to generate a concise narrative transition sentence for every verified continuity contradiction.

---

## 3. Method Claim Architecture (Independent Claim)

### Claim 8 (Independent Method Claim)
A computer-implemented method for verifying narrative continuity across sequential text documents, the method comprising:
1. Segmenting a narrative screenplay into an ordered series of narrative units;
2. Extracting from each narrative unit structured state events comprising hierarchical spatial attributes, temporal anchors, and co-present entity sets;
3. Writing the structured state events to a relational database table ordered by sequence numbers;
4. Executing analytical window operations across the relational database table to detect candidate continuity conflicts between sequence-separated units without performing generative inference;
5. Dispatching a bounded investigative agent to adjudicate each detected candidate conflict, wherein the agent is restricted to querying intervening narrative context via dedicated tool functions subject to a maximum call quota;
6. Emitting an auditable continuity verdict classifying the candidate into a closed set of verified and resolved statuses; and
7. Attaching sequence-indexed verbatim text excerpts to each verified verdict.

---

## 4. Computer-Readable Medium Claim (Independent Claim)

### Claim 9 (Independent CRM Claim)
One or more non-transitory computer-readable storage media comprising computer-executable instructions that, when executed by one or more processors, cause the processors to perform the method of Claim 8.

---

## 5. Prior-Art Collision & Risk Analysis

```
+---------------------+-------------------------------+-----------------------------------+------------------------------------+
| CLAIM LEVEL         | LIKELY PRIOR-ART OBJECTION    | TECHNICAL COUNTER-ARGUMENT        | RECOMMENDED CLAIM ADJUSTMENT       |
+---------------------+-------------------------------+-----------------------------------+------------------------------------+
| Broad System        | 35 U.S.C. 101 / Section 3(k)  | System provides specific data     | Ensure claim explicitly recites    |
| (Claim 1)           | "Abstract mental process of   | structures (4-tier hierarchy) and | relational database queries and    |
|                     | screenplay review"            | deterministic relational queries. | bounded tool execution limits.     |
+---------------------+-------------------------------+-----------------------------------+------------------------------------+
| Candidate Detector  | Anticipation by standard SQL  | Standard SQL is general; here it  | Tie window queries specifically to |
| (Claims 3-4)        | or rule engines               | is combined with narrative state. | temporal narrative sequence bounds.|
+---------------------+-------------------------------+-----------------------------------+------------------------------------+
| Investigation Agent | Obviousness over general RAG  | General RAG is unbounded search;  | Emphasize selective execution on   |
| (Claims 5-6)        | / ReAct architectures         | here it acts *only* on candidates.| candidate subset + hard k<=6 bound.|
+---------------------+-------------------------------+-----------------------------------+------------------------------------+
```
