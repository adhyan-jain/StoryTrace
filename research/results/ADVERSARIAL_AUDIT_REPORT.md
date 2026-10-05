# SSR-Bench adversarial audit and selective-revision phenomenon (2026-10-03)

**Status: CONDITIONAL.** The phenomenon survives every control run; the condition is that v1 cannot support a validity claim (story-blind solver at 0.933) and needs the pre-registered ledger-blind v2 before any paper claim. (Final line repeats this.)
Protocol: `research/PREREGISTRATION.md` Addendum C (decision rules fixed before any number below was computed). Analysis only: the benchmark
definition and data are byte-identical to the audit start (`results/snapshot_2026-10-02/BENCHMARK_HASHES.txt`, enforced by `tests/test_adv_integrity.py`).
No method implemented, no prompt tuned. GPU used only for the p2 re-run on transformed sets (Ollama, user-approved, 100% GPU placement checked per model). Every number below comes from `results/adv/*.json` or `results/BASELINE_REPORT.md` (regenerable; see Reproduce).

## What was and was not run
| item | status |
|---|---|
| existing pipeline: G1-G8 leakage gates, attackers, deep_analysis, analyze, 28 existing tests | run, all pass (34 tests with the 6 new ones) (G1-G8 `ALL_GATES_PASS: true`) |
| 11 new non-LLM attackers + references, all 9 splits | run (`adv/attacker_results_orig.json`) |
| 7 transformed sets (entity permutation same/cross pool, lexical paraphrase, novel templates, claim-order, story-order, matched pairs); gold recomputed by both oracles, invariances asserted | built and attacker-evaluated |
| scoring audit S1-S5 on all raw LLM outputs, equivalence-class facts, 60-item manual adjudication | run |
| attacker-vs-LLM gap, error overlap, balanced delta-size strata | run |
| LLM p2 x 4 models on the 7 transformed sets plus the identity control (4,408 calls, 0 errors, all models 100% GPU) | run (`adv/LLM_TRANSFORMS.md/json`) |
| rule-paraphrase prompt variants | not built (only useful together with the LLM runs) |
| pair-level flip accuracy for LLMs on matched pairs | run |

## Headline numbers
Value-aware delta-EM on `test_id` (full split, 300 items, story-cluster bootstrap 95% CI): **ledger_lookup 0.933 [0.907, 0.957]** (preservation 0.991, revision recall 0.962, conflict recall 1.000),
always_keep 0.333, symbolic 1.000. Best LLM condition (p2): qwen2.5 0.200, llama3 0.033, qwen3 0.013, mistral 0.013 (`BASELINE_REPORT.md`).
`ledger_lookup` reads ONLY the evidence sentence (parsed with the train-pool regex grammar) and the ledger's prior values. It never reads the story and never replays the world
(`test_ledger_lookup_never_reads_the_story` blanks the story and asserts identical output).

### Attackers, label-exact item rate, LLM subsample (150 items test_id; 60 per OOD split), p2 for models
| split | ledger_lookup | positional | template_nn | qwen2.5 | llama3 | qwen3 | mistral | always_keep | symbolic |
|---|---|---|---|---|---|---|---|---|---|
| test_id | 0.927 | 0.407 | 0.433 | 0.207 | 0.033 | 0.013 | 0.013 | 0.333 | 1.000 |
| test_ood_lex | 0.333* | 0.367 | 0.333 | 0.117 | 0.067 | 0.000 | 0.017 | 0.333 | 0.333* |
| test_ood_ent | 0.933 | 0.433 | 0.433 | 0.183 | 0.050 | 0.033 | 0.000 | 0.333 | 1.000 |
| test_ood_struct | 0.950 | 0.417 | 0.550 | 0.217 | 0.033 | 0.017 | 0.000 | 0.333 | 1.000 |
| test_ood_nonlinear | 0.950 | 0.383 | 0.367 | 0.100 | 0.067 | 0.000 | 0.017 | 0.333 | 1.000 |
| test_ood_length | 0.900 | 0.383 | 0.383 | 0.200 | 0.050 | 0.017 | 0.017 | 0.333 | 1.000 |
| test_ood_distract | 0.950 | 0.400 | 0.450 | 0.167 | 0.033 | 0.000 | 0.017 | 0.333 | 1.000 |
| test_ood_evorder | 0.900 | 0.400 | 0.417 | 0.250 | 0.083 | 0.017 | 0.017 | 0.333 | 1.000 |
| test_challenge | 0.967 | 0.383 | 0.633 | 0.217 | 0.050 | 0.000 | 0.017 | 0.333 | 1.000 |

\* parser failure only: the evidence regex grammar was built from train templates. With the held-out grammar (`ledger_lookup_priv`) it scores 0.943 on `test_ood_lex` and 0.927 on the lexically paraphrased `test_id` worlds.
It scores 0.333 on `novel_templates` even with both grammars (unparseable), i.e. its success is a parsing dependence, not semantic content.

Other attackers on `test_id` (full split): positional 0.417 [0.378, 0.450], template_nn 0.383 (label-level 0.450), triple_aware 0.390, category_then_select 0.317, lexical_overlap 0.317, entity_blind 0.323 (chance 0.333), claim_count_prior 0.090, mention_rule 0.000.
Diagnostic only (uses gold n_changed and category): delta_size_oracle 0.587 (label-level 0.753).
World-rule ablation ladder of the symbolic parser (`test_id`): all rules 1.000; no injury rule 0.947; no travel 0.943; no preconditions 0.720; no persistence 0.587.
Transformations (attackers, `test_id` subsample, label-exact vs identity re-realisation 0.927): entity permutation same-pool 0.927, cross-pool 0.927, claim-order 0.927, story-order 0.927 for ledger_lookup (no effect); lexical paraphrase and novel templates 0.333 (parser).

## Answers

### 1. Is the benchmark valid?
**Internally yes; as a measure of story-grounded state tracking, no.**
- Gold is computed, not typed: two independently written oracles agree on 100% of items (G8), property tests pass, `identity` re-realisation reproduces every gold label and every ledger exactly (150/150 items), and the 6 re-realisation transforms passed their invariance assertions (matched pairs have no invariance check; they are new evidence by construction).
- Construct validity fails: a solver that never sees the story reaches 0.933 delta-EM (CI lower bound 0.907). For about 93% of items the ledger plus the one evidence sentence contain everything needed, so the benchmark mostly measures applying an update rule to a ledger, not tracking state across a narrative.
- It fails exactly where the story would be needed: ledger_lookup fails 11/150 items of the subsample (resolving 6, irrelevant 5; move 9, give 2), all of them cases where the ledger lacks the intermediate state (e.g. a later move bounds the change). That is the only slice that requires the story.

### 2. Is leakage adequately ruled out?
**No.** G1-G8 pass, and the earlier attackers stay low (text-only category macro-F1 0.47-0.58 against the 0.60 gate; per-claim F1 0.37-0.46), but the gates did not test ledger content as a solver input.
- Contradictory items are solved 100/100 and the failures above are confined to resolving/irrelevant items. This is consistent with `generate.pick_claims`, which always places the contradicted claim (and, for resolving items, the changed claims) in the ledger, so ledger composition and prior values carry the label. I did not run a separate experiment that isolates composition from values; this attribution comes from the code plus the solver's perfect contradiction score.
- `entity_blind` sits at chance and entity permutation does not change the solver, so entity names are not the channel. Residual: `template_nn` reaches 0.633 label-exact on `test_challenge` (0.433 on `test_id`), below the Addendum C threshold on `test_id` but worth a look in any redesign.
- The matched-pair construction exposed a related fact: from 50 resolving items I could build 49 irrelevant variants but only 3 contradictory ones, because a contradiction needs its conflict claim in the ledger and the ledger is fixed. Ledger composition is category-dependent.

### 3. Can a shallow non-reasoning system solve it?
**Yes, by the rule fixed in Addendum C** (non-LLM, no story replay, delta-EM >= 0.50 or claim macro-F1 >= 0.80): ledger_lookup has delta-EM 0.933 and claim macro-F1 0.966. It uses a regex parse of one sentence plus value comparisons, with no story and no world simulation.
Learned shallow attackers with no parser (positional, lexical_overlap, template_nn, triple_aware, entity_blind, category_then_select) stay between chance and 0.45 on `test_id` and none meets the rule.

### 4. Does the selective-revision phenomenon survive adversarial controls?
**Yes, on every control run, including the LLM re-runs on all transformed sets.**
- Survives: lenient scoring (Q5), balanced delta-size strata, manual adjudication, and attacker solvability (the failure is not explained by an easy-to-solve benchmark: the ledger solver succeeds on items the LLMs fail).
- Balanced strata (equal weight to irrelevant, contradictory and resolving n=1/2/3; `test_id`, label-exact): always_keep 0.200 [0.200, 0.200]; qwen2.5 0.141 [0.098, 0.189]; llama3 0.060 [0.008, 0.140]; qwen3 0.037 [0.000, 0.114]; mistral 0.008 [0.000, 0.020]; ledger_lookup 0.927 [0.885, 0.965]. On this view every LLM scores at or below the do-nothing baseline.
- Error overlap on `test_id` (p2): P(LLM fails | ledger_lookup succeeds) = 0.80 (qwen2.5), 0.97 (llama3), 0.99 (qwen3), 0.99 (mistral); McNemar p < 1e-28 for every model. The LLM failures are not concentrated in the items that need the story: on the 11 items ledger_lookup fails, the LLMs score 0.27, 0.09, 0.00, 0.00, while on the 139 it solves they score 0.20, 0.03, 0.01, 0.01.
- LLM re-runs on transformed sets (p2, 150 `test_id` items per set, 52 for matched pairs; `results/adv/LLM_TRANSFORMS.md`): delta-EM stays within the identity-control range for every model under entity permutation (same and cross pool), claim reordering, story reordering, lexical paraphrase and novel templates. Identity control: qwen2.5 0.200, llama3 0.040, qwen3 0.020, mistral 0.020. The largest change is qwen2.5 on lexical paraphrase and cross-pool renaming (-0.060 each); all others are within 0.03. No transformation lifts any model above 0.20 delta-EM, and the Addendum C survival rule (preservation CI upper < 0.97 or recall CI upper < 0.85, delta-EM < 0.9) holds on every set for all four models.
- The failure signatures are stable too: qwen3 keeps over-revising (preservation 0.49-0.57, recall 0.82-0.91), qwen2.5 keeps under-revising (preservation 0.90-0.93, recall 0.11-0.18), llama3 and mistral stay weak on both.
- Matched pairs (52 resolving items, each with a one-edit variant that flips the category; 49 irrelevant, 3 contradictory variants): both items exactly right for **1.9%** (qwen2.5), **1.9%** (llama3), **0%** (qwen3) and **0%** (mistral). Base items are right 8-10% (qwen2.5, llama3) and 2% (qwen3, mistral); variants 15%, 4%, 0%, 0%. The models do not separate a state change from a near-identical sentence that changes nothing.
- Interpretation caveat: because the ledger suffices on 93% of items, the failure is better described as "LLMs cannot reliably apply a one-sentence update to a ledger under explicit rules" than as "LLMs cannot track narrative state". The stated rules are in the prompt, so attack K (instruction following vs reasoning) stays open.

### 5. Which errors are metric artifacts vs model failures?
Scoring audit on the same raw outputs (`results/adv/scoring_audit.json`; p2, `test_id`, delta-EM under the strict scorer S0 and under all lenient rules combined SALL, plus the share of S0 failures that SALL rescues, story-cluster 95% CI):
| model | S0 | SALL | rescued share of failures |
|---|---|---|---|
| qwen2.5:7b | 0.200 | 0.313 | 0.142 [0.073, 0.211] |
| llama3:latest | 0.033 | 0.213 | 0.186 [0.141, 0.232] |
| qwen3:8b | 0.013 | 0.147 | 0.135 [0.088, 0.183] |
| mistral:7b | 0.013 | 0.047 | 0.034 [0.007, 0.067] |
- Almost all of the rescue comes from one equivalence: `REVISE: <prior value>` is the same state as KEEP (S2). It sits mainly on irrelevant items (llama3 irrelevant 0.02 -> 0.56, qwen3 0.02 -> 0.34).
- On resolving items no model exceeds 0.10 even under all leniencies together. Lenient CONFLICT (S3), INVALID tolerance (S5) and label-only scoring (S1) add little; value errors are real errors (S1 equals S0 for most models).
- The state-only view (S2b, CONFLICT treated as KEEP) is high (0.17-0.55) only because for irrelevant and contradictory items gold means "state unchanged"; it is not a rescue of resolving items.
- Manual adjudication, 60 stratified p2 `test_id` failures (5 per model x category; single annotator; labelled before seeing any automated flag): **10 artifacts (17%), 6 ambiguous (10%), 44 model failures (73%)**. All 10 artifacts are exactly the items the automated SALL flag rescues, with no false positives. Artifacts: 7 irrelevant, 2 contradictory, 1 resolving.
- The 6 "ambiguous" items all treat a contradiction as a correction (`REVISE` to the asserted value instead of `CONFLICT`). The rules in the prompt say contradictions are CONFLICT, so under the protocol this is non-compliance, but it is a defensible reading of the sentence in the real world.
- Model-failure signatures in the sample: collateral revisions of unrelated claims (qwen3, llama3), spurious CONFLICT flags on consistent claims (mistral, qwen2.5), missed revisions (qwen2.5, mistral), and failing to stop a change at the next event.

### 6. Is single-reference scoring actually inadequate?
**Partly, and it does not change the conclusion.**
- It is inadequate in one concrete way: it rejects a state-equivalent output (`REVISE` to the unchanged value). Every item has about 9.1 KEEP claims with such an equivalent form.
- The conflict reference is structurally ambiguous: on `test_id` contradictory items the mean number of ledger claims contradicted by the evidence (same attribute and entity, same constant-value interval) is 2.4, and 78% of those items have more than one. Gold accepts exactly one. In practice this barely matters (S3 rescue is small) because the models rarely flag a consistent alternative.
- Even under every lenient rule combined, the best model is at 0.31 delta-EM, far from the 0.9 level in the Addendum C failure criterion. A multi-reference or state-based scorer should be reported next to the strict one in any follow-up, but it would not rescue these models on this benchmark.

### 7. What exact research problem remains?
Whether language models revise exactly the claims whose evidential status changes when the information needed to decide that is in the story rather than readable off the ledger. Two parts:
- (a) a benchmark where the ledger neither reveals which claims matter nor carries the prior state needed to resolve preconditions, so that story-state tracking is required;
- (b) the observed failure even where the ledger suffices: why 7-9B models produce spurious CONFLICT flags, collateral revisions and `REVISE`-to-same-value outputs under explicit rules (instruction following vs state tracking, attack K).

### 8. What experiment must happen next?
In this order:
1. (Done) p2 x 4 models on the transformed sets: the Addendum C survival criterion holds under every transformation.
2. A pre-registered benchmark v2 (new Addendum, no edits to v1): the three items of a story share one ledger chosen before the evidence (so composition carries zero label information), prior values for the claims needed by the precondition are not shown, and a new gate G9 requires ledger_lookup and every non-replay attacker to stay at or below chance level on label-exact and contradiction detection before any LLM runs. Re-run the same 4 models with strict and state-equivalence scorers as co-primary metrics, and report the balanced-strata macro-average.
3. Include a prompt-side control for attack K (rules removed or paraphrased) and a pair-level flip-accuracy measure on minimal pairs whose ledgers are identical.

## Killed hypotheses (explicit)
| # | hypothesis | killed by |
|---|---|---|
| K1 | SSR-Bench v1 is a leakage-free test of story-grounded state revision | ledger_lookup 0.933 [0.907, 0.957] on `test_id`, 0.90-0.97 on every held-out split that its parser can read, no story access |
| K2 | The pre-registered gates G1-G8 are sufficient to certify that no shallow solution exists | all gates passed while a shallow solver exists; gates never tested ledger content |
| K3 | The LLM failure is explained by inability to track state through the story | LLMs fail 80-99% of the items a story-blind solver gets right, and are no better on the items that need the story |
| K4 | The failure is a metric artifact of strict single-reference scoring | SALL rescues 3-19% of failures; resolving items stay <= 0.10; manual sample 73% real failures |
| K5 | Entity-name, claim-count, positional or lexical-overlap shortcuts solve the benchmark | entity_blind 0.323 (chance 0.333), positional 0.417, lexical_overlap 0.317, claim_count_prior 0.090; entity permutation leaves the solver unchanged |
| K6 | Delta size (number of changed claims) explains the result | balanced-strata macro-average keeps LLMs at or below always_keep; delta_size_oracle (diagnostic) still only 0.587 |
| K7 | "No existing benchmark measures preservation of unaffected state" | killed earlier (`docs/HOSTILE_PRIOR_ART_REVIEW.md`: RippleEdits, DeltaLogic, Belief-R) |
| K8 | AGY "SSR v0" numbers and claims | killed earlier (`docs/BENCHMARK_FAILURE_AUDIT.md`) |
| K9 | The failure is an artifact of particular names, wording, claim order or narration order | p2 delta-EM for all four models stays within 0.06 of the identity control across 7 transformations; survival rule holds on every set |
Not killed, unresolved: attack K (explicit-rule following vs reasoning; the rule-paraphrase / no-rules prompt control was not built or run) and whether the failure persists on a ledger-blind benchmark (v2).

## Disclosures and limits
- LLM re-runs use the p2 prompt only (p1/p3/p4 not re-run on transforms) and one seed (temperature 0).
- Single annotator for the adjudication sample; the sample covers p2 on `test_id` only.
- Everything is synthetic-grammar data; there is no real-text evaluation.
- All models are 7-9B local Ollama models (mistral replaced gemma2 under rule B.2).
- ledger_lookup's grammar dependence means its numbers on reworded evidence are parser failures, not evidence that the ledger leak disappears.
- `deep_analysis.py`, `attackers.py`, `verify_runs.py`, `analyze.py` overwrote their untracked outputs; the only pre-audit version that differs from the current output (the Oct 1 `DEEP_ANALYSIS.md`) and the benchmark hashes are in `results/snapshot_2026-10-02/`.
- Nothing has been committed.

## Reproduce
```
source venv/bin/activate
python -m research.ssr_bench.leakage ; python -m research.ssr_bench.attackers ; python -m research.ssr_bench.deep_analysis
python -m research.ssr_bench.adv.run_attackers          # attacker_results_orig.json
python -m research.ssr_bench.adv.transforms             # results/adv/data/*  (never data/)
python -m research.ssr_bench.adv.scoring_audit          # scoring_audit.json, adjudication_sample.json
python -m research.ssr_bench.adv.analyze_adv            # ADV_RESULTS.md/json
python -m research.ssr_bench.adv.run_llm                # GPU, resumable, ~3 h: p2 x 4 models on the transformed sets
python -m research.ssr_bench.adv.analyze_llm_transforms # LLM_TRANSFORMS.md/json
pytest research/tests
```
Files: `research/ssr_bench/adv/{common,attackers_adv,symbolic_ablate,transforms,novel_realize,run_attackers,scoring_audit,analyze_adv,run_llm,analyze_llm_transforms}.py`, `research/tests/test_adv_integrity.py`, `research/results/adv/`.

**CONDITIONAL**
