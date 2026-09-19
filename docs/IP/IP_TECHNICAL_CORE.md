# StoryTrace V2: Technical Core & Dependency Chain

**Document:** Formal Reconstructed Inventive Core Specification  
**System:** StoryTrace V2 Neurosymbolic Screenplay Continuity Verification Engine  
**Date:** September 19, 2026  
**Auditor:** Antigravity IP & Technical Core Architecture Group  

---

## 1. Executive Summary & Core Definition

StoryTrace V2 is **not** a generic "AI screenplay checker." It is a **neurosymbolic multi-stage pipeline** that couples structured LLM state extraction, an append-only OLAP temporal state store, zero-LLM parameterized SQL analytical window anomaly detectors, and a tool-augmented bounded ReAct investigation agent ($k \le 6$) operating over a closed calibrated verdict space.

```
========================================================================================================================
                                         STORYTRACE V2 END-TO-END DEPENDENCY CHAIN
========================================================================================================================
[1. Screenplay Input] ──> [2. Enriched Extraction] ──> [3. OLAP State Store] ──> [4. SQL Window Candidate Gen]
                                                                                            │ (Zero LLM Calls)
                                                                                            ▼
[8. Verbatim Provenance] <── [7. Two-Tier Verdict] <── [6. Bounded ReAct Agent] <── [5. FastMCP Tool Bridge]
                                                               ($k \le 6$)
========================================================================================================================
```

---

## 2. Stage-by-Stage Technical Decomposition

### Stage 1: Screenplay Ingestion & Boundary Segmentation
- **Exact Implementation:** Regular-expression boundary parser matching standard screenplay scene headings (`INT.`, `EXT.`, `INT/EXT.`, `I/E.`).
- **Input:** Raw ASCII/UTF-8 screenplay text.
- **Output:** Ordered sequence of `NarrativeUnit` records with `sequence_number`, `title`, and `raw_text`.
- **Deterministic vs. Probabilistic:** **100% Deterministic**.
- **Dependency:** Source document input.
- **Why it exists:** Screenplays are inherently partitioned into discrete spatial-temporal units by sluglines; unsegmented text creates unbounded coreference search spaces.
- **Failure mode if removed:** Loss of discrete sequence indices ($t_1, t_2, \dots, t_N$), preventing temporal ordering and window queries.

---

### Stage 2: Enriched Observer-Role Scene Extraction
- **Exact Implementation:** [`backend/v2/pipeline/enriched_extractor.py`](file:///home/adhyan/Desktop/StoryTrace/backend/v2/pipeline/enriched_extractor.py).
- **Input:** Single `NarrativeUnit` text chunk.
- **Output:** `SceneExtractionV2` containing:
  - 4-Tier Spatial Hierarchy: `setting_type` (INT/EXT), `environment`, `specific_room`, `city_region`.
  - Temporal Anchors: `time_of_day`, `chronological_order_hint`, `time_elapsed_hint`, `flashback_indicator`.
  - Scene Co-Presence: Set of entities actively co-located in the unit.
  - State Transitions: `possession`, `physical_condition`, `clothing`, `epistemic_fact`, `relational_status`.
  - Verbatim Grounding: Substring validation against unit raw text.
- **Deterministic vs. Probabilistic:** **Structured Probabilistic (Constrained JSON schema)**.
- **Dependency:** Stage 1 (`NarrativeUnit`).
- **Why it exists:** Transforms unstructured literary prose into a structured temporal database.
- **Failure mode if removed:** System collapses to unconstrained text matching (V1 Condition D), resulting in $0.0000$ F1.

---

### Stage 3: Persistent Relational OLAP State Store
- **Exact Implementation:** ClickHouse analytical engine (`state_events_v2`, `scene_co_presence_v2`, `narrative_units`).
- **Input:** Parsed records from Stage 2.
- **Output:** Columnar, sequence-indexed, append-only relational state tables.
- **Deterministic vs. Probabilistic:** **100% Deterministic Storage**.
- **Dependency:** Stage 2 extracted state.
- **Why it exists:** Decouples state ingestion from anomaly detection, enabling low-latency analytical queries across 30,000+ words in milliseconds.
- **Failure mode if removed:** System must pass full script history into every LLM prompt, hitting context limits and severe latency degradation.

---

### Stage 4: Deterministic SQL Analytical Window Anomaly Detection
- **Exact Implementation:** [`backend/v2/candidate_detection/detector.py`](file:///home/adhyan/Desktop/StoryTrace/backend/v2/candidate_detection/detector.py) & [`sql_rules.py`](file:///home/adhyan/Desktop/StoryTrace/backend/v2/candidate_detection/sql_rules.py).
- **Input:** Database table query parameters (`story_universe_id`).
- **Output:** List of `CandidateConflictV2` records containing conflict rule, involved entities, and prior/current scene unit IDs.
- **Deterministic vs. Probabilistic:** **100% Deterministic (Zero LLM Calls)**.
- **The 8 SQL Analytical Rules:**
  1. `possession_machine`: Simultaneous possession of unique item by disjoint entities.
  2. `co_presence_collision`: Character simultaneously present in disjoint scenes.
  3. `continuous_spatial_jump`: Entity teleportation without bridging scenes under continuous time.
  4. `physical_inversion`: Permanent injury/death magically reversed without treatment beat.
  5. `clothing_swap`: Sudden unestablished costume change within continuous pacing.
  6. `epistemic_anomaly`: Character acting on secret knowledge prior to learning beat.
  7. `relational_rupture`: Unexplained status shift without dramatic transition.
  8. `chronology_inversion`: Temporal anchor contradictions violating linear script progression.
- **Dependency:** Stage 3 (ClickHouse tables).
- **Why it exists:** Filters thousands of possible narrative pairings into a high-recall candidate set ($78.08\%$ addressable recall) in $< 0.1$s without token costs.
- **Failure mode if removed:** System requires $O(N^2)$ LLM pairwise comparisons, causing quadratic cost explosion and prompt fatigue.

---

### Stage 5: Targeted FastMCP Tool Bridge
- **Exact Implementation:** [`backend/v2/agent/tools.py`](file:///home/adhyan/Desktop/StoryTrace/backend/v2/agent/tools.py) (Model Context Protocol stdio interface).
- **Input:** Tool invocation requests from the agent (`get_entity_timeline_v2`, `get_scene_co_presence`, `get_spatial_trajectory`, `find_attribute_changes`, `get_unit_text`).
- **Output:** Filtered, structured database records and verbatim text excerpts.
- **Deterministic vs. Probabilistic:** **100% Deterministic Retrieval**.
- **Dependency:** Stage 3 and Stage 4.
- **Why it exists:** Provides bounded, targeted random access to intervening narrative units rather than dumping the whole screenplay into context.
- **Failure mode if removed:** The agent cannot verify intervening narrative context (e.g., verifying if a character received paramedic care between scene 10 and 20).

---

### Stage 6: Bounded Calibrated ReAct Investigation Agent
- **Exact Implementation:** [`backend/v2/agent/investigator.py`](file:///home/adhyan/Desktop/StoryTrace/backend/v2/agent/investigator.py).
- **Input:** Single candidate conflict + FastMCP tool bridge.
- **Output:** Adjudicated verdict record with explanation and tool trace.
- **Guardrails:**
  - Strict tool call budget: **$k \le 6$ calls per candidate**.
  - Exact loop/duplicate tool-call detection.
  - Step-by-step reasoning enforced before status selection.
- **Deterministic vs. Probabilistic:** **Probabilistic Inference over Deterministic Tool Observations**.
- **Dependency:** Stage 4 candidates and Stage 5 tool bridge.
- **Why it exists:** Evaluates narrative context (flashbacks, off-screen travel, metaphor, dramatic justification) to filter candidate false positives.
- **Failure mode if removed:** System surfaces raw SQL candidates directly (Condition B), causing a drop from $0.9508$ to $0.2372$ precision.

---

### Stage 7: Two-Tier Calibrated Verdict Classification
- **Exact Implementation:** [`backend/v2/story_state/models.py`](file:///home/adhyan/Desktop/StoryTrace/backend/v2/story_state/models.py) (`VerdictStatusV2`).
- **Closed Space:**
  1. `verified_hard_conflict` (critical physical/logical impossibility).
  2. `verified_narrative_anomaly` (soft unbridged temporal/spatial jump).
  3. `resolved` (narratively justified transition).
  4. `uncertain` (insufficient textual proof).
- **Deterministic vs. Probabilistic:** **Structured Output Enum**.
- **Dependency:** Stage 6 ReAct reasoning.
- **Why it exists:** Prevents V1's failure mode where soft anomalies were either aggressively suppressed or conflated with hard errors.
- **Failure mode if removed:** V1 binary over-suppression resumes (F1 drops to $0.0659$).

---

### Stage 8: Verbatim Provenance & Suggested Fix Generation
- **Exact Implementation:** Sequence-indexed excerpt linking and single-sentence bridging fix generation.
- **Input:** Final verified verdict.
- **Output:** Human-auditable report citing exact scene numbers, verbatim text quotes, and concrete screenwriting repair fixes.
- **Deterministic vs. Probabilistic:** **Deterministic linking + generative repair sentence**.
- **Dependency:** Stage 7 verdict.
- **Why it exists:** Guarantees transparency and immediate utility for professional screenwriters and script supervisors.
- **Failure mode if removed:** Unverifiable black-box hallucination reports that writers cannot audit.

---

## 3. Minimum Technical Combination Summary

The demonstrated performance ($0.7821$ F1, $0.9508$ Precision, $80.91\%$ Addressable Recall) cannot be reproduced by removing any single component:
$$\text{Performance} = \mathbf{C}_{\text{Extraction}}^{\text{Hierarchical}} \circ \mathbf{S}_{\text{Storage}}^{\text{Append-Only}} \circ \mathbf{D}_{\text{Candidate}}^{\text{SQL Window (Zero LLM)}} \circ \mathbf{A}_{\text{Investigator}}^{\text{Bounded FastMCP ReAct}} \circ \mathbf{V}_{\text{Verdict}}^{\text{Two-Tier}}$$
