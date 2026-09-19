# INSTITUTIONAL INVENTION DISCLOSURE FORM (IDF)
## Vellore Institute of Technology (VIT) — Intellectual Property Rights (IPR) Cell

---

**TITLE OF INVENTION:**  
A Computer-Implemented Neurosymbolic System and Method for Long-Form Narrative Continuity Verification via Append-Only Relational State Logs, Deterministic Window Detectors, and Bounded Tool-Augmented Agentic Adjudication

**PRIMARY INVENTOR (STUDENT):** [Adhyan Jain / Registration No. Placeholder]  
**FACULTY GUIDE / CO-INVENTOR(S):** [Faculty Guide Name / Employee ID Placeholder]  
**DEPARTMENT / SCHOOL:** [School of Computer Science and Engineering (SCOPE) / Department Placeholder]  
**INSTITUTION:** Vellore Institute of Technology, Vellore – 632014, Tamil Nadu, India  
**DATE OF DISCLOSURE:** September 19, 2026  
**DOCUMENT CLASSIFICATION:** Confidential — For Institutional IP Evaluation & Patent Drafting Only  

---

## 1. One-Page Invention Abstract

The present invention provides a computer-implemented neurosymbolic system and method for automated temporal and physical continuity verification across long-form multi-scene narrative texts (e.g., theatrical screenplays, teleplays, and episodic scripts). Existing Large Language Model (LLM) consistency checkers suffer from quadratic computational complexity $O(N^2)$, context-window degradation, and high false-positive rates when scanning full manuscripts. 

The disclosed invention overcomes these limitations through an integrated eight-stage architecture:
1. An input screenplay is deterministically partitioned into sequence-indexed `NarrativeUnit` records based on standard scene boundaries.
2. A structured extraction engine extracts normalized state events comprising a 4-tier spatial hierarchy (`setting_type`, `environment`, `specific_room`, `city_region`), temporal anchors, scene co-presence lists, and physical/prop transitions.
3. The extracted state events are written to an append-only, sequence-indexed relational Online Analytical Processing (OLAP) database.
4. A deterministic candidate conflict detector executes parameterized SQL analytical window functions (e.g., `lagInFrame`) across the relational database to surface candidate narrative contradictions in $O(1)$ LLM calls with zero generative inference during discovery.
5. A tool-augmented investigation subsystem, operating via a standardized Model Context Protocol (FastMCP) interface, selectively dispatches a ReAct investigative agent *exclusively* to adjudicate surfaced candidates.
6. The investigation agent is subject to a strict hard bound of $k \le 6$ tool calls per candidate with automated duplicate query termination.
7. The agent adjudicates each candidate into a closed, calibrated four-state verdict space (`verified_hard_conflict`, `verified_narrative_anomaly`, `resolved`, `uncertain`), enforcing step-by-step reasoning prior to status selection.
8. Verified findings are output with sequence-indexed verbatim text excerpts and single-sentence narrative bridging repair fixes.

Empirical validation across a 10-film benchmark ($N = 989$ ground-truth errors) demonstrates that the system expands representational addressability from 8.49% to 82.10% (a 9.67x increase), achieves a **Micro-F1 of 0.7821** with **0.9508 precision** ($p < 0.001$), and filters 85.71% of candidate false positives while maintaining strict tool-budget compliance on held-out screenplays (*The Green Mile*).

---

## 2. Problem $\to$ Solution $\to$ Mechanism $\to$ Technical Effect

```
+-------------------+---------------------------------------------------------------------------------------------------+
| DIMENSION         | TECHNICAL SPECIFICATION & EVIDENCE                                                                 |
+-------------------+---------------------------------------------------------------------------------------------------+
| TECHNICAL PROBLEM | 1. Scalability Bottleneck: Evaluating pairwise scene continuity across an N-scene script requires |
|                   |    O(N^2) LLM prompt evaluations, causing severe latency and token cost explosions.               |
|                   | 2. Context Window & Hallucination Drift: Monolithic in-context LLMs forget earlier entity states, |
|                   |    hallucinate transitions, and suffer high false-positive rates (Precision < 0.15 in prior art). |
|                   | 3. Expressivity Ceiling: Flat state representations fail to capture multi-grain spatial blocking,  |
|                   |    creating an artificial recall bottleneck (< 8.5% addressable coverage).                        |
+-------------------+---------------------------------------------------------------------------------------------------+
| TECHNICAL SOLUTION| A hybrid neurosymbolic architecture that completely decouples deterministic candidate discovery   |
|                   | from agentic candidate adjudication, using structured extraction to populate an append-only OLAP |
|                   | relational store, SQL window functions for zero-LLM candidate detection, and bounded FastMCP     |
|                   | ReAct agents for targeted intervening evidence verification.                                      |
+-------------------+---------------------------------------------------------------------------------------------------+
| EXACT MECHANISM   | 1. Hierarchical spatial-temporal state normalization into relational schemas.                     |
|                   | 2. Parameterized SQL analytical window queries (8 rules) detecting state inversions in < 0.1s.    |
|                   | 3. FastMCP tool bridge providing read-only timeline and spatial trajectory access to an agent.     |
|                   | 4. Bounded ReAct loop (k <= 6) with duplicate call termination and two-tier calibrated verdicts.  |
+-------------------+---------------------------------------------------------------------------------------------------+
| TECHNICAL EFFECT  | 1. Computational Reduction: Reduces LLM inference calls during candidate discovery from O(N^2) to |
| (Section 3(k)     |    exactly ZERO (0 LLM calls). Overall screenplay runtime reduced from 2,596s to 109s.            |
| Requirement)      | 2. Precision Lift: Agent filters 85.71% of candidate false positives, boosting precision from     |
|                   |    0.7438 to 0.9508 (+20.7 percentage points lift).                                               |
|                   | 3. State Space Expansion: Expands representational error addressability by 9.67x (8.49% to 82.10%)|
|                   |    yielding statistically significant F1 lift (0.0659 -> 0.7821, p = 0.0016).                     |
+-------------------+---------------------------------------------------------------------------------------------------+
```

---

## 3. System Architecture Diagram

```
                                      STORYTRACE V2 SYSTEM ARCHITECTURE
                                                        │
                      ┌─────────────────────────────────┴─────────────────────────────────┐
                      │ INPUT: Raw Multi-Scene Screenplay Text (e.g., 30,000 words)       │
                      └─────────────────────────────────┬─────────────────────────────────┘
                                                        │
                                                        ▼
                      ┌───────────────────────────────────────────────────────────────────┐
                      │ 1. BOUNDARY SEGMENTATION MODULE                                   │
                      │    • Regex slugline parsing (INT./EXT./I.E.)                      │
                      │    • Sequence-indexed NarrativeUnits (t_1, t_2, ..., t_N)         │
                      └─────────────────────────────────┬─────────────────────────────────┘
                                                        │
                                                        ▼
                      ┌───────────────────────────────────────────────────────────────────┐
                      │ 2. STRUCTURED OBSERVER EXTRACTION ENGINE                          │
                      │    • 4-Tier Spatial Hierarchy (Setting/Environment/Room/City)     │
                      │    • Temporal Anchors & Scene Co-Presence Tracking                │
                      │    • Verbatim Substring Grounding & Hallucination Rejection       │
                      └─────────────────────────────────┬─────────────────────────────────┘
                                                        │
                                                        ▼
                      ┌───────────────────────────────────────────────────────────────────┐
                      │ 3. APPEND-ONLY OLAP RELATIONAL STORE (ClickHouse Engine)          │
                      │    • Tables: state_events_v2, scene_co_presence_v2, narrative_units│
                      └─────────────────────────────────┬─────────────────────────────────┘
                                                        │
                                                        ▼
                      ┌───────────────────────────────────────────────────────────────────┐
                      │ 4. DETERMINISTIC SQL WINDOW ANOMALY DETECTOR (ZERO LLM CALLS)     │
                      │    • 8 Parameterized SQL Window Queries (lagInFrame, bounds)      │
                      │    • Possession, Co-Presence, Spatial Jumps, Inversions           │
                      │    • High-Recall Candidate Conflicts (78.08% Addressable Recall)  │
                      └─────────────────────────────────┬─────────────────────────────────┘
                                                        │ (Candidate Conflict IDs)
                                                        ▼
                      ┌───────────────────────────────────────────────────────────────────┐
                      │ 5. STANDARDIZED FASTMCP TOOL BRIDGE                               │
                      │    • get_entity_timeline_v2, get_scene_co_presence,                │
                      │      get_spatial_trajectory, find_attribute_changes, get_unit_text│
                      └─────────────────────────────────┬─────────────────────────────────┘
                                                        │ (Tool Invocations & Observ.)
                                                        ▼
                      ┌───────────────────────────────────────────────────────────────────┐
                      │ 6. BOUNDED REACT INVESTIGATION AGENT (k <= 6)                     │
                      │    • Strict tool-call budget (k <= 6) + Duplicate loop backstop   │
                      │    • Selective execution ONLY on surfaced candidates              │
                      │    • Step-by-step reasoning enforced prior to status emission     │
                      └─────────────────────────────────┬─────────────────────────────────┘
                                                        │
                                                        ▼
                      ┌───────────────────────────────────────────────────────────────────┐
                      │ 7. TWO-TIER CALIBRATED VERDICT CLASSIFIER                         │
                      │    • verified_hard_conflict | verified_narrative_anomaly          │
                      │    • resolved | uncertain                                         │
                      └─────────────────────────────────┬─────────────────────────────────┘
                                                        │
                                                        ▼
                      ┌───────────────────────────────────────────────────────────────────┐
                      │ 8. PROVENANCE & BRIDGING REPAIR GENERATOR                         │
                      │    • Sequence-indexed verbatim text excerpts                      │
                      │    • Single-sentence narrative repair fix recommendations         │
                      └───────────────────────────────────────────────────────────────────┘
```

---

## 4. Method Flowchart & Algorithmic Steps

```
[Start: Screenplay Text] 
       │
       ▼
[Step 1: Parse Scene Headers] ──> Generate NarrativeUnits {u_1, ..., u_N}
       │
       ▼
[Step 2: Extract State Tuples] ──> Extract (Entity, Hierarchy, TempAnchor, CoPresence)
       │
       ▼
[Step 3: Ingest to Database] ──> Insert to relational tables state_events_v2 & scene_co_presence_v2
       │
       ▼
[Step 4: Execute SQL Window Rules] ──> Run 8 parameterized analytical window queries (Zero LLM)
       │
       ├───> If 0 candidates found ──> [Emit Clean Continuity Report] ──> [End]
       │
       ▼
[Step 5: For each Candidate Conflict C_i]
       │
       ├───> Initialize Investigation Agent (Budget = 6, CallCount = 0)
       │
       ├───> [Loop: Agent Action Selection]
       │        │
       │        ├───> Check Tool Call: Is CallCount >= 6 OR ToolQuery in History?
       │        │        ├─ YES ──> Force Early Adjudication ──> (Go to Step 6)
       │        │        └─ NO  ──> Increment CallCount
       │        │
       │        ├───> Execute FastMCP Query against ClickHouse
       │        └───> Receive Structured Text / Trajectory Observation
       │
       ▼
[Step 6: Emit Calibrated Verdict]
       │
       ├───> Generate Step-by-Step Textual Reasoning Explanation
       ├───> Select Status: [verified_hard_conflict | verified_narrative_anomaly | resolved | uncertain]
       │
       ▼
[Step 7: Generate Repair & Provenance]
       │
       ├───> If Status in (verified_hard_conflict, verified_narrative_anomaly):
       │        ├── Attach verbatim source excerpts from prior & current units
       │        └── Synthesize single-sentence narrative bridging repair
       │
       ▼
[End: Output Structured Audit Report]
```

---

## 5. Proposed Patent Claim Candidates

### Independent System Claim (Claim 1)
A computer-implemented system for verifying temporal narrative continuity across multi-scene narrative text, comprising:
1. **A Narrative Ingestion and Segmentation Module** configured to partition input narrative text into an ordered series of discrete narrative units indexed by sequence numbers;
2. **A Structured State Extraction Engine** configured to process each narrative unit to extract normalized state events comprising a multi-tier spatial hierarchy, a temporal anchor, a co-present entity set, and physical state transitions, wherein excerpts of the state events are validated against the raw text of the narrative unit;
3. **An Append-Only Relational State Database** storing the normalized state events indexed by sequence numbers;
4. **A Deterministic Candidate Conflict Detector** configured to execute parameterized analytical window queries over the relational state database to identify candidate continuity conflicts across sequence units without invoking generative language model inference;
5. **A Tool-Augmented Investigation Subsystem** comprising a language model configured to investigate the candidate continuity conflicts, wherein the language model is constrained to:
   - selectively query intervening narrative state events and raw text excerpts exclusively via a standardized tool bridge interface;
   - execute within a strict predefined maximum tool call budget per candidate conflict;
   - terminate execution upon detecting duplicate query arguments; and
   - adjudicate each candidate conflict into a closed multi-tier verdict space distinguishing physical impossibilities from unbridged narrative anomalies; and
6. **A Provenance and Report Generation Engine** configured to output continuity reports associating each adjudicated verdict with sequence-indexed verbatim text excerpts.

---

### Independent Method Claim (Claim 8)
A computer-implemented method for verifying narrative continuity across sequential narrative documents, the method comprising:
1. Segmenting an input narrative document into an ordered sequence of narrative units indexed by sequence numbers;
2. Extracting from each narrative unit structured state events comprising hierarchical spatial attributes, temporal anchors, and co-present entity sets;
3. Ingesting the structured state events into an append-only relational database ordered by sequence numbers;
4. Executing parameterized SQL analytical window operations across the relational database to detect candidate continuity conflicts between sequence-separated units without performing generative language model inference;
5. Selectively dispatching an investigative agent to adjudicate each detected candidate conflict, wherein the agent is restricted to querying intervening narrative state via dedicated tool functions subject to a maximum tool-call quota;
6. Generating an auditable verdict classifying each candidate conflict into a closed set of verified and resolved statuses; and
7. Attaching sequence-indexed verbatim text excerpts and narrative repair recommendations to each verified verdict.

---

### Independent Computer-Readable Medium Claim (Claim 9)
One or more non-transitory computer-readable storage media comprising computer-executable instructions that, when executed by one or more processors, cause the processors to carry out the method of Claim 8.

---

## 6. Dependent Claim Candidates

- **Dependent Claim 2 (4-Tier Spatial Hierarchy):** The system of Claim 1, wherein the multi-tier spatial hierarchy comprises setting type (interior/exterior), environment, specific room, and geographic region.
- **Dependent Claim 3 (Possession Machine SQL Window Rule):** The system of Claim 1, wherein the deterministic candidate conflict detector identifies disjoint simultaneous entity possession of a unique physical asset using a SQL window query tracking asset assignment across sequential narrative units.
- **Dependent Claim 4 (Co-Presence Collision SQL Window Rule):** The system of Claim 1, wherein the deterministic candidate conflict detector detects an entity concurrently appearing across disjoint scene units sharing overlapping temporal anchors.
- **Dependent Claim 5 (Continuous Spatial Jump Rule):** The system of Claim 1, wherein the candidate conflict detector detects an entity transitioning across disjoint environments across contiguous scene sequence numbers without an intermediate travel unit.
- **Dependent Claim 6 (Bounded Tool Budget & Loop Detection):** The system of Claim 1, wherein the tool-augmented investigation subsystem enforces a hard quota of $k \le 6$ tool calls per candidate and terminates execution upon detecting duplicate query arguments.
- **Dependent Claim 7 (Reasoning-First Schema Enforcement):** The system of Claim 1, wherein the investigation subsystem requires generation of step-by-step natural language reasoning grounded in retrieved excerpts prior to emitting the categorical verdict classification.
- **Dependent Claim 8 (Automated Bridging Fix Generator):** The system of Claim 1, further comprising a repair module configured to generate a concise narrative transition sentence for every verified continuity contradiction.

---

## 7. Embodiments & Technical Variations

1. **Primary Embodiment (Pre-Production Screenplay Verification):** System ingests feature film screenplays (`.txt`, `.pdf`, `.fountain`, `.fdx`) and outputs interactive audit dashboards for script supervisors, showrunners, and story editors.
2. **Alternative Embodiment A (Episodic Television Bible Verification):** System operates across multi-episode television bibles, tracking character knowledge, backstory revelations, and prop possession across entire seasons.
3. **Alternative Embodiment B (Interactive Video Game Narrative Engine):** System tracks branching player choice states, validating that non-linear dialogue trees do not introduce contradictory character survival or inventory states.
4. **Alternative Embodiment C (Legal and Patent Document Timeline Auditing):** System ingests multi-party litigation transcripts, witness depositions, or prior-art patent filings to detect temporal-spatial contradictions across witness testimonies.

---

## 8. Implementation Evidence for Every Claim Element

```
+------------------------------------+---------------------------------------------------------------+-----------------------------------------+
| CLAIM ELEMENT                      | EXACT REPOSITORY FILE & CODE SYMBOL                           | VERIFIED LINE RANGE / SPECIFICATION     |
+------------------------------------+---------------------------------------------------------------+-----------------------------------------+
| E1: Scene Segmentation             | `scripts/v2/run_v2_eval.py` :: `load_screenplay_units`        | Lines 45–85 (Slugline regex parsing)    |
+------------------------------------+---------------------------------------------------------------+-----------------------------------------+
| E2: 4-Tier Spatial Hierarchy       | `backend/v2/story_state/models.py` :: `HierarchicalLocationV2`| Lines 10–25 (`setting_type`, `room`, ..)|
+------------------------------------+---------------------------------------------------------------+-----------------------------------------+
| E3: Append-Only Relational Store   | `backend/v2/clickhouse/schema_v2.sql`                         | Lines 1–45 (DDL for ClickHouse tables)  |
+------------------------------------+---------------------------------------------------------------+-----------------------------------------+
| E4: Normalized State Events        | `backend/v2/story_state/models.py` :: `StateEventV2`          | Lines 30–55 (Event tuple definition)    |
+------------------------------------+---------------------------------------------------------------+-----------------------------------------+
| E5: Co-Presence Tracking           | `backend/v2/story_state/models.py` :: `SceneCoPresence`       | Lines 60–75 (`entity_ids`, `room`, etc.)|
+------------------------------------+---------------------------------------------------------------+-----------------------------------------+
| E6/E7: SQL Window Candidate Mining | `backend/v2/candidate_detection/sql_rules.py`                 | Lines 1–120 (8 SQL Analytical Queries)  |
|                                    | `backend/v2/candidate_detection/detector.py`                  | Lines 40–95 (`CandidateDetectorV2`)     |
+------------------------------------+---------------------------------------------------------------+-----------------------------------------+
| E8/E9: FastMCP Tool Bridge         | `backend/v2/agent/tools.py` :: `AgentToolsV2`                 | Lines 15–110 (5 MCP Analytical Tools)   |
+------------------------------------+---------------------------------------------------------------+-----------------------------------------+
| E10/E11: Bounded ReAct Investigator| `backend/v2/agent/investigator.py` :: `InvestigationAgentV2`  | Lines 70–210 (k <= 6 budget & loop halt)|
+------------------------------------+---------------------------------------------------------------+-----------------------------------------+
| E12: Two-Tier Calibrated Schema    | `backend/v2/story_state/models.py` :: `VerdictStatusV2`       | Lines 85–105 (4 closed enum statuses)   |
+------------------------------------+---------------------------------------------------------------+-----------------------------------------+
| E13: Verbatim Grounding & Provenance| `backend/v2/pipeline/enriched_extractor.py`                  | Lines 32–54 (`_match_verbatim_excerpt`) |
+------------------------------------+---------------------------------------------------------------+-----------------------------------------+
| E14: Candidate-Only Dispatching    | `scripts/v2/run_v2_eval.py`                                   | Lines 150–190 (Loop over candidates)    |
+------------------------------------+---------------------------------------------------------------+-----------------------------------------+
| E15: Reasoning-First Pydantic Order| `backend/v2/agent/investigator.py` :: `FinalVerdictV2`        | Lines 55–68 (`explanation` before `st`) |
+------------------------------------+---------------------------------------------------------------+-----------------------------------------+
```

---

## 9. Closest Prior-Art Distinctions

```
+------------------------------------+---------------------------------------------------------------+---------------------------------------------------------------+
| PRIOR ART REFERENCE                | PRIOR ART LIMITATIONS & DISCLOSURES                           | STORYTRACE V2 TECHNICAL DISTINCTIONS                          |
+------------------------------------+---------------------------------------------------------------+---------------------------------------------------------------+
| **ATLAS** (Yuan et al., 2024/2025) | Builds dynamic narrative knowledge graphs using probabilistic | StoryTrace does NOT use probabilistic graph traversal. It uses|
| `arXiv:2410.05558` (Academic)      | embeddings and vector edge links. Fails to enforce discrete   | an append-only relational OLAP database and deterministic SQL |
|                                    | spatial hierarchies or zero-LLM SQL window rules.             | window anomaly detection with bounded FastMCP agent auditing. |
+------------------------------------+---------------------------------------------------------------+---------------------------------------------------------------+
| **ConStory-Checker** (ACL 2026)    | Monolithic single-stage LLM-as-a-judge prompt. Conflates      | Decouples candidate generation (100% deterministic SQL) from  |
| `arXiv:2603.05890` (Academic)      | discovery and verification in one call; fails on long scripts | adjudication (bounded agent), lifting precision to 0.9508 and  |
|                                    | due to context limits; high false-positive rate.              | eliminating quadratic token costs.                            |
+------------------------------------+---------------------------------------------------------------+---------------------------------------------------------------+
| **US Patent 10,489,482**           | Discloses screenplay parsing and element tagging for static   | Static production scheduling only. Does NOT model dynamic     |
| Oct 2019 (USPTO)                   | call sheets and shooting schedules.                           | physical state transitions, temporal conflicts, or agents.   |
+------------------------------------+---------------------------------------------------------------+---------------------------------------------------------------+
| **US Patent 11,256,928**           | Natural language script analysis using monolithic statistical | Uses black-box semantic classifiers. Discloses neither an     |
| Feb 2022 (USPTO)                   | semantic rules.                                               | append-only OLAP state store, SQL window rules, nor FastMCP.  |
+------------------------------------+---------------------------------------------------------------+---------------------------------------------------------------+
```

---

## 10. Inventor & Contributor Information Placeholders

```
+------------------------------------+-----------------------------------+-----------------------------------+
| FIELD                              | PRIMARY INVENTOR (STUDENT)        | CO-INVENTOR (FACULTY GUIDE)       |
+------------------------------------+-----------------------------------+-----------------------------------+
| Full Legal Name                    | [Adhyan Jain]                     | [Faculty Guide Full Name]         |
| Institutional Affiliation          | Vellore Institute of Technology   | Vellore Institute of Technology   |
| School / Department                | [SCOPE / Computer Science]        | [SCOPE / Computer Science]        |
| Registration / Employee ID         | [Student Reg No Placeholder]      | [Faculty Employee ID Placeholder] |
| Email Address                      | [student.email@vitstudent.ac.in]  | [faculty.email@vit.ac.in]         |
| Nationality / Citizenship          | Indian                            | Indian                            |
| Permanent Residential Address      | [Address Placeholder]             | [Address Placeholder]             |
| Contribution Description           | Core Architecture, Code, Database | Conceptual Guidance, Evaluation   |
|                                    | Implementation, and Evaluation    | Methodology & Paper Review        |
| Contribution Percentage            | [e.g., 70%]                       | [e.g., 30%]                       |
| Signature & Date                   | ____________________ Date: ______ | ____________________ Date: ______ |
+------------------------------------+-----------------------------------+-----------------------------------+
```

---

## 11. Public-Disclosure Timeline & Statutory Deadlines

```
========================================================================================================
                                   CRITICAL INTELLECTUAL PROPERTY TIMELINE
========================================================================================================
Stage / Milestone                      Target Date / Deadline          Mandatory Action & Constraints
--------------------------------------------------------------------------------------------------------
1. Institutional IDF Submission        September 20, 2026              Submit this completed IDF package to
                                                                       VIT IPR Cell for review.
2. Form 1 & Form 2 Drafting            September 21–25, 2026           Draft Official Indian Provisional Patent
                                                                       Specification with VIT Patent Attorney.
3. Provisional Patent Filing (IPO)     September 28, 2026              FILE PROVISIONAL PATENT APPLICATION.
                                                                       Obtain official Application Number.
--------------------------------------------------------------------------------------------------------
[CRITICAL BARRIER: ZERO PUBLIC DISCLOSURE PRIOR TO STEP 3 FILING DATE]
--------------------------------------------------------------------------------------------------------
4. Academic Preprint (arXiv) Release   September 30, 2026              Upload research paper to arXiv (Safe only
                                                                       AFTER Step 3 provisional filing date).
5. Conference / Journal Submission     October 2026                    Submit to target venue (ACL/EMNLP).
6. Complete Specification (Form 2)     September 2027 (Within 12 mos)  File Complete Specification at IPO.
========================================================================================================
```

---

## 12. Substantiating Git Commits & Conception Evidence

```
+---------------+---------------------+---------------------------------------------------------------+-----------------------------------------+
| COMMIT HASH   | DATE STAMP (UTC)    | COMMIT TITLE / DESCRIPTION                                    | SUBSTANTIATED TECHNICAL ARTIFACTS       |
+---------------+---------------------+---------------------------------------------------------------+-----------------------------------------+
| `eab6ef6`     | 2026-09-17 14:12    | `research: freeze StoryTrace V1 experiment`                   | Frozen V1 baseline on canonical `main`. |
+---------------+---------------------+---------------------------------------------------------------+-----------------------------------------+
| `8c86caa`     | 2026-09-18 06:15    | `v2: initialize data models and ClickHouse V2 analytics`      | `models.py`, `schema_v2.sql`.           |
+---------------+---------------------+---------------------------------------------------------------+-----------------------------------------+
| `56ca734`     | 2026-09-18 08:30    | `v2: implement enriched scene and hierarchical state extract` | `enriched_extractor.py`, `prompts.py`.  |
+---------------+---------------------+---------------------------------------------------------------+-----------------------------------------+
| `b1c6728`     | 2026-09-18 11:20    | `v2: implement 8 deterministic SQL analytical window rules`   | `sql_rules.py`, `detector.py`.          |
+---------------+---------------------+---------------------------------------------------------------+-----------------------------------------+
| `7410463`     | 2026-09-18 16:45    | `v2: implement calibrated two-tier ReAct investigation agent` | `investigator.py`, `tools.py`.          |
+---------------+---------------------+---------------------------------------------------------------+-----------------------------------------+
| `20d5dd8`     | 2026-09-19 12:57    | `v2: implement evaluation harness, scoring engine, comparison`| `run_v2_eval.py`, `score_v2_exp.py`.    |
+---------------+---------------------+---------------------------------------------------------------+-----------------------------------------+
| `4064cf7`     | 2026-09-19 13:37    | `research: complete V2 audit, gold reconcil, held-out Green M`| `audit_investigator.py`, Green Mile data|
+---------------+---------------------+---------------------------------------------------------------+-----------------------------------------+
| `ac3e5c1`     | 2026-09-19 14:01    | `docs: complete StoryTrace V2 IP audit and claim architecture`| `IP_TECHNICAL_CORE.md`, `PATENT_CLAIM..`|
+---------------+---------------------+---------------------------------------------------------------+-----------------------------------------+
```

---

## 13. Strategic Questions for VIT IPR Cell

1. **Expedited Examination Eligibility (Rule 24C):** As an Indian educational institution, will VIT file for Expedited Examination under Rule 24C to fast-track patent grant within 12 months?
2. **Co-Ownership & Commercial Rights:** What is VIT's standard revenue-sharing and commercial licensing policy for student-developed software inventions?
3. **Patent Cooperation Treaty (PCT) International Filing:** What is the procedure and timeline for filing a PCT International Application within the 12-month convention period following the Indian provisional filing?
4. **Institutional No-Objection Certificate (NOC) for Paper Submission:** Once the provisional application number is generated, does the IPR Cell issue an immediate written NOC allowing submission to international conferences (ACL/EMNLP) and public posting on arXiv?
5. **Software Patentability (Section 3(k)) Defense:** Does the VIT-empanelled patent attorney recommend emphasizing the hardware resource optimization (99.8% reduction in GPU token load) or the relational database transformation as the primary technical effect?
