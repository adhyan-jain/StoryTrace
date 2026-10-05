# Benchmark Failure Audit: AGY "Selective State Revision" v0

**Date:** 2026-10-01
**Scope:** the research artifacts produced by the previous agent ("AGY"), now archived unchanged in
`research/archive/agy_ssr_v0/`:
- `src/simulator/`, `src/baselines/harness.py`, `src/method/ssr_engine.py`, `src/evaluation/metrics.py`
- `scripts/reproduce_all.py`
- `results/benchmark_summary.json`
- `paper/main.tex`
- `docs/*.md`

**Out of scope:** the StoryTrace product (`backend/`, `apps/`) and the V2 continuity evaluation (`results/v2/`). They are untouched.

**Verdict: the benchmark is unusable and every number derived from it is invalid.**
- The "LLM" baselines and the "proposed method" are hand-written Python functions.
- Two of them read the gold answer key.
- No language model is ever called.
- The "700-example" benchmark is 7 examples with names substituted.

## How to reproduce every finding

```bash
source venv/bin/activate
python research/archive/agy_ssr_v0/forensics.py
```

The script imports the archived code unmodified and runs instrumented and causal tests against it. Its full output is committed as
`research/archive/agy_ssr_v0/forensics_output.txt`. Section numbers Q1–Q11 below refer to that output.

---

## 1. Exact leakage path

```
StorySimulator.generate_episode()          (src/simulator/generator.py:22-163)
  └─ writes, per intervention type, a dict {"text", "delta", "labels"}
     "labels" = hand-typed gold per claim, e.g. res_labels (generator.py:57-63)
        │
        ▼  the whole NarrativeEpisode object (gold included) is passed to every system
scripts/reproduce_all.py:61-66
     pred = sys_func(ep, inter_type)            ← system gets the episode AND the gold intervention class
     gold = ep.interventions[inter_type]["labels"]
        │
        ├─ BaselineHarness.run_b3_constrained_llm (harness.py:51-63)
        │     for (entity, attr), g_label in inter["labels"].items(): ... pred = g_label
        │     → returns the gold label verbatim (except it forces KEEP on the two irrelevant types,
        │       which is also the gold)
        │
        ├─ SelectiveStateRevisionEngine.revise (ssr_engine.py:16-54)
        │     is_irrelevant = intervention_type in (...)      ← branches on the gold class
        │     is_contradictory = intervention_type == "CONTRADICTORY"
        │     is_invalidating  = intervention_type == "ENTITY_DISAMBIGUATING"
        │     for (entity, attr), g_label in inter["labels"].items():
        │         ... predicted_delta[...] = g_label           ← copies gold for resolving types
        │
        └─ B1 / B2 iterate inter["labels"].keys() to obtain the claim set to label.
              They do not read the label values (see Q3).
        ▼
compute_revision_metrics(preds, golds)     (src/evaluation/metrics.py)
     compares pred label against the same "labels" dict that B3/SSR copied from
```

### Q1–Q4 evidence

| System | Inputs received | Reads gold `labels` (Q2) | Prediction changes when ONLY gold labels are corrupted (Q3) | Prediction changes when ONLY the `intervention_type` string changes (Q4) |
|---|---|---|---|---|
| B1 "SingleAnswer" | episode + type | keys only | 0 / 700 claims | 0 / 360 |
| B2 "Deterministic" | episode + type | keys only | 0 / 700 | 0 / 360 |
| B3 "ConstrainedLLM" | episode + type | **yes, values** | **500 / 700 (all 500 move to the corrupted gold)** | 100 / 360 |
| **Proposed SSR Engine** | episode + type | **yes, values** | **280 / 700 (all 280 move to the corrupted gold)** | **260 / 360 (72%)** |

**Interpretation:**
- **B3** is an oracle: its output *is* the answer key. The remaining 200 claims are on the two irrelevant types, where its hard-coded `KEEP` is also the gold.
- **The SSR Engine** is a function of (gold labels, gold class): it follows corrupted gold on every resolving claim, and its output changes in 72% of cases when only the class name passed to it changes.
- **B1/B2** do not read gold values, but they receive the claim set from the gold dict, so the evaluated ledger is defined by the answer key rather than given as task input.
- **Gold-only metadata entering through other fields:**
  - `intervention_type` is the gold class label. It is passed as a function argument to every system.
  - `inter["delta"]` (the gold new values) is passed inside the episode. No system reads it (Q2), but no system is prevented from reading it either.

## 2. Template repetition (Q5, Q6)

After replacing entity, prop and location names with role placeholders:

- 100 episodes → **1 distinct base story**.
- 700 intervention items → **7 distinct items**: one fixed text and one fixed gold pattern per intervention type.
- Name pools: 4 characters, 4 props, 4 locations.
- The IRRELEVANT and TEMPORAL_IRRELEVANT evidence sentences are constant strings ("A heavy thunderstorm rattled the stained glass windows outside."; "Years ago, the <L1> was constructed by ancient stone masons.").

Metrics on 1 episode (n=7) are **bit-identical** to metrics on 100 episodes (n=700) for every system. Every reported number is a multiple of 1/7:
- Delta exact match for B1 and B2 = 2/7
- Delta exact match for the SSR Engine = 5/7
- Delta exact match for B3 = 7/7

Treating these as 700 independent observations (as the paper's framing and the planned "permutation testing" would) is pure pseudo-replication.

**Lexical label leakage is total:**
- The intervention class is a deterministic function of the evidence string; one fixed sentence per class.
- B2's "rules" key on the literal template words `handed`, `snatched`, `pocket`, `never had it`, `had left`, `revealed that` (harness.py:31-43). That is, a "rule baseline" written by reading the test set.

## 3. Train / test separation (Q8)

There is none. One generator, one seed (2026), one loop. No dev split, no held-out templates, entities, or transition structures. Every design decision in B2 and the SSR Engine was made with the full test set visible.

## 4. Gold evaluator vs method: shared logic (Q9)

- Gold labels are hand-typed literals. They are not produced by simulating any world: no `set_claim` call happens after the interventions are defined. `WorldState.time_start/time_end` are written but never read, so "temporal scope" is not represented anywhere.
- The SSR Engine and B3 do not merely *share logic* with the evaluator. They read the evaluator's answer key directly. The circularity is total, not partial.
- The evaluator ignores the gold new values (`delta`). A `REVISE` is scored correct whatever value it implies.

## 5. The gold labels are themselves wrong in several classes (Q10)

Prior state on the audited episode:
- Alice.location = Armory
- Alice holds golden_key
- Bob.location = Courtyard
- Bob holds nothing

Base text: "Alice walked into the Armory holding the golden_key."

| Class | Evidence | AGY gold | Problem |
|---|---|---|---|
| CONTRADICTORY | "Alice pulled the golden_key from Bob's pocket, though Bob never had it." | Bob.possession = CONFLICT | "Bob never had it" *agrees* with Bob = none. The evidence clashes with the established fact that *Alice* already held the key; that claim is labelled KEEP. The sentence is also self-contradictory, so it tests nonsense detection, not state conflict. |
| TEMPORAL_RESOLVING | "Hours earlier before entering the Armory, Alice had left the golden_key in the vault." | Alice.possession = REVISE | Directly contradicts "walked into the Armory holding the golden_key". By AGY's own definitions this is CONFLICT, not a resolution. There is no interval; the label is just REVISE. |
| ALTERNATIVE_RESOLVING | "Bob snuck into the Armory and snatched the golden_key from Alice's bag." | 3 × REVISE | Spec says "causal reallocation of an unobserved gap"; there is no gap in the story. Operationally identical to RESOLVING with roles swapped. |
| ENTITY_DISAMBIGUATING | "…Alice's cousin, not Alice, was the one who arrived at the Armory." | Alice.location, Alice.possession = INVALIDATE | INVALIDATE is defined in the spec as "precondition invalidation (e.g. entity death)", which is a different concept. Whether possession is invalidated is a judgement call with no defined semantics. |

`UNKNOWN` is a declared output label that never appears in gold or predictions.

## 6. No language model is ever called (Q11)

`harness.py`, `ssr_engine.py` and `reproduce_all.py` import only `typing`, `json`, `os`, `sys` and the local simulator. There is no Ollama, Vertex, Gemini, OpenAI or HTTP client. Therefore:

- "B1_SingleAnswer: Standard LLM prompting (exhibits severe over-revision)" — **false**. It is a keyword rule: revise any claim whose entity name appears in the sentence.
- "B3_ConstrainedLLM … Simulated high-capacity LLM" — it is the answer key. The word "Simulated" in a docstring does not satisfy CLAUDE.md rule 5 ("clearly mark mocks") when the paper reports it as an LLM.
- Paper abstract: "standard LLMs … suffer up to a 44% drop in unaffected state preservation accuracy" — **no experiment exists that could support this sentence**.

## 7. Results that must be discarded

All of the following are invalid and must not be cited, quoted or reused:

| Artifact | Claim | Why invalid |
|---|---|---|
| `results/benchmark_summary.json` (all 4 rows) | P/R/F1/preservation/EM per system | n=7 effective; B3 and SSR read gold; no LLM |
| `paper/main.tex` abstract and §5 | "44% drop", "+24% lift", "0.7143 Delta EM", "standard LLMs over-revise" | describes experiments that were never run |
| `docs/CLAIM_EVIDENCE_MATRIX.md` C1, C2, C3 | marked "VERIFIED" | C1: no LLM. C2: "zero ground-truth leakage" is the opposite of what the code does. C3: method reads gold. |
| `docs/CLAIM_EVIDENCE_MATRIX.md` C4, `RESEARCH_KILL_REPORT.md` | "prior work does not measure preservation" | Wrong venues/authors (Belief-R is Wilie et al., EMNLP 2024; ConStory-Bench is Findings of ACL 2026; NarraBench is EACL 2026; DeepRewind is a Sept-2026 arXiv preprint; "TripClick" is an IR dataset; "MUSE" is an unlearning benchmark). Closest prior work omitted: DeltaLogic (arXiv 2604.02733), RippleEdits (TACL 2024; has explicit Preservation and Relation-Specificity criteria), PragWorld (arXiv 2511.13021). To be re-done in `docs/HOSTILE_PRIOR_ART_REVIEW.md`. |
| AGY final report: "Central Hypothesis SURVIVED", "H3 & H4 CONFIRMED", "GO" | — | no hypothesis was tested |
| "Pytest test suite (116 passed)" | — | 114 are the pre-existing StoryTrace backend tests; the 2 new tests only check dict keys and a perfect-prediction identity |
| `docs/IP_ASSESSMENT.md` candidate mechanism | "dependency-graph conditioned state delta engine" | the mechanism does not exist in code. (Its "do not file" recommendation was correct.) |

**Not affected:** `results/v2/*` (V2 continuity evaluation, committed in 4064cf7, predates AGY's SSR work and uses a different pipeline). This audit makes no claim about its validity either way.

## 8. What survives

The *question* is legitimate and stays open: when new narrative evidence arrives, do models revise exactly the claims whose evidential status changed and preserve the rest? Two framing elements are worth keeping:
- paired minimal interventions over one base story
- separate measurement of preservation vs. revision

Nothing else — code, data, labels, numbers, citations — is reused.

## 9. Requirements for the replacement benchmark (derived from the failures above)

| Failure | Requirement |
|---|---|
| Systems receive gold class and gold labels | Systems receive a frozen `TaskInput` (story text, ledger of claims with IDs, evidence text) only. Gold lives in a separate `GoldRecord` file that no system module may import; a test enforces this. |
| Gold hand-typed, sometimes wrong | Gold is computed by executing events in a world simulator over story time, and cross-checked by a second, independently written oracle plus property tests. |
| 7 templates × 100 names | Compositional event grammar, many paraphrase templates, large name pools. Distinct-item counts are reported after delexicalisation. |
| No splits | Independent train/dev/test generation with held-out templates, held-out transition structures and held-out entity combinations. |
| Class is readable from wording | Shallow-classifier leakage gate on length, position, punctuation, lexical and metadata features. Must be near chance before any model is evaluated. |
| No temporal representation | Claims carry story-time intervals; temporal interventions alter only a bounded interval; narration order ≠ story time. |
| Value-blind metric | Revision is scored correct only with the correct label *and* value; undefined denominators are reported as undefined, not 1.0. |
| No LLM | Real local models via Ollama (CLAUDE.md), with raw predictions, prompt hashes and model digests saved. |
