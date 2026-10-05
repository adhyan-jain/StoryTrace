# SSR V2 preregistration (written 2026-10-03, BEFORE any V2 attacker result and BEFORE any V2 LLM result)

Status of knowledge at the time of writing (disclosure): V1 results, the V1 adversarial audit and the prior-art recheck (`results/V2_PRIOR_ART_RECHECK.md`) have been seen.
Seen for V2: only the generator feasibility pilot (`results/v2/feasibility_pilot.json`: counts of achievable matched pairs per depth, no attackers, no models).
Rules below are frozen by sha256 (recorded in `results/V2_DECISION_LOG.md`). Any later change is an amendment dated and listed separately; results obtained before an amendment are not re-interpreted under it.
Scope: phenomenon only. No method (SSR/AANST or other) is built. V1 files and results are not modified (hash manifest `results/snapshot_v2_start/TREE_HASHES.txt`). Local Ollama models only.

## 1. Research question
Can LLMs perform causally localized state revision when the information that determines the required update is distributed across a sequential story, while preserving state that should remain unchanged?
The question is asked narrowly, about current local 7-9B models on a controlled synthetic world plus one small real-execution domain. It is NOT assumed that failure reflects a reasoning limitation.

## 2. Competing explanations the design must separate
E1 genuine sequential/state-revision difficulty; E2 failure to follow an explicit rule; E3 representation/format; E4 ambiguous or incomplete information; E5 reference dependence (needing a correct prior state); E6 lexical/positional/count/template shortcuts.

## 3. Task (V2-state)
Input: story (intro states the initial world; day-tagged events, narrated in order or shuffled where causally valid) + ONE new sentence at a free day + 10 claim questions WITHOUT prior values.
Output: JSON `{claim_id: final value}` with each value enum-constrained to the claim's domain (locations / character names + `nobody` / `injured` or `unharmed`). The scorer derives the revision by comparing against the oracle prior state.
Claim set: a fixed function of the evidence surface form, entity lists, evidence slot and horizon only (`ssr_v2/core.py: claim_keys`); never of the event trajectory; identical within a matched pair.
Evidence is always a single event sentence (move, give, pickup, drop, injure, heal) at a free day >= 2. Outcome classes (oracle-derived): resolving, irrelevant, blocked (event impossible under a world law; the story world is unchanged, final state = prior).
Assertion-type evidence from V1 is not used in V2.

## 4. Gold, validity and set-valued scoring
Gold from BOTH V1 oracles (`oracle_a`, `oracle_b`), required to agree on every item. A story-replay solver (text only) is also evaluated (section 8).
Set-valued stratum: disjunctive evidence ("moved to X or Y, unclear which"). Gold = set of valid joint final states {world_X, world_Y}; an output is valid iff it equals one world's state on ALL claims jointly (carried-prop location must agree with the chosen alternative).
Semantic scorer for every item: closed-vocabulary normalisation (case, articles, `nobody`/`no one`/`none`), REVISE-to-same-value == KEEP, set-valued gold, cross-claim invariants (holder/proploc/loc consistency). Strict scorer: exact enum equality with the canonical state. BOTH reported everywhere; conclusions must hold under the semantic scorer.

## 5. Matched pairs and causal depth
Pair = (S1, S2, evidence, claims). Hard validators: both stories valid under both oracles; evidence text byte-identical; claim keys identical; exactly one event sentence differs; the revisions (non-KEEP claims with values) DIFFER; both members have the same causal depth; `|n_sentences(S1) - n_sentences(S2)| = 0`.
Consequence (proved by the validator, not assumed): any deterministic story-blind function is wrong on at least one member of every pair (pair-both-correct = 0), and the story-blind Bayes bound (best constant output per group of identical non-story inputs) is <= 0.50 item-level.
Causal depth D = size of the support set = number of distinct events that are last writers (before the evidence) of every state variable the evidence reads, plus the first later overwriter of every variable it writes that a claim reads afterwards (`core.support_set`). Secondary notion: ancestor-closure size (`core.ancestor_closure`). Length is equalised across depth strata by matching the n_sentences histogram, and by padding with events outside every claim's variables (validated: padding leaves the revision unchanged).
Feasibility pilot result (2026-10-03, 1,500 samples): equal-depth pairs found per depth 0/1/2/3/4 = 197/614/459/52/5 (pairs, not independent stories). No grammar extension needed; depth 4 is oversampled by drawing more candidate stories.

## 6. Test design and sizes (frozen)
- train: 400 pairs (attackers, 3 few-shot examples), pool A, seed block 2001.
- dev: 20 pairs, pool A, seed 2002. Used ONLY to confirm that each prompt produces parseable JSON; no prompt text is changed after the dev smoke except for fixing a format bug, and any such change is logged.
- test_main: 150 pairs = 300 items, pool A, seed block 2003: D1, D2, D3, D4 x 30 pairs (120) + length control 30 pairs (D2 with >= +6 padding sentences). Each stratum matched on n_sentences histogram and entity count (3 chars; 4 chars in <= 25% of pairs, equal across strata).
- set-valued: 30 unpaired disjunctive-evidence items, pool A, seed 2004.
- transform subsample: first 50 pairs (100 items) of test_main balanced over D1-D4 (12/13 pairs each), used for transformations.
- Entity pools: test uses pool A like train (names are not the experimental variable; entity renaming is a transformation, cross-pool pool B included).

## 7. Conditions (same items, same output format, temperature 0, seed 0, num_ctx 6144, num_predict 500)
K1 explicit imperative rules + world laws (V1 `rules.txt` adapted); K1-fs K1 + 3 train examples; K2 no rules, no laws (resolving + irrelevant items only); K3a, K3b substantially rewritten rules with word 3-gram Jaccard overlap < 0.25 to `rules.txt` (measured and reported); K4 declarative world laws only, no imperative procedure, including "an event that cannot happen under these laws did not happen"; PG = K1 plus TRUE prior value for each claim at its slot; S0 = same story and claims, NO new sentence (prior-state tracking); K1-delta = K1 with V1-style KEEP/REVISE/CONFLICT output (100-item subsample).
Models (no substitution): qwen2.5:7b, llama3:latest, qwen3:8b (think=False), mistral:7b; exact digests recorded; each must show 100% GPU placement. Optional sensitivity (declared now): qwen3:8b with thinking enabled, token cap raised to 4096, on 60 items, reported separately and never pooled.

## 8. Reference solvers and attackers (computed BEFORE any LLM)
Story-replay oracle: text-only parser + replay (adapted from `systems/symbolic.py`), reads the story, evidence and claims. Must reach >= 0.98 semantic state-EM on test_main, on the set-valued stratum and on every transformed set.
Story-blind attackers (trained on train only; inputs = evidence text, claim questions, entity lists; NO story): ledger_lookup (adapted: evidence + claim set only), positional, lexical-overlap, template/nearest-neighbour, entity-blind, claim-count prior, majority prior, plus a gradient-boosting search over every non-story field (any model that fits is reported as an attacker). Also the story-blind Bayes bound.

## 9. G9 gate (all conditions must hold on test_main; thresholds fixed now)
(a) pair-both-correct, upper 95% pair-cluster bootstrap CI <= 0.02 for every story-blind attacker; (b) item semantic state-EM upper 95% CI <= 0.55 for every story-blind attacker; (c) accuracy on claims whose gold value changes <= (majority-per-attribute baseline accuracy on those claims) + 0.05; (d) story-blind Bayes bound <= 0.55; (e) story-replay oracle >= 0.98; (f) oracles A and B agree on 100% of items; (g) every pair satisfies all section-5 validators. If G9 fails after the ONE redesign round allowed (changes logged), the project is KILLED at the benchmark stage; no LLM is run before G9 passes.

## 10. Metrics
Primary: item semantic state-EM under K1 on test_main (per model), reported with the Story-Use Gap and the Replay Gap:
- Story-Use Gap = state-EM(model, K1) - state-EM(best story-blind attacker); H1 asks whether it exceeds 0.05.
- Replay Gap = state-EM(replay oracle) - state-EM(model, K1).
Secondary: pair-both-correct, 4-way pair consistency (both / neither / S1 only / S2 only) and the rate at which a model changes its output in the direction of the differing prior state while keeping shared downstream claims fixed; required-change recall; preservation; collateral edit rate and count; claims modified/missed; strict state-EM; invalid-output rate; per-claim error class (correct minimal revision, under-revision, over-revision, wrong-value revision, contradictory revision = jointly inconsistent final state, semantically equivalent revision, invalid, collateral edit on unrelated entity); PG, S0 decomposition: P(S0 correct), P(revision correct | S0 correct on the relevant claims), P(PG correct).

## 11. Hypotheses and nulls
H1 story use: Story-Use Gap > 0.05 (null: <= 0.05). H2 depth: semantic state-EM(D4) is lower than state-EM(D1) by >= 0.15 at matched length (null: < 0.15); constant-depth length effect (D2 short vs D2 padded) is reported with its own CI and is not a hypothesis. H3: PG state-EM exceeds K1 by < 0.10 (failure persists when the prior state is given) vs >= 0.10 (story reconstruction matters). H4: K2/K3a/K3b/K4 semantic state-EM do not exceed K1 by >= 0.10 for >= 2 models (null: some wording lifts performance by >= 0.10). H5: effect survives each transformation (|delta vs identity| < 0.10).
Attack K rules: "rule-following explains most of the effect" iff the best of {K2, K3a, K3b, K4} reaches semantic state-EM >= 0.80 for >= 3 of 4 models. "Story reconstruction explains" iff PG - K1 >= 0.15 with 95% CI lower bound >= 0.10 for >= 3 models or S0 accuracy < 0.50. "Representation explains" iff K1-delta vs K1 differ by >= 0.15 (CI excluding 0) for >= 3 models.

## 12. Exclusions, seeds, sample size, stopping
No item is excluded after generation. Unparseable / out-of-enum outputs count as errors and are reported as invalid rate. Generation seeds as in section 6; LLM temperature 0, seed 0. Pair counts above are the pre-specified sample (150 pairs main; 50 pairs transforms). Stage A (K1, K2, K4, PG, S0, set-valued) runs first; if semantic state-EM >= 0.90 for all models under K1 AND PG, the phenomenon is declared absent and Stage B is not run. Stage B (K1-fs, K3a, K3b, K1-delta, transforms) and the external set run only after Stage A and after explicit user approval for GPU time.

## 13. Transformations (test_main transform subsample, K1)
entity renaming (same pool and pool B), causally valid narration shuffle, evidence paraphrase, rule paraphrase (= K3a/K3b), novel templates (disjoint from all existing templates, test enforced), lexical substitution (verb synonym swap), irrelevant-context insertion (events outside every claim variable, validated), changed surface ordering with fixed causal structure. Each transformed set: gold recomputed by both oracles, invariance asserted, story-replay oracle >= 0.98, G9 re-run. Collapse flag: |delta state-EM vs identity re-realisation| >= 0.10 for any model.
Survival rule per model: preservation CI upper < 0.97 OR required-change recall CI upper < 0.85, AND state-EM < 0.90, on every set.

## 14. External set (separate, reported separately)
Real execution traces of filesystem + git commands in sandboxed temp dirs; gold from re-executing the commands; about 30 matched pairs, depth 1-3; conditions K1, PG, S0; same models. Purpose: artifact-of-grammar check, not statistical power. Direction of effect only.

## 15. Statistics
Unit = matched pair (or story). Exact McNemar for paired correctness; pair-cluster bootstrap CIs (10,000); sign-flip permutation for continuous paired metrics; Cohen's h / paired risk difference as effect sizes; Holm correction within each family (H1-H5 per model); per-model and pooled results (pooled = bootstrap over pairs, models fixed). No p-value is used alone.

## 16. Decision rule (applied mechanically in `results/V2_DECISION_LOG.md`)
GREENLIGHT only if ALL: G9 passes; story-blind attackers meet (a)-(d); replay oracle >= 0.98; H1 supported for >= 3 of 4 models; the effect survives K3a, K3b, K4 and K2 (state-EM stays < 0.80 for >= 2 models); survives all transformations; the semantic scorer does not remove it (state-EM < 0.80); H2 supported OR H1's gap grows with depth; external set shows the same direction for >= 3 of 4 models; the prior-art recheck leaves a stated gap.
CONDITIONAL if the phenomenon is real but exactly one of those conditions is unresolved, or external evidence is insufficient.
KILL if any of: G9 fails after the allowed redesign; Story-Use Gap <= 0.05 for >= 3 of 4 models; rule-following explains most of the effect (section 11); semantic scoring brings state-EM >= 0.80 for >= 3 of 4 models; the phenomenon fails the survival rule on >= 2 transformations.
Every killed claim is listed individually with the number that killed it.

## 17. Interpretation rules and forbidden claims
Allowed form (only if the controls support it): "Under controlled sequential revision tasks where the required update is causally dependent on distributed prior state and unrelated state must be preserved, current local LLMs exhibit a [measured] story-dependence gap and [measured] under-/over-revision rates relative to symbolic story replay."
Forbidden: "LLMs cannot reason about sequential state"; any claim about larger or frontier models; any claim of novelty not supported by the prior-art table; any claim about EchoTales or patent-sensitive material (this project is separate and uses none of it).
If models do not beat the best story-blind attacker (H1 null), the correct statement is that they behave like story-blind systems on this task; that is recorded as such and is not rewritten as a reasoning claim.

## 18. Reproducibility
All data, attackers, validators, oracles, scorers and analyses are code under `research/ssr_v2/` and regenerate from fixed seeds; raw predictions, gold states/sets, semantic judgments, attacker outputs, pair ids, transform ids, depth labels, model metadata (digest, quantisation, temperature, seed, prompt sha256, GPU utilisation, runtime, retries, failures) are written to `research/results/v2/`.

---
## Amendment 1 (2026-10-03, written BEFORE any V2 attacker result and BEFORE any V2 LLM result)
Reason: while implementing the output format I found that, in a final-state format, a resolving item and its irrelevant partner can have identical gold final values on every post-evidence claim (e.g. "Bob moved to the library" gives the same final location whether or not Bob was already there), so a story-blind function could be right on both members. The section-5 validator "revisions differ" is therefore NOT sufficient.
Change (additive, everything else unchanged): a matched pair is valid only if, in addition to section 5, at least one claim whose slot >= the evidence day has a DIFFERENT gold final value in the two members. Consequence: any story-blind function (same output for both members) is wrong on that claim in at least one member; G9 (a) holds by construction and is verified empirically.
G9 (c) is replaced by (c'): accuracy of every story-blind attacker on the pair-differential claims (claims whose gold final value differs between members), pooled over both members, has upper 95% CI <= 0.55.
Feasibility recount under the amended validator (3,000 samples, counts only): equal-depth pairs per depth 0/1/2/3/4 = 38/220/337/57/5; category transitions (S1,S2): blocked<->resolving 1,014, resolving<->resolving 981, blocked<->blocked 208, resolving<->irrelevant 124, other 8. Depth 4 is rare (about 5 pairs per 3,000 samples) but reachable by drawing more candidates; no grammar extension.
Consequences stated now: (i) main test pairs mostly contrast "event applies" vs "event is blocked by a world law" or two different applied results; irrelevant-evidence items are rare in the pair set, so preservation is measured through the unchanged claims inside every item (collateral edit rate), and irrelevant evidence appears in the transform and dev/train data only; (ii) K2 (no laws stated) uses only pairs where neither member is blocked, so its n is smaller and is reported with its own n and compared to K1 on exactly the same pairs.
