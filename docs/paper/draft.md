# StoryTrace: Evidence-Grounded Narrative Continuity Analysis via Deterministic Detection and Bounded Agentic Investigation

*Draft -- structure complete, numeric results pending Phase 1/2 of
`~/.claude/plans/dapper-stargazing-adleman.md` (real Vertex AI pipeline runs
require GCP Application Default Credentials not available in the authoring
environment; human blind gold-annotation is a separate, human-only step).*

## Abstract

Automated continuity checking over long-form narrative documents --
screenplays, novels, serialized fiction -- requires both finding candidate
inconsistencies and judging whether they are real errors or narratively
justified. We present StoryTrace, a system that separates these two
concerns: a deterministic SQL pass over an append-only, controlled-vocabulary
event log generates candidate conflicts without invoking a generative model,
and a bounded tool-augmented agent (max [INSERT: current max_calls value,
re-check backend/agent/investigator.py at time of writing] tool calls)
adjudicates each candidate against verbatim retrieved evidence. We evaluate
against a one-shot LLM baseline and two ablations (pipeline-only, no
investigation; unconstrained-vocabulary extraction) on [INSERT: N] STAGE
screenplays. StoryTrace achieves precision [INSERT] / recall [INSERT] / F1
[INSERT], compared to [INSERT] for the one-shot baseline (p=[INSERT],
paired bootstrap). We report cost-efficiency and cross-domain
generalization results and discuss the specific role of vocabulary
constraint in enabling deterministic detection.

## 1. Introduction

Narrative continuity errors -- a character's injury that heals off-page, a
prop that reappears after being lost, a location that silently
contradicts an earlier scene -- are costly to catch by hand and easy for
long-context LLMs to hallucinate about when asked to "find every
continuity error" in one pass. Script supervisors on professional
productions catch these manually; independent authors and lower-budget
productions largely do not, and post-hoc fixes are expensive.

Existing automated approaches typically frame this as a single LLM-as-judge
call over the whole document (or a long-context retrieval-augmented
variant), inheriting two problems: (1) no persistent, queryable state means
every judgment is re-derived from raw text under context-window pressure,
and (2) no separation between "is this even a candidate worth examining"
and "is this candidate a real error" means the system's precision is
bottlenecked by a single generative pass with no cheap early filter.
ConStory-Checker [INSERT CITE] reports an overall F1 of 0.678 on its own
benchmark using this unified approach.

StoryTrace's contribution is architectural: separate deterministic
candidate generation (SQL window functions over a controlled-vocabulary
event log -- no generative model in the loop) from a bounded agentic
investigation phase that only runs on candidates the deterministic pass
already produced, and that must ground every verdict in verbatim retrieved
text.

Contributions:
1. A controlled-vocabulary entity-state extraction schema that makes SQL-only
   candidate detection possible (Section 4.2).
2. An append-only temporal event log design over ClickHouse enabling
   `lagInFrame`-based deterministic conflict detection (Section 4.3).
3. A bounded ReAct-style investigation agent with verbatim-evidence-grounded
   verdicts and a hard tool-call bound (Section 4.4).
4. An ablation study isolating the contribution of (a) vocabulary constraint
   and (b) the investigation phase, plus a cost-efficiency analysis against
   a one-shot LLM baseline (Section 6).

Paper organization: Section 2 reviews related work; Section 3 formalizes the
task; Section 4 describes the architecture; Sections 5-6 describe the
evaluation and results; Section 7 analyzes qualitative behavior; Section 8
discusses limitations; Section 9 concludes.

## 2. Related Work

**Narrative consistency detection.** ConStory-Bench / ConStory-Checker
[INSERT CITE, arXiv:2603.05890] frames continuity checking as unified
LLM-as-judge scoring over narrative spans. StoryTrace differs by
interposing a deterministic, non-generative candidate-generation stage
before any judge call, and by requiring every verdict to cite a specific
stored `unit_id`/`raw_excerpt` rather than a free-text judgment.

**Temporal knowledge graphs for narrative.** E²RAG [INSERT CITE,
arXiv:2506.05939], IA-RAG [INSERT CITE, arXiv:2606.06044], and NoT [INSERT
CITE, arXiv:2410.05558] build retrieval structures over narrative state but
do not enforce a closed, SQL-joinable value vocabulary -- retrieval quality
depends on embedding similarity, not exact-match state transitions.
StoryTrace's controlled vocabulary trades expressiveness for the ability to
detect conflicts with a plain SQL query, with no model call and no
similarity threshold to tune.

**Screenplay benchmarks.** STAGE [INSERT CITE, arXiv:2601.08510] provides
task assets (checkpoints, questions, role instances) for evaluating
narrative-change understanding across 151 bilingual movies, but does not
ship screenplay text itself or a continuity-error gold set -- this paper's
evaluation corpus resolves STAGE's per-film `script_url` metadata to source
text and builds continuity-error gold labels from scratch (Section 5.2).
ScriptBench [INSERT CITE if verified] is [INSERT].

**Evidence-grounded LLM reasoning and agent provenance.** CANVAS [INSERT
CITE, arXiv:2604.13452], PROVSEEK [INSERT CITE], and work on agent trace
provenance [INSERT CITE, arXiv:2606.04990] motivate grounding agent outputs
in retrievable evidence; StoryTrace's investigation agent follows a
ReAct-style loop [Yao et al. 2023, INSERT CITE] but is bounded to
[INSERT: current max_calls] tool calls specifically against a fixed,
append-only event log rather than open web/document retrieval.

## 3. Problem Formulation

- **NarrativeUnit** $u_i$: a document segment (scene, chapter, passage) with
  a sequence number $i$, `raw_text`, and `unit_id` -- see
  `backend/ingestion/models.py`.
- **EntityStateEvent** $e = (\text{entity\_id}, \text{attribute}, \text{value}, \text{sequence}, \text{raw\_excerpt})$:
  an extracted, controlled-vocabulary fact about an entity's state at unit
  $i$ -- see `backend/pipeline/state_extraction.py`.
- **CandidateConflict** $c = (e_{\text{prior}}, e_{\text{current}})$ where
  $e_{\text{prior}}.\text{value} \ne e_{\text{current}}.\text{value}$ for the
  same (entity, attribute) pair, produced by a SQL `lagInFrame` window query
  over the event log -- see `backend/candidate_detection/detector.py`.
- **InvestigationVerdict** $v \in \{\text{verified}, \text{resolved},
  \text{uncertain}\}$: the agent's adjudication of a candidate, with a
  severity, confidence, free-text explanation, and the tool-call trace that
  produced it -- see `backend/story_state/models.py`.
- **Task**: given document $D$, produce the set of verified conflicts
  $V(D)$ maximizing agreement (precision and recall) with human gold
  annotations $G(D)$ (Section 5.2), while minimizing generative-model calls
  spent on non-conflicting candidates.

## 4. System Architecture

### 4.1 Document Parsing and Unit Segmentation
[Describe screenplay scene-header segmentation vs. prose paragraph/chapter
segmentation -- see `scripts/eval/run_ablation.py`'s `load_screenplay_units`
for the screenplay-specific INT./EXT. scene-boundary convention used in this
evaluation, distinct from the blank-line paragraph convention used for
synthetic prose test documents.]

### 4.2 Controlled-Vocabulary Entity State Extraction
The extraction prompt (`backend/pipeline/state_extraction.py`) constrains
`possession.<prop>` values to `{held, acquired, lost}` and `injury.<body_part>`
values to `{injured, healed, dead}`; `location`/`location.city`/`clothing.<item>`
remain free-text but are validated against grounding checks (the value's
content words must appear in its own excerpt) rather than a fixed vocabulary.
[INSERT: vocabulary table]. Section 6.3/7.3 report what this constraint
costs and buys via the Condition A vs. C ablation.

### 4.3 Append-Only Temporal Event Log (ClickHouse)
[Describe the `state_events` MergeTree table, ordering by
(entity_id, attribute, sequence_number), and why append-only: every
extracted fact is retained rather than overwritten, so the full history of
an attribute's value is queryable.]

### 4.4 Deterministic SQL Candidate Generation
```sql
-- reproduced verbatim from backend/candidate_detection/detector.py at time
-- of writing -- re-verify before final submission, this file may change.
[INSERT: exact lagInFrame query text]
```
No generative model call occurs in this stage. A prior attempt at a fully
generic "any location change" rule was tried and reverted after producing
16/18 false positives (precision 0.111) -- the shipped detector only fires
on the four specific transitions listed in `detector.py`'s inline
documentation, a deliberately conservative design choice.

### 4.5 Bounded Investigation Agent
A ReAct-style loop (`backend/agent/investigator.py`) with four MCP-exposed
ClickHouse tools (`get_entity_timeline`, `get_unit_text`, `get_state_at_unit`,
`find_attribute_changes`) plus `finish`, bounded to
[INSERT: current max_calls value] tool calls, with duplicate-call detection
that forces early finalization after 2 identical repeats. Verdicts
(`verified`/`resolved`/`uncertain`) are produced only after the model
explains its reasoning (field order deliberately puts `explanation` before
`status` -- see the `FinalVerdict` docstring), and a `verified` verdict
triggers a suggested-fix generation step.

### 4.6 Revision-Aware Version Diffing
[Describe cross-version conflict diffing, joined on entity+attribute rather
than document position -- INSERT detail from `backend/api/main.py`'s diff
endpoint if in scope.]

## 5. Experimental Setup

### 5.1 Evaluation Corpus
[INSERT: N] STAGE-sourced screenplays (STAGE_v0 itself ships no screenplay
text -- `english_movie_info.csv`'s `script_url` column was resolved to
source pages, primarily IMSDb; see `scripts/eval/fetch_stage_screenplay.py`)
plus the synthetic `controlled_test.txt` diagnostic document with 3 planted
verified conflicts and 2 planted resolved cases. STAGE's own `num_scenes`
metadata field was found to use a unit inconsistent with literal INT./EXT.
scene-header counts (e.g. reporting 384 for a film with 192 real scene
headers) -- corpus bucket selection (>80 / 30-80 scenes) used real,
recomputed scene counts, not the CSV field, and this discrepancy is itself
worth noting as a caveat on any cross-paper comparison to STAGE's own
scene-count statistics.

### 5.2 Annotation Protocol
Gold conflicts were annotated [INSERT: describe blind vs. confirm-only
process actually used] by a single annotator; no second annotator/
inter-annotator agreement was computed for this draft ([INSERT if a second
annotator was later added]) -- see Section 8.2.

### 5.3 Evaluation Metrics
Precision/recall/F1 computed over each condition's candidate population plus
human-identified false negatives (not a global true-negative count -- see
Section 8.2 for why a global TN count is not well-defined for this task).
`resolution_precision` (correctly-resolved / total-resolved) is reported for
Condition A as a proxy for investigation-phase discrimination.

### 5.4 Baselines
- **Condition B (pipeline-only)**: SQL detection with every candidate
  auto-flagged `verified`, no investigation call
  (`backend/eval/pipeline_only_investigator.py`).
- **Condition C (unconstrained extraction)**: same extraction task, no fixed
  value vocabulary, same SQL detector and investigation agent
  (`backend/eval/unconstrained_extractor.py`).
- **Condition D (one-shot LLM)**: a single call with the full (or first
  50,000-character-truncated) screenplay and a free-text continuity-error
  extraction prompt (`scripts/eval/one_shot_baseline.py`). The spec's
  originally-named "Gemini 1.5 Pro" is confirmed unavailable (404) in this
  GCP project as of the 2026-09-14 pilot run -- the entire Gemini 1.5 family
  (pro, pro-002, flash, flash-002) is retired there. Condition D was
  substituted to **gemini-2.5-pro**; Condition A uses **gemini-2.5-flash**.
  **Model-version note**: this is still a genuine model-version confound
  (different Gemini 2.5 tiers, not the same model), on top of the original
  1.5-vs-2.5 substitution -- any precision/recall gap between A and D should
  not be read as purely architectural. See Section 8.2.

## 6. Results
*(All values below Section 6.0 are [INSERT] pending Phase 1/2 runs -- see
data/eval/metrics/aggregate.json once populated.)*

### 6.0 Phase 0 Pilot Validation (preliminary -- NOT the reported study)
Before committing to the full 10-film Phase 1 run, all four conditions were
executed once against real Vertex AI (gemini-2.5-flash for A/B/C,
gemini-2.5-pro for D) on the Phase 0 pilot set: *Aliens* (192 scenes),
*Scream 2* (76 scenes), and the synthetic `controlled_test.txt` (17 units,
the only pilot item with pre-existing hand-verified gold labels). This
section exists to confirm the pipeline runs end-to-end and to sanity-check
cost, not to substitute for Phase 1 -- N=1 run per condition per film, no
statistical test, no blind annotation.

**Accuracy (controlled_test.txt only -- the only pilot item with gold
labels)**, Condition A scored against the existing `data/eval/golden_dataset.py`:

| Phase | Precision | Recall | F1 | TP | FP | FN |
|---|---|---|---|---|---|---|
| Extraction | 0.630 | 0.690 | 0.659 | 29 | 17 | 13 |
| Detection | 1.000 | 0.800 | 0.889 | 4 | 0 | 1 |
| Investigation | 1.000 | 0.800 | 0.889 | 4 | 0 | 1 |
| **Overall** | | | **0.812** | | | |

For comparison, the most recent Ollama (`qwen2.5:7b`) run against the same
document/gold labels (`EVAL_REPORT.md`, 2026-09-12): overall F1 0.832,
Extraction F1 0.719, Detection/Investigation F1 0.889 each. Detection and
Investigation are identical across providers; Extraction is measurably
weaker on this one Vertex run (0.659 vs. 0.719), plausibly reflecting the
malformed/truncated-JSON extraction failures logged during the pilot run
(a handful of scenes per film failed Pydantic schema validation and were
silently dropped -- see Section 8.2). N=1 per provider; not a
provider-quality claim.

**Cost and candidate volume (all three pilot items, raw counts -- Aliens
and Scream 2 have no gold labels, so these are NOT accuracy figures):**

| Film | Cond. | Candidates | Surfaced/Findings | API calls | Cost (USD) |
|---|---|---|---|---|---|
| Aliens | A | 1 | 0 | 182 | 0.4092 |
| Aliens | B | 2 | 2 | 178 | 0.4076 |
| Aliens | C | 0 | 0 | 162 | 0.3423 |
| Aliens | D | -- | 3 | 1 | 0.0201 |
| Scream 2 | A | 0 | 0 | 67 | 0.1746 |
| Scream 2 | B | 1 | 1 | 68 | 0.1786 |
| Scream 2 | C | 0 | 0 | 64 | 0.1581 |
| Scream 2 | D | -- | 1 | 1 | 0.0182 |
| controlled_test | A | 4 | 2 | 33 | 0.0390 |
| controlled_test | B | 4 | 4 | 17 | 0.0305 |
| controlled_test | C | 1 | 1 | 22 | 0.0277 |
| controlled_test | D | -- | 5 | 1 | 0.0097 |

Total pilot cost: ~$1.82 across all three items and four conditions. Notably,
Condition A found **zero** candidates on both real screenplays (Aliens: 1;
Scream 2: 0) versus 4 on the deliberately-seeded `controlled_test.txt` --
without gold labels for the real screenplays this cannot be scored, but it
is a real, disclosable observation that warrants attention before Phase 1:
either real screenplays genuinely contain few bald (non-narratively-resolved)
contradictions at this scale, or detection/extraction is under-triggering on
real screenplay formatting relative to the synthetic benchmark. This should
be investigated (e.g. via a quick manual read of one film) before or during
Phase 1's blind annotation, not left as an unexamined pilot artifact.

**Known Phase 0 infrastructure issues** (fixed or worked around during the
pilot, documented here since they affect data provenance): a ClickHouse
Cloud `story_universe_id` that accumulates many prior DELETE mutations
(exactly what this eval harness's clear-and-reuse pattern does across
Conditions A-D and re-runs) can silently drop a subsequent insert of scene
data with no exception -- worked around with fresh per-run ids
(`backend/clickhouse/client.py`'s `insert_narrative_units` also now
chunks+verifies+retries as a partial mitigation); root cause not identified.
`mcp-clickhouse` must be resolvable on `PATH` for the Investigation Agent's
subprocess spawn. See `git log` around 2026-09-14/15 for full detail.

### 6.1 Main Results Table
[INSERT: Table 1 -- see docs/paper/tables.tex]

### 6.2 Entity-Type Breakdown
[INSERT: from data/eval/metrics/entity_type_breakdown.json]

### 6.3 Cost Efficiency Analysis
[INSERT: from data/eval/cost_analysis.json / cost_summary_for_condition()]

### 6.4 Cross-Domain Generalization
[INSERT: from data/eval/generalization_test.json, including the human
`manual_notes` field -- this is a qualitative finding, not a metric.]

### 6.5 Statistical Significance
[INSERT: from data/eval/metrics/aggregate.json's `statistical_test` field --
example-level paired bootstrap over pooled annotated conflicts, not a
per-film F1 bootstrap (10 films is too few points to bootstrap
informatively at the film level; see Section 8.2).]

## 7. Analysis

### 7.1 Qualitative Examples
[INSERT: one verified conflict, one correctly-resolved conflict, one
Condition-D false positive that Condition A suppresses -- pull directly
from ablation JSON files with real unit_id/raw_excerpt provenance, never
paraphrased.]

### 7.2 Failure Modes
[INSERT after reviewing annotated false positives/negatives.]

### 7.3 Effect of Vocabulary Constraint (A vs. C)
[INSERT: candidates_generated comparison -- expected sharply lower under
Condition C since free-form values rarely repeat exactly across units.]

### 7.4 Effect of the Investigation Agent (A vs. B)
[INSERT: precision comparison -- Condition B is expected to have recall
equal to Condition A's candidate coverage but lower precision, since every
candidate is auto-verified with no adjudication.]

## 8. Discussion

### 8.1 The Case for Separating Detection from Investigation
[Synthesize 7.3/7.4 findings once available.]

### 8.2 Limitations
- **Single annotator, no inter-annotator agreement** was computed for gold
  labels in this draft ([INSERT if changed]) -- gold labels reflect one
  annotator's judgment.
- **Condition D model-version confound**: Condition D runs Gemini 1.5 Pro
  while Condition A runs [INSERT model] -- part of any precision/recall gap
  may be attributable to model capability, not architecture alone.
- **No global true-negative count**: precision/recall are computed over the
  candidate population plus manually-identified false negatives, not a
  combinatorial true-negative universe (see Section 5.3).
- **Small corpus (N=[INSERT] films)**: the example-level bootstrap (6.5)
  partially mitigates this by resampling individual annotated conflicts
  rather than per-film F1 scores, but the underlying film sample remains
  small; results should be read as suggestive, not conclusive, pending a
  larger corpus.
- **STAGE screenplay text was resolved via third-party source URLs (mostly
  IMSDb), not distributed by STAGE itself** -- see Section 5.1; standard
  research-use norms for screenplay text apply, but this is not a
  redistribution-clean, licensed corpus.
- Extraction quality is the load-bearing wall for the entire pipeline: a
  missed or misclassified state fact cannot be recovered by later stages.
- Entity resolution failures (the same character/prop named differently
  across units) can fragment one entity's history into two never-joined
  attribute keys.
- Long-range tracking is bounded by what fits in the append-only log's
  practical query window; very long documents may need chunked evaluation.

### 8.3 Future Work
A fine-tuned extraction model to reduce dependence on prompt-engineered
vocabulary constraints; broader knowledge tracking beyond the four
attribute categories currently supported; cross-document (multi-book/
multi-script) continuity analysis.

## 9. Conclusion
[Synthesize once Section 6 numbers are in.]

## References
- ConStory-Bench / ConStory-Checker, arXiv:2603.05890
- STAGE, arXiv:2601.08510
- E²RAG, arXiv:2506.05939
- IA-RAG, arXiv:2606.06044
- NoT, arXiv:2410.05558
- CANVAS, arXiv:2604.13452
- Yao et al., ReAct: Synergizing Reasoning and Acting in Language Models, 2023
- PROVSEEK [INSERT full citation -- not independently verified in this draft]
- Agent trace/provenance, arXiv:2606.04990
