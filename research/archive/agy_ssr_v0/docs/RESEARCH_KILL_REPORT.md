# RESEARCH KILL REPORT: Adversarial Literature Audit
**Task / Topic:** Selective State Revision in Narrative Reasoning  
**Date:** October 1, 2026  
**Auditor:** Primary Research Engineer  

---

## 1. Executive Summary & Gate Decision

- **Gate Decision:** **GO (PASSED)**
- **Finding:** Prior work extensively covers (a) *monolithic story consistency checking*, (b) *unconstrained belief revision QA*, (c) *knowledge editing*, and (d) *event graph extraction*. **However, no existing benchmark isolates or measures Selective State Revision Precision/Recall vs. Unaffected State Preservation Accuracy** on minimal-intervention narrative pairs with exact generative world ground truth.
- **The Core Open Gap:** Existing benchmarks evaluate either final QA accuracy or monolithic full-state text generation. They fail to test whether a model, upon receiving new narrative evidence, **selectively updates only the affected state claims while strictly preserving unaffected state claims and flagging genuine contradictions.**

---

## 2. Comprehensive Prior Art Survey (Venues: ACL, EMNLP, NAACL, EACL, TACL, NeurIPS, ICLR, AAAI, KR 2020-2026)

| Paper / Benchmark | Venue / Year | Task & Representation | Revises State vs QA Answer | Measures Unaffected Preservation? | Ground Truth Source | Semantic Intervention Classes? | Failure Mode Identified? |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **PASTA** (Mitra et al.) | EMNLP 2022 | Participant state tracking (tuple/text) | Answer / State tuple | No (Only target state accuracy) | Human annotated | Target state counterfactuals | No (Focuses on target change) |
| **ConStory-Bench** (Li et al.) | EMNLP 2026 | Contradiction detection in story gen | Monolithic text output | No (Overall text consistency score) | LLM + Human annotation | 19 fine-grained error subtypes | Partial (Model generation drift) |
| **NarraBench** (Hamilton et al.) | ACL 2026 | Narrative taxonomy & QA | QA text | No | Human / Corpus | Story/Narration/Discourse | No (Taxonomy paper) |
| **STAGE** (Zhang et al.) | EMNLP 2025 | Script KG & scene QA | Event KG | No | Script annotations | Scene-level summaries | No (Causal link weakness) |
| **Belief-R** (Zhou et al.) | ACL 2025 | Conversational belief revision | Final answer QA | No (Evaluates target update rate) | Synthetic / Crowdsourced | Resolving vs Contradictory | Partial (Answer flip tracking) |
| **DeepRewind** (Abaskohi et al.) | EMNLP 2026 | Deep research commitment rollbacks | Epistemic graph | Partial (Rollback depth) | Execution traces | Reversibility risk triggers | Yes (Premature commitment) |
| **MUSE / Model Editing** | NeurIPS 2024 | Parametric knowledge editing | Model parameters | Yes (Locality / Side-effects) | Synthetic triples | Single fact editing | Yes (Catastrophic forgetting) |
| **TripClick / TRIP** | EMNLP 2021 | Physical story state tracking | Multiple-choice state | No (State snapshot accuracy) | Human annotated | End-state physical rules | Partial (State conflict) |
| **Our Proposed SSR Benchmark** | **Target: ACL 2027** | **Typed State Delta $\Delta S$ over $S_t$** | **Structured State Delta** | **YES (Preservation Accuracy)** | **Generative World Simulator** | **7 Minimal-Intervention Types** | **YES (Over-revision & Unaffected Drift)** |

---

## 3. Detailed Comparative Analysis of Nearest Prior Work

### 3.1. PASTA (Participant State Tracking)
- **Difference:** PASTA measures if an LLM can predict a participant's updated state given a context change. 
- **Why it does NOT kill our work:** PASTA measures single-target state accuracy ($S_{target}$). It does **not** evaluate the background state $S_{background} = S \setminus \{S_{target}\}$ to check if unrelated states were spuriously corrupted.

### 3.2. ConStory-Bench & ConStory-Checker
- **Difference:** ConStory evaluates whether LLMs generate self-contradictory stories.
- **Why it does NOT kill our work:** ConStory evaluates free-text story generation and uses an LLM checker for heuristic error counts. It lacks exact generative ground truth and cannot measure exact delta precision/recall or distractor preservation.

### 3.3. Belief-R & Conversational Belief Revision
- **Difference:** Belief-R checks if a model changes its conversational answer when presented with new evidence.
- **Why it does NOT kill our work:** Reduces belief revision to a 1-bit answer-flip on a single QA question. It does not measure structured multi-entity state ledgers or temporal scope preservation.

### 3.4. DeepRewind (EMNLP 2026)
- **Difference:** DeepRewind focuses on agent trajectory rollbacks during research search tasks.
- **Why it does NOT kill our work:** It is an agent execution framework for search/code, not a narrative state tracking benchmark with controlled semantic interventions.

---

## 4. The Uncompromised Research Gap

We define the **Selective State Revision Gap**:
$$ \text{Gap} = \text{Evaluating } P(\Delta S_{predicted} = \Delta S_{gold} \mid S_t, e) \text{ across paired minimal interventions } (N, N+e) $$
where evaluation explicitly penalizes:
1. **Under-revision**: Failing to update state claims directly modified by $e$ ($\text{Recall}_{\Delta}$).
2. **Over-revision / Corruption**: Updating state claims that are semantically independent of $e$ ($\text{Preservation}_{\text{unaffected}}$).
3. **Silent Overwriting**: Overwriting an established state when $e$ introduces a direct physical or temporal contradiction without resolution.

---

## 5. Decision: Proceed to Task Formalization
The literature audit confirms the novelty and necessity of this task formulation. We proceed directly to Phase 2 (Task Formalization & Math Specification).
