# StoryTrace: Evidence-Grounded Narrative Continuity Verification via Append-Only Temporal State Logging and Bounded Agentic Adjudication

**Target Venue:** EMNLP / ACL / NAACL (System Demonstration / Empirical NLP Track)  
**Author:** Adhyan Jain  
**Affiliation:** School of Computer Science & Engineering, Vellore Institute of Technology (VIT Vellore)  
**Status:** Research Manuscript & System Evaluation Proposal for Faculty Review  

---

## Executive Summary

### 1. What This Project Actually Is
**StoryTrace** is an enterprise-grade, neurosymbolic narrative continuity verification engine designed to automatically audit long-form narrative documents (such as feature-length screenplays, multi-chapter novels, and episodic scripts) for multi-hop consistency violations. Long-form creative texts are prone to latent continuity errors—such as characters exhibiting contradictory physical states across scenes, props teleporting or duplicating without acquisition events, and spatial locations conflicting across timeline intervals. Rather than relying on a single large language model (LLM) to perform monolithic, ungrounded error detection across tens of thousands of tokens, StoryTrace converts unstructured screenplay text into an append-only, temporally indexed event log in an OLAP database (ClickHouse), computes candidate state anomalies deterministically using SQL analytical window functions (`lagInFrame`), and deploys a bounded, tool-augmented ReAct Investigation Agent that autonomously interrogates the story universe through the Model Context Protocol (MCP) to confirm, refute, or explain candidate anomalies with verbatim citations.

### 2. Core Scientific & Engineering Novelty
The fundamental novelty of StoryTrace lies in its **strict decoupling of deterministic candidate generation from bounded, evidence-grounded agentic adjudication under a closed-vocabulary state grammar**:
1. **Zero-Inference Candidate Generation via Controlled State Semantics:** Unlike existing retrieval-augmented generation (RAG) and graph-based narrative tracking systems (e.g., E²RAG, IA-RAG, ConStory-Checker) that rely on soft semantic similarity thresholds or unconstrained LLM-as-a-judge passes, StoryTrace constrains physical entity states (e.g., possession $\in \{\text{held}, \text{acquired}, \text{lost}\}$, injury $\in \{\text{injured}, \text{healed}, \text{dead}\}$) into a formal, closed-world grammar. This allows candidate narrative inconsistencies to be detected with $O(1)$ statistical inference cost purely through SQL temporal window queries over an append-only event stream.
2. **Bounded ReAct Adjudication with Auditable Tool Provenance:** To eliminate the severe hallucination and false-positive rates inherent in naive LLM reviewers, candidate anomalies are adjudicated by an autonomous investigation agent constrained to a hard budget of tool invocations (max 6 calls via ClickHouse MCP). The agent is prohibited from issuing ungrounded verdicts: every determination (`verified`, `resolved`, `uncertain`, `intentional`) must cite verbatim textual excerpts and timeline sequences from the immutable event store, providing mathematically auditable trace provenance for script supervisors and narrative editors.

---

## 1. Problem Formulation & Formal Task Definition

Let a narrative manuscript $\mathcal{D}$ be segmented into an ordered sequence of $N$ discrete narrative units:
$$\mathcal{D} = \langle u_1, u_2, \dots, u_N \rangle, \quad u_i = \left(\text{unit\_id}_i, \text{seq}_i, \text{heading}_i, \mathcal{T}_i\right)$$
where $\text{seq}_i \in \mathbb{N}$ denotes the temporal sequence index and $\mathcal{T}_i$ is the raw narrative text of scene $u_i$.

### 1.1 State Extraction & Canonical Entity Space
Let $\mathcal{E}$ denote the universe of resolved canonical entities (characters, props, locations) and $\mathcal{A}$ denote the set of tracked state attributes:
$$\mathcal{A} = \{\text{possession}.p, \text{injury}.b, \text{location}, \text{clothing}.c\}$$

For each unit $u_i$, an extraction operator $\Phi: \mathcal{T}_i \to \mathcal{S}_i$ maps narrative text to a set of atomic state events:
$$e = \left(\text{entity\_id}, \text{attribute}, \text{value}, \text{seq}_i, \text{raw\_excerpt}\right) \in \mathcal{S}_i$$
where $\text{value} \in \Sigma_{\text{attr}}$ is strictly governed by the closed vocabulary:
$$\Sigma_{\text{possession}} = \{\text{held}, \text{acquired}, \text{lost}\}, \quad \Sigma_{\text{injury}} = \{\text{injured}, \text{healed}, \text{dead}\}$$

### 1.2 Append-Only Temporal State Engine
State events are persisted into an append-only MergeTree table partitioned by `story_universe_id` and ordered by `(entity_id, attribute, sequence_number)`:
$$\mathcal{H}(\mathcal{D}) = \bigcup_{i=1}^N \mathcal{S}_i$$

### 1.3 Deterministic Candidate Conflict Detection
A candidate continuity conflict $c = (e_{t_1}, e_{t_2})$ occurs when two consecutive state events for the same entity and attribute exhibit a physically invalid state transition without an intermediate resolution event:
$$c = \left\{ (e_{t_1}, e_{t_2}) \in \mathcal{H}(\mathcal{D})^2 \;\middle|\; \begin{aligned} &e_{t_1}.\text{entity} = e_{t_2}.\text{entity} \land e_{t_1}.\text{attr} = e_{t_2}.\text{attr} \\ &\land t_1 < t_2 \land \nexists e_{t_3} (t_1 < t_3 < t_2) \land \mathcal{V}(e_{t_1}.\text{val}, e_{t_2}.\text{val}) = \text{invalid} \end{aligned} \right\}$$

This is executed deterministically in ClickHouse using SQL analytical window functions:
```sql
SELECT
    story_universe_id,
    entity_id,
    attribute,
    value AS current_value,
    sequence_number AS current_seq,
    lagInFrame(value, 1) OVER w AS prior_value,
    lagInFrame(sequence_number, 1) OVER w AS prior_seq,
    raw_excerpt AS current_excerpt,
    lagInFrame(raw_excerpt, 1) OVER w AS prior_excerpt
FROM state_events
WHERE story_universe_id = %(universe_id)s
WINDOW w AS (
    PARTITION BY story_universe_id, entity_id, attribute
    ORDER BY sequence_number ASC
    ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
)
HAVING prior_value != '' 
   AND prior_value != current_value
   AND isValidTransition(attribute, prior_value, current_value) = 0;
```

---

## 2. System Architecture

```
+-----------------------------------------------------------------------------------------+
|                                    STORYTRACE PIPELINE                                  |
+-----------------------------------------------------------------------------------------+
|                                                                                         |
|   +-----------------------+       +-------------------------------------------------+   |
|   | Screenplay / Novel    | ----> | Ingestion & Segmentation Engine                 |   |
|   | Raw Text Document (D) |       | (Scene Boundaries: INT./EXT., Sequence Indexing) |   |
|   +-----------------------+       +-------------------------------------------------+   |
|                                                            |                            |
|                                                            v                            |
|                                   +-------------------------------------------------+   |
|                                   | Controlled-Vocabulary Entity-State Extractor    |   |
|                                   | (LLM-guided, strict Pydantic grammar schemas)   |   |
|                                   +-------------------------------------------------+   |
|                                                            |                            |
|                                                            v                            |
|                                   +-------------------------------------------------+   |
|                                   | Append-Only Temporal State Engine (ClickHouse)  |   |
|                                   | (MergeTree ordered by entity, attr, seq)        |   |
|                                   +-------------------------------------------------+   |
|                                                            |                            |
|                                                            v                            |
|                                   +-------------------------------------------------+   |
|                                   | Deterministic SQL Analytical Detector           |   |
|                                   | (lagInFrame Window Operations: Zero LLM Calls)  |   |
|                                   +-------------------------------------------------+   |
|                                                            |                            |
|                                           [Candidate Conflicts Generated]               |
|                                                            |                            |
|                                                            v                            |
|                                   +-------------------------------------------------+   |
|                                   | Bounded ReAct Investigation Agent               |   |
|                                   | (ClickHouse MCP Tools: max 6 tool calls)        |   |
|                                   +-------------------------------------------------+   |
|                                                            |                            |
|                                                            v                            |
|                                   +-------------------------------------------------+   |
|                                   | Auditable Continuity Autopsy & Evidence Dossier |   |
|                                   | (Verified / Resolved / Uncertain / Intentional) |   |
|                                   +-------------------------------------------------+   |
+-----------------------------------------------------------------------------------------+
```

### 2.1 Investigation Agent & MCP Protocol
For each detected candidate $c$, the **Investigation Agent** acts as an autonomous adjudicator equipped with four specialized Model Context Protocol (MCP) tools:
1. `get_entity_timeline(entity_id, from_seq, to_seq)`: Retrieves the complete event history for an entity within a temporal window.
2. `get_unit_text(unit_id)`: Fetches full unparsed narrative context surrounding the candidate transition.
3. `get_state_at_unit(entity_id, sequence_number)`: Computes the aggregated prefix state of an entity up to sequence $k$.
4. `find_attribute_changes(entity_id, attribute)`: Evaluates global attribute trajectories across the story universe.

The agent operates in a ReAct loop (`Thought` $\to$ `Action` $\to$ `Observation` $\to$ `Final Verdict`) capped at a strict upper limit ($k \le 6$) of tool calls, terminating with an immutable Pydantic schema:
```python
class InvestigationVerdict(BaseModel):
    status: Literal["verified", "resolved", "uncertain", "intentional"]
    severity: Literal["critical", "warning", "info"]
    confidence: float = Field(ge=0.0, le=1.0)
    explanation: str
    investigation_actions: list[str]
    evidence_citations: list[str]
```

---

## 3. Experimental Setup & 4-Way Ablation Design

To rigorously evaluate the system, we construct a 4-way ablation protocol across 10 full-length real-world screenplays from the established STAGE narrative benchmark:

| Condition | Architecture Name | Extractor Vocabulary | Conflict Detector | Investigation Agent |
| :--- | :--- | :--- | :--- | :--- |
| **A** | **Full StoryTrace** | **Controlled / Closed** | **Deterministic SQL (`lagInFrame`)** | **Active (Bounded ReAct via MCP)** |
| **B** | **Pipeline Only** | **Controlled / Closed** | **Deterministic SQL (`lagInFrame`)** | *None (All candidates accepted)* |
| **C** | **Unconstrained** | *Free-Text / Open* | Free-Text SQL Join | **Active (Bounded ReAct via MCP)** |
| **D** | **One-Shot Baseline** | *N/A (Monolithic)* | *N/A (LLM Direct Prompt)* | *N/A (Zero-shot LLM-as-judge)* |

### 3.1 Research Corpus
The evaluation corpus spans 10 canonical feature films representing diverse genres, character counts, and temporal complexities:
1. *Chasing Amy* (`chasing_amy`)
2. *Darkman* (`darkman`)
3. *Do the Right Thing* (`do_the_right_thing`)
4. *Dog Day Afternoon* (`dog_day_afternoon`)
5. *Fargo* (`fargo_film`)
6. *Inception* (`inception`)
7. *Punch-Drunk Love* (`punch_drunk_love`)
8. *Smokin' Aces* (`smokin_aces`)
9. *Snow White and the Huntsman* (`snow_white_and_the_huntsman`)
10. *The Bourne Identity* (`the_bourne_identity_2002_film`)

### 3.2 Evaluation Metrics
- **Micro / Macro Precision ($P$), Recall ($R$), and $F_1$-score** evaluated against expert human-annotated gold standard datasets (`gold_dataset_v3.json`).
- **Cost & Latency Efficiency:** Wall-clock runtime, total tokens, and GPU inference seconds per screenplay.
- **Auditable Grounding Rate:** Percentage of reported errors containing verified, exact-match text citations.

---

## 4. Key Expected Contributions & Comparison with Prior Art

| Capability / Metric | StoryTrace (Ours) | ConStory-Checker (ACL '26) | E²RAG / IA-RAG | One-Shot Long-Context LLM |
| :--- | :--- | :--- | :--- | :--- |
| **State Storage** | Append-Only OLAP (ClickHouse) | None (In-Context) | Graph / Vector DB | None |
| **Candidate Detection** | **Deterministic SQL ($O(1)$ LLM)** | Generative LLM pass | Soft Vector Cosine ($\text{sim} \ge \theta$) | Generative LLM pass |
| **State Grammar** | **Controlled Closed Vocabulary** | Free-text unstructured | Unstructured natural language | Unstructured natural language |
| **Adjudication Phase** | **Bounded ReAct Agent (MCP)** | Single Judge Call | Retrieval-guided Generation | Zero-shot / Few-shot |
| **Evidence Grounding** | **Verbatim Unit IDs & Spans** | Abstract Rationale | Retrieved Chunk Embeddings | Hallucinated / Approximate |
| **Tool Budget** | $\le 6$ Bounded Invocations | Single-pass | Unbounded Search | 0 |

---

## 5. Research Roadmap & Proposed Faculty Collaboration

1. **Inter-Annotator Agreement (IAA) Study:**
   - Onboard 2 independent student annotators using our standardized [`docs/ANNOTATION_GUIDELINES.md`](file:///home/adhyan/Desktop/StoryTrace/docs/ANNOTATION_GUIDELINES.md) to calculate Cohen's $\kappa$ / Fleiss' $\kappa$ across the 10-film gold standard.
2. **Multi-Model Scaling Comparison:**
   - Benchmark local open-weights inference (`qwen2.5:7b`, `llama-3.1:8b`) against proprietary frontier models (`gemini-1.5-pro`, `gpt-4o`) to quantify neurosymbolic architectural gains across model sizes.
3. **Conference Target:**
   - Submission to **EMNLP 2027 System Demonstrations / Long Papers** or **ACL 2027**.
