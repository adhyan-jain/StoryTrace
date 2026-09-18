# StoryTrace V2 Architecture & Design Audit

**Document:** Comprehensive V2 Design Audit & Gap Analysis  
**Baseline:** StoryTrace V1 Frozen Baseline (`commit eab6ef63975ca906c1c615d5d69e6e03c6fd2b87`)  
**Target:** StoryTrace V2 Architecture Specification  
**Date:** September 18, 2026  

---

## 1. Executive Summary

StoryTrace V1 established the neurosymbolic paradigm for screenplay continuity checking: deterministic SQL window functions over an append-only temporal event log paired with a bounded investigation agent. While V1 proved decisively superior to monolithic one-shot LLMs (Condition A $+0.0672$ Macro-F1 vs. Condition D $0.0000$, $p = 0.0039$, Cohen's $d = +1.29$), V1's global recall remained low ($3.44\%$ Micro Recall) due to an overly narrow physical state extraction ontology.

The V1 unconstrained extraction ablation (Condition C) demonstrated that richer state tracking increases recall by **$+114.5\%$** (73 TPs vs. 34 TPs), but at a **$+50.4\%$ compute penalty** due to unstructured string comparisons.

**StoryTrace V2's core objective is to expand state representation coverage and deterministic candidate detection without abandoning closed-vocabulary tractability, computational efficiency, or auditable evidence provenance.**

---

## 2. V1 Bottleneck & Gap Analysis

```
+----------------------------------------------------------------------------------------------------+
|                                    V1 ERROR & BOTTLENECK FLOW                                      |
+----------------------------------------------------------------------------------------------------+
|                                                                                                    |
|  [Screenplay Scenes]                                                                               |
|         │                                                                                          |
|         ▼                                                                                          |
|  [State Extraction] ──(Bottleneck 1: Schema Narrowness) ──► Missed 85% of gold errors (dialogue,   |
|         │                                                   room shifts, temporal leaps, co-loc)   |
|         ▼                                                                                          |
|  [ClickHouse Store] ──(Bottleneck 2: Flat Entity Log)   ──► No spatial hierarchy, no time delta,    |
|         │                                                   no multi-entity co-presence tracking   |
|         ▼                                                                                          |
|  [SQL Candidate Det]──(Bottleneck 3: 4 Rigid Rules)     ──► Only fires on city/possession/injury   |
|         │                                                   (Theoretical Recall Ceiling: 8.49%)    |
|         ▼                                                                                          |
|  [Investigation Agt]──(Bottleneck 4: Proof Standard)    ──► Over-suppresses 14 TPs as plausible   |
|         │                                                   narrative ellipses                     |
|         ▼                                                                                          |
|  [Final Verdicts]   ──► Precision: 0.5965 | Micro Recall: 0.0344 | Macro F1: 0.0672                |
+----------------------------------------------------------------------------------------------------+
```

### 2.1 Where Recall is Lost in V1
1. **Extraction Scope Imbalance (85% of lost recall)**:
   - Gold dataset contains 989 fine-grained inconsistencies across 10 films.
   - V1 extracted 958 state facts, producing only **84 raw candidate transitions across 10 films**.
   - The absolute mathematical ceiling for V1 recall against this gold set is $84 / 989 = 8.49\%$.
2. **Co-Presence and Relational Blindness**:
   - V1 models entities in isolation (`PARTITION BY entity_id, attribute`). It cannot detect contradictions where Character A and Character B are claimed to be in two different locations while simultaneously having a conversation in the same scene.
3. **Spatial Hierarchy Flattening**:
   - V1 only checked `location.city` changes because checking raw `location` strings flagged every ordinary room-to-room cut as an error (causing 16/18 false positives in early tests). Consequently, impossible room-level teleports within the same city were invisible to SQL detection.
4. **Temporal Context Ignorance**:
   - V1 treated sequence numbers as uniform ordinal steps ($1, 2, 3, \dots$). It had no representation of scene time deltas (`NIGHT`, `DAY`, `MOMENTS LATER`, `YEARS LATER`), making travel-time contradictions undetectable.
5. **Investigation Agent Over-Suppression (14 TPs Lost)**:
   - The agent was instructed with a strict single-verdict proof standard. When an unbridged spatial jump occurred without explicit text proving the character lacked a car/transit, the agent marked it `resolved`.

---

## 3. Deep Competitor Mechanism Audit

| Dimension | StoryTrace V1 | ATLAS (Narrative Graph / NoT) | ConStory-Checker (ACL 2026) | Proposed StoryTrace V2 |
| :--- | :--- | :--- | :--- | :--- |
| **State Representation** | Flat key-value triples with closed vocabularies | Dynamic property graph with entity-relation edges | Unstructured natural language text spans in LLM context | **Hierarchical spatial-temporal typed state graph** |
| **Storage Engine** | Append-only ClickHouse OLAP log | In-memory graph / NetworkX | Stateless (Prompt context window) | **ClickHouse OLAP tables + Scene Co-Presence Index** |
| **Candidate Detection** | Deterministic SQL window functions (`lagInFrame`) | Probabilistic LLM graph traversal queries | Single-stage LLM-as-judge prompt | **Multi-Rule SQL Window + Relational Spatial/Temporal Join** |
| **Candidate Generation Cost** | $O(1)$ SQL queries (Zero LLM inference) | $O(N)$ LLM edge evaluations | $O(N)$ large context LLM calls | **$O(1)$ SQL queries (Zero LLM inference)** |
| **Investigation Mechanism** | Bounded ReAct agent via FastMCP ($k \le 6$) | Path search over generated graph | None (Immediate verdict) | **Two-Tier Calibrated ReAct Agent ($k \le 6$)** |
| **Evidence Grounding** | Verbatim ClickHouse `raw_excerpt` + `unit_id` | Graph node text references | Extracted quote spans (often paraphrased) | **Bidirectional unit-level verbatim trace provenance** |
| **Reproducibility** | Deterministic detection, frozen seeds | Non-deterministic graph construction | Stochastic sampling | **100% Deterministic Detection + Seeded Agent** |

### Key Architectural Learnings from Competitors:
- **ATLAS** demonstrates that multi-entity relations (e.g. `is_with`, `holding`, `located_at`) are essential for detecting co-presence anomalies, but constructing full graph edges via LLMs is prohibitively expensive and prone to hallucinations.
- **ConStory-Checker** shows that free-text LLM judges achieve reasonable recall on small passages (0.678 F1) but completely break down on full-length 120-page scripts due to attention dilution and lost temporal state.
- **StoryTrace V2 Opportunity**: Synthesize the relational power of ATLAS with the deterministic efficiency and scale of ClickHouse SQL by indexing **Scene Co-Presence** and **Hierarchical Spatial Tuples** directly in the analytical schema.

---

## 4. Proposed StoryTrace V2 Architecture

```
                                  STORYTRACE V2 ARCHITECTURE
                                  
  ┌────────────────────────────────────────────────────────────────────────────────────────┐
  │ 1. ENRICHED SCENE & STATE EXTRACTION                                                   │
  │    • Unit Segmentation (INT./EXT., Time-of-Day, Setting, Scene Number)                 │
  │    • Co-Presence List: present_entities = [character_1, character_2, prop_1]           │
  │    • Hierarchical Location: [setting_type, environment, specific_room]                 │
  │    • Relational State Tuples: possession(holder, target), interaction(source, target)  │
  │    • Temporal Anchor: time_delta in {CONTINUOUS, MOMENTS_LATER, DAY, NIGHT, FLASHBACK} │
  └───────────────────────────────────────────┬────────────────────────────────────────────┘
                                              │
                                              ▼
  ┌────────────────────────────────────────────────────────────────────────────────────────┐
  │ 2. DUAL-TABLE TEMPORAL OLAP ENGINE (ClickHouse)                                        │
  │    ├── state_events (entity_id, attribute, value, hier_location, time_anchor, seq)     │
  │    └── scene_co_presence (scene_unit_id, sequence_number, entity_ids[], time_of_day)  │
  └───────────────────────────────────────────┬────────────────────────────────────────────┘
                                              │
                                              ▼
  ┌────────────────────────────────────────────────────────────────────────────────────────┐
  │ 3. EXPANDED DETERMINISTIC CANDIDATE DETECTOR (Zero LLM Calls)                          │
  │    ├── Rule 1: Possession State Machine (lost -> held, held by A -> held by B)         │
  │    ├── Rule 2: Impossible Co-Presence (Entity in Scene X and Scene Y simultaneously)   │
  │    ├── Rule 3: Spatial Teleportation (Hierarchical mismatch under CONTINUOUS time)     │
  │    ├── Rule 4: Physical Inversion (injured -> healed without medical event)            │
  │    └── Rule 5: Epistemic / Relational Rupture (Dead entity participating in scene)     │
  └───────────────────────────────────────────┬────────────────────────────────────────────┘
                                              │
                                              ▼
  ┌────────────────────────────────────────────────────────────────────────────────────────┐
  │ 4. CALIBRATED TWO-TIER INVESTIGATION AGENT (ClickHouse MCP, max_calls = 6)             │
  │    • Tools: get_entity_timeline, get_unit_text, get_co_presence, get_spatial_path      │
  │    • Calibrated Verdicts:                                                              │
  │        - verified_hard_conflict (Direct logical/physical impossibility)                │
  │        - verified_narrative_anomaly (Unbridged leap / continuity slip)                 │
  │        - resolved (Legitimate off-screen ellipsis / flashback)                         │
  │        - uncertain (Insufficient textual evidence)                                     │
  └────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 5. Component Preservation vs. Redesign Matrix

| Component | V1 Implementation | V2 Decision | Design Rationale |
| :--- | :--- | :---: | :--- |
| **ClickHouse Storage Engine** | `state_events` MergeTree table | **PRESERVE & EXTEND** | OLAP append-only log is highly performant; add `scene_co_presence` table. |
| **Deterministic Candidate Paradigm** | Pure SQL window queries (no LLM calls) | **PRESERVE** | Core patentable novelty; guarantees $O(1)$ LLM cost at candidate generation. |
| **FastMCP Subprocess Bridge** | Stdio MCP bridge exposing ClickHouse queries | **PRESERVE** | Clean tool isolation compliant with standard agent protocols. |
| **Bounded Investigation Loop** | ReAct loop with max 6 calls + loop detection | **PRESERVE** | Prevents runaway agent cost and ensures bounded execution latency. |
| **State Extraction Prompt & Schema** | Narrow flat attributes (`possession`, `injury`) | **REDESIGN** | Add hierarchical location, co-presence lists, and temporal scene anchors. |
| **Candidate Detection Rules** | 4 single-entity rules | **REDESIGN** | Add multi-entity co-presence collision and continuous-time spatial jumps. |
| **Investigation Verdict Schema** | 3 flat statuses (`verified`, `resolved`, `uncertain`) | **REDESIGN** | Introduce calibrated severity (`hard_conflict` vs `narrative_anomaly`). |
| **Evaluation Isolation** | `data/eval/ablation/` and root json files | **REDESIGN** | Strict `results/v1/` vs `results/v2/` namespace separation. |

---

## 6. Expected Tradeoffs & Risk Mitigation

| Dimension | Expected Impact in V2 | Potential Risk | Mitigation Strategy |
| :--- | :--- | :--- | :--- |
| **Recall** | Projected to increase from **$3.4\%$ to $\mathbf{20\% - 35\%}$** on gold benchmark. | Higher candidate volume may increase Investigation Agent work. | Fast SQL pre-filters discard normal linear progressions before agent invocation. |
| **Precision** | Target precision maintained at **$\ge 0.60$**. | Richer extraction could introduce semantic extraction noise. | Closed schema types for temporal anchors (`CONTINUOUS`, `DAY`, `NIGHT`) and strict grounding regex. |
| **Compute Cost** | Target runtime within $\le 1.25\times$ of V1 Condition A ($< 9.0\text{h}$ across 10 films). | Multiple extraction fields could increase LLM prompt token size. | Combined single-pass structured JSON extraction per scene unit. |
| **Auditability** | 100% trace provenance maintained. | Complex rules might obscure verdict reasons. | Every candidate records the triggering SQL rule ID and input row IDs. |

---

## 7. V2 Validation & Roadmap Plan

1. **Phase 1: Architecture & Data Model (Branch: `v2-development`)**:
   - Define V2 Pydantic schemas in `backend/v2/models.py`.
   - Create ClickHouse V2 migrations (`state_events_v2`, `scene_co_presence_v2`).
2. **Phase 2: Enriched Extraction Pipeline**:
   - Implement `backend/v2/pipeline/enriched_extraction.py` supporting hierarchical spatial tuples and co-presence.
   - Unit test on synthetic test corpus (`controlled_test.txt`).
3. **Phase 3: Expanded SQL Candidate Detector**:
   - Implement `backend/v2/candidate_detection/detector_v2.py` with multi-entity and temporal window queries.
4. **Phase 4: Calibrated Investigation Agent**:
   - Equip agent with `get_co_presence` and `get_spatial_path` MCP tools.
5. **Phase 5: Evaluation & Auditing**:
   - Execute V2 benchmark on the identical 10-film corpus.
   - Store all outputs strictly in `results/v2/`.
   - Run paired statistical significance tests ($V2$ vs $V1$).
