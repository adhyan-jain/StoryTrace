# Patent Readiness Audit: StoryTrace System & Method

**Document Type:** Technical Invention Audit & IP Readiness Assessment  
**Project:** StoryTrace (Multi-Document Narrative Continuity Verification Engine)  
**Author:** Adhyan Jain  
**Affiliation:** School of Computer Science & Engineering, Vellore Institute of Technology (VIT Vellore)  
**Date:** September 18, 2026  
**Disclaimer:** *This document provides a technical and procedural audit of the software repository for patent filing readiness. It does NOT constitute legal advice or an official patentability opinion. Patent grant determinations require formal evaluation by registered patent attorneys and patent examiners.*

---

## 1. Precise Invention Definition & Technical Decomposition

The technical invention implemented in StoryTrace is **NOT** generic "LLM screenplay analysis" or a standard "narrative knowledge graph." Rather, the invention is a **neurosymbolic, multi-stage pipeline and data processing architecture that decouples deterministic zero-inference candidate contradiction generation from bounded, evidence-grounded agentic adjudication via an append-only temporal state store**.

Below is the technical decomposition of the 12 core system elements:

```
+--------------------------------------------------------------------------------------------------+
|                                    STORYTRACE SYSTEM PIPELINE                                    |
+--------------------------------------------------------------------------------------------------+
|                                                                                                  |
|  [Narrative Manuscript D]                                                                        |
|            │                                                                                     |
|            ▼                                                                                     |
|  (1) NarrativeUnit Segmentation (Page Boundaries, Scene Headers INT/EXT, Sequence Numbering)     |
|            │                                                                                     |
|            ▼                                                                                     |
|  (2) Canonical Entity Resolution (Fuzzy Alias Linking, Project-Scoped Scoping, Persistent IDs)   |
|            │                                                                                     |
|            ▼                                                                                     |
|  (3) Controlled-Grammar State Extraction (Pydantic Schema: Possession, Injury, Location, Cloth)  |
|            │                                                                                     |
|            ▼                                                                                     |
|  (4) Append-Only Temporal State Engine (ClickHouse MergeTree ordered by entity, attr, seq)       |
|            │                                                                                     |
|            ▼                                                                                     |
|  (5) Deterministic SQL Window Detection (lagInFrame Analytic Query: Zero Generative Model Calls) |
|            │                                                                                     |
|            ▼  [Surfaced Candidate Anomaly Tuples: (e_prior, e_current)]                          |
|  (6) Targeted Tool-Based Evidence Retrieval (MCP ClickHouse Bridge: Specific Time Windows)       |
|            │                                                                                     |
|            ▼                                                                                     |
|  (7) Bounded ReAct Investigation Agent (Max 6 Invocations, Resilient Error Observation Feedback) |
|            │                                                                                     |
|            ▼                                                                                     |
|  (8) Closed Four-Way Classification (VERIFIED / RESOLVED / UNCERTAIN / INTENTIONAL)              |
|            │                                                                                     |
|            ▼                                                                                     |
|  (9) Auditable Evidence Dossier (Verbatim unit_id Citations, Provenance Traces, Confidence)      |
+--------------------------------------------------------------------------------------------------+
```

### Detailed Component Analysis

| # | Technical Element | What It Does Technically | Why It Exists / Problem Solved | Conventional vs. Potentially Distinctive |
| :--- | :--- | :--- | :--- | :--- |
| **1** | **Temporal Narrative-State Representation** | Segments text into ordered `NarrativeUnit` tuples $(u_i, \text{seq}_i, \text{type}, \mathcal{T}_i)$ preserving scene headers (`INT./EXT.`) and physical page ranges (`start_page`, `end_page`). | Establishes a discrete temporal coordinate system independent of volatile page counts across script revisions. | **Conventional**: Text chunking and scene header regex parsing. |
| **2** | **Canonical Entity Resolution** | Resolves character/prop variants to persistent UUIDs scoped per project (`backend/story_state/models.py`), utilizing alias dictionaries and fuzzy matching. | Prevents split-brain state tracking where "BOB", "ROBERT", and "HIM" are tracked as independent entities. | **Conventional**: Entity linking and coreference resolution. |
| **3** | **Provenance-Linked State Assertions** | Maps each state fact $e$ to a tuple `(entity_id, attribute, value, sequence_number, raw_excerpt)`. Requires substring containment of `raw_excerpt` in $u_i$. | Eliminates ungrounded hallucinations during extraction; guarantees every asserted fact has an audit trail. | **Potentially Distinctive in Combination**: Enforcing strict character offset containment before database insertion. |
| **4** | **Controlled-Vocabulary State Semantics** | Restricts dynamic state domains to closed grammars: $\Sigma_{\text{possession}} \in \{\text{held}, \text{acquired}, \text{lost}\}$, $\Sigma_{\text{injury}} \in \{\text{injured}, \text{healed}, \text{dead}\}$. | Enables deterministic state transition validation without fuzzy embeddings or semantic ambiguity. | **Potentially Distinctive**: Sacrificing open-ended expressiveness specifically to unlock exact-match SQL joins. |
| **5** | **Deterministic SQL Candidate Detection** | Executes analytical window queries (`lagInFrame`) over ClickHouse partitions `(entity_id, attribute)` ordered by `sequence_number ASC`. | Eliminates expensive and noisy LLM passes over the entire screenplay to find potential conflict locations. | **Potentially Distinctive**: Using OLAP SQL window functions directly on narrative state logs for $O(1)$ inference-cost anomaly discovery. |
| **6** | **Append-Only Temporal State Store** | Persists all state events in an immutable MergeTree engine partitioned by `story_universe_id`. No mutating in-place updates. | Preserves the complete historical trajectory of an entity; enables retrospection across arbitrary scene spans. | **Conventional**: Event sourcing / time-series database design applied to NLP. |
| **7** | **Targeted Model Context Protocol (MCP) Bridge** | Exposes 4 granular tools to the agent: `get_entity_timeline`, `get_unit_text`, `get_state_at_unit`, `find_attribute_changes`. | Restricts model context ingestion strictly to the relevant temporal window rather than feeding whole books. | **Potentially Distinctive in Combination**: MCP stdio interface connecting ReAct agent to OLAP temporal store. |
| **8** | **Bounded ReAct Investigation Agent** | Executes a multi-step reasoning loop (`Thought` $\to$ `Action` $\to$ `Observation`) capped at a hard backstop ($k \le 6$). Bad tool calls are fed back as observations without crashing. | Prevents runaway agent loops and context blowout while allowing self-correction of parameter hallucinations. | **Potentially Distinctive in Combination**: Resilient error feedback loop bounded by a strict resource quota. |
| **9** | **Closed 4-Way Adjudication Classification** | Classifies candidates strictly into `verified` (true error), `resolved` (justified off-screen or in intervening scene), `uncertain` (ambiguous), `intentional` (flashback/dream). | High-precision triage for professional script supervisors who need actionable, auditable defect reports. | **Conventional**: Multi-class classification, but distinctive in its semantic grounding criteria. |
| **10** | **Verbatim Evidence Provenance Dossier** | Compiles an autopsy dossier containing exact `unit_id`, surrounding text, confidence score ($0.0 - 1.0$), and the tool trace. | Provides human script supervisors with an instant, verifiable audit trail without requiring them to re-read the script. | **Potentially Distinctive**: Fully auditable trace provenance tied to immutable database sequence numbers. |
| **11** | **Multi-Version Project Diffs** | Groups uploads under `project_id` and diffs conflicts across versions $V_1 \to V_2$ joined on `(entity_id, attribute)` rather than upload IDs. | Allows writers to verify whether a script rewrite resolved a previously flagged continuity error. | **Conventional**: Software diffing applied to narrative entities. |
| **12** | **Deterministic Failure Backstop** | Reverts to `uncertain` with confidence `0.0` if the agent exhausts tool calls or encounters an unrecoverable exception. | Enforces a fail-safe precision guarantee over ungrounded recall. | **Conventional**: Defensive error-handling design. |

---

## 2. Technical Depth & Repository Artifact Audit

We audited the repository implementation against 35 U.S.C. § 112 (Written Description and Enablement Requirements):

| Patent Disclosure Requirement | Status in Codebase | Source File Reference |
| :--- | :---: | :--- |
| **1. Data Structure Definitions** | ✅ **Complete** | [`backend/ingestion/models.py`](file:///home/adhyan/Desktop/StoryTrace/backend/ingestion/models.py), [`backend/story_state/models.py`](file:///home/adhyan/Desktop/StoryTrace/backend/story_state/models.py) |
| **2. State Extraction Schemas** | ✅ **Complete** | [`backend/pipeline/state_extraction.py`](file:///home/adhyan/Desktop/StoryTrace/backend/pipeline/state_extraction.py) (`_POSSESSION_VALUES`, `_INJURY_VALUES`) |
| **3. Database Schema (DDL)** | ✅ **Complete** | [`backend/clickhouse/schema.sql`](file:///home/adhyan/Desktop/StoryTrace/backend/clickhouse/schema.sql) (`state_events`, `narrative_units`, `story_universes`) |
| **4. Candidate Detection Algorithm** | ✅ **Complete** | [`backend/candidate_detection/detector.py`](file:///home/adhyan/Desktop/StoryTrace/backend/candidate_detection/detector.py) (`find_candidate_conflicts_sql`) |
| **5. Investigation Workflow & Agent** | ✅ **Complete** | [`backend/agent/investigator.py`](file:///home/adhyan/Desktop/StoryTrace/backend/agent/investigator.py) (`InvestigationAgent._run_loop`) |
| **6. Tool Protocol (MCP Server)** | ✅ **Complete** | [`backend/mcp/server.py`](file:///home/adhyan/Desktop/StoryTrace/backend/mcp/server.py) (FastMCP registered tools) |
| **7. Reproducible Evaluation Pipeline**| ✅ **Complete** | [`scripts/eval/run_final_research_experiment.py`](file:///home/adhyan/Desktop/StoryTrace/scripts/eval/run_final_research_experiment.py), [`scripts/eval/score_final_experiment.py`](file:///home/adhyan/Desktop/StoryTrace/scripts/eval/score_final_experiment.py) |
| **8. System Architecture Diagrams** | ⚠️ **Needs Polishing**| Textual diagrams exist in `docs/architecture.md`; formal patent-style block flowcharts should be prepared. |
| **9. Formal Pseudocode Listings** | ⚠️ **Needs Expansion** | SQL queries and Python code exist; concise LaTeX/algorithmic pseudocode for the patent specification is recommended. |

---

## 3. Institutional & Procedural IP Strategy (VIT Vellore Context)

### 3.1 University Invention Assignment & IP Policy
1. **Ownership Determination (Threshold Requirement)**:
   - Under the Intellectual Property Policy of Vellore Institute of Technology (VIT Vellore), intellectual property created by enrolled students using university facilities, compute resources, faculty supervision, or capstone project frameworks may be subject to institutional assignment or joint ownership.
   - **Action Item**: Before filing any provisional application or publicly publishing code, submit the formal invention disclosure to the **VIT Center for Technology Business Incubation (TBI) / Intellectual Property Rights (IPR) Cell**.

### 3.2 Statutory Public Disclosure Bar & Filing Timelines
1. **United States (USPTO)**:
   - 35 U.S.C. § 102(b)(1) provides a **1-year grace period** following the inventor's own public disclosure. If initial public commits were made in September 2026, a US Provisional Application must be filed within 12 months.
2. **India (Indian Patent Office - IPO)**:
   - Section 29–34 of the Indian Patents Act, 1970 provides very narrow exceptions (e.g., public display at notified exhibitions or communication to government authorities). Public disclosure on open GitHub repositories generally invalidates novelty in India unless an absolute priority application was filed prior to disclosure.
3. **European Patent Office (EPO)**:
   - The EPO enforces a strict **absolute novelty standard** (Article 54 EPC). Any public pre-filing disclosure acts as a fatal novelty bar.

### 3.3 Subject Matter Eligibility Risks (Alice / 35 U.S.C. § 101 & Section 3(k) India)
- **Alice Step 1 & 2 (USPTO)**: Abstract ideas (organizing information, logical reasoning) are ineligible unless tied to a practical technical improvement in computer functioning or a specific, non-preemptive distributed pipeline architecture.
- **Section 3(k) (India)**: Computer programs per se and mathematical/algorithmic methods are non-patentable. Claims must be drafted emphasizing technical implementation, hardware database interaction (ClickHouse OLAP MergeTree memory indexing), and automated system integration.
