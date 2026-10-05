# SSR-Bench pre-registration (written 2026-10-01, BEFORE any leakage number or LLM result was computed)

Status of the benchmark at the time of writing: generator, two oracles, lexicon, realiser exist; oracle A and B agree on every
generated item (checked at generation time). No shallow-classifier or LLM result had been looked at.

## Leakage gates (all must pass on `test_id` and on every OOD split before any LLM is run)
Shallow attackers are trained on `train` only and evaluated on held-out splits. The best of {logistic regression,
gradient boosting / random forest} is taken per gate (strongest attacker).

| Gate | Attacker input | Target | Pass condition |
|---|---|---|---|
| G1 | evidence text only (word 1-2-grams) | evidence category (3 classes, balanced) | macro-F1 <= 0.60 (chance 0.33) |
| G2 | metadata only (evidence length, word count, punctuation counts, evidence slot, #story sentences, story length) | evidence category | macro-F1 <= 0.40 |
| G3 | per-claim features (attr, slot - evidence slot, entity mentioned in evidence, ledger position, evidence n-grams) | claim changed (REVISE/CONFLICT) vs KEEP | positive-class F1 <= 0.70 |
| G4 | ledger position of a claim | claim changed | no association (chi-square p > 0.01) |
| G5 | exposure | task files contain only whitelisted keys; no gold words (RESOLVING/IRRELEVANT/CONTRADICTORY/KEEP/REVISE/CONFLICT) anywhere in task files | exact |
| G6 | distinctness | delexicalised (story, evidence, label-pattern) items | >= 0.95 unique per split |
| G7 | split disjointness | OOD-lex templates, OOD-ent entities, OOD-struct signatures vs train/dev/test_id | empty intersection |
| G8 | oracle agreement | all items, recomputed from stored world | 100% |

If any gate fails: the benchmark is redesigned (using train/dev only for tuning) and ALL gates re-run; no LLM run starts.
Every redesign iteration is logged in `research/results/design_log.md`, including failures.

## Baseline-failure criteria (fixed now, for the LLM stage)
"Systematic selective-revision failure" is declared only if, for a given model on `test_id`, BOTH hold:
1. preservation accuracy (KEEP claims kept) 95% CI upper bound < 0.97 OR revision recall 95% CI upper bound < 0.85, and
2. the failure is not explained by the strongest non-LLM baseline already reaching delta-EM >= 0.9 (benchmark too easy).
Otherwise the report states "no systematic failure found" and the project does not proceed to a method.

## Addendum A (2026-10-01, before any test-split model run): LLM stage protocol
- Prompts frozen (sha256 recorded in every raw record). Dev smoke (qwen2.5:7b, 10 stories) was the only prompt iteration; logged in design_log.md.
- Models (local Ollama only, per project rule): qwen2.5:7b, llama3:latest, qwen3:8b (think=False). Frontier/hosted models are NOT used (project rule: no Vertex/Gemini unless explicitly requested).
- Conditions: p1_zero_shot_delta, p2_explicit_revision (3-shot from train), p3_regenerate (full-state regeneration, labels by diff), p4_self_consistency
  (p2 prompt, k=5, T=0.7, per-claim majority, ties->KEEP; test_id only), p5_direct_qa (probe question only, no ledger); non-LLM: always_keep, symbolic
  (train-grammar parser + own replay), symbolic_privileged_grammar (ceiling; ood_lex only).
- Subsample (fixed, seeded by sha256(story_id)): test_id 50 stories (150 items), every other test split 20 stories (60 items). Unit of analysis = story.
- temperature 0, seed 0, num_ctx 6144 (greedy conditions).
- Pre-declared contrasts (Holm over the family, per model): p2 vs p1, p3 vs p1, p4 vs p2 on test_id for {delta_exact_match, preservation_accuracy, revision_recall}.
- Interpretation note on failure criterion 2 (written before results, to remove ambiguity): "strongest non-LLM baseline" means shallow/rule baselines (always_keep,
  mention rule). The symbolic parser is reported separately as a grammar-aware reference; if it reaches delta-EM ~1.0 that shows the gold is solvable/consistent, and is
  reported as a limitation (synthetic grammar), not as grounds to suppress LLM results.

## Addendum B (2026-10-01 23:5x IST, before any analysis of full results): add a model from a different family
Motivation: qwen2.5 and qwen3 share a lineage; their failures may be correlated. gemma2:9b (Google; already pulled locally) is added as a 4th model.
- Pure addition: the model set {qwen2.5:7b, llama3:latest, qwen3:8b} and every rule above are unchanged; no model is dropped or swapped.
- Same frozen prompts, subsample, conditions (p1-p5) and settings. No prompt tuning for gemma2.
- Disclosure: before this addendum I looked at partial qwen2.5:7b p1 raw outputs on test_id (4 irrelevant items) to debug a suspicious 0.000 distractor-invariance
  value (it was genuine model behaviour: spurious CONFLICT flags). No model-selection decision depended on it.
- Criterion 1 is evaluated per model; the overall verdict is reported per model and as "any model / all models", with no model excluded afterwards.

### Addendum B.1 (same day, before gemma2 has produced any output): fit rule
The 4th model must run 100% on the GPU (`ollama ps` PROCESSOR = "100% GPU") so that speed/precision are comparable with the other models.
If gemma2:9b loads with any CPU offload, it is stopped, its partial outputs are deleted and not analysed, and mistral:7b (different family, ~4.4 GB) is used instead
with the identical protocol. This rule is fixed now and does not depend on any result. Only one of the two is analysed as the 4th model.

### Addendum B.2 (2026-10-02 ~15:30 IST): fit rule triggered
gemma2:9b loaded as "14%/86% CPU/GPU" (8.8 GB, `ollama ps`), violating B.1. It had produced p5 (630), p1 (630) and p2 (585) records; per B.1 these were
stopped and DELETED UNANALYSED (no metric was computed on them). mistral:7b (digest 6577803aa9a0) is the 4th model, identical protocol.

## Addendum C (2026-10-02, written BEFORE any adversarial-audit number was computed): adversarial audit protocol
Disclosure: baseline results (BASELINE_REPORT.md, all 4 models) were already seen. No attacker below, no transform, no alternative scorer had been run.
Scope: analysis only. The benchmark definition (generate/world/oracles/realize/lexicon, data/, manifest) is NOT modified (hashes in results/snapshot_2026-10-02/BENCHMARK_HASHES.txt, enforced by a test). No method is implemented. No prompt is tuned.
GPU use: LLM re-runs on transformed sets (p2 x 4 models, test_id subsample) happen only after explicit user approval for GPU time.

Attackers (non-LLM, per-claim label+value outputs, trained on train/dev only): majority_prior, claim_count_prior, mention_rule, positional, lexical_overlap, delta_size, entity_blind, template_nn, triple_aware, ledger_lookup (task fields only, no story replay), world_rule_partial (ablation ladder of the symbolic parser). References: always_keep, symbolic, symbolic_privileged_grammar.
Transforms (gold recomputed by both oracles, invariance asserted): entity_permute, lexical_paraphrase, rule_paraphrase, claim_order_random, balanced_delta_sizes, novel_templates, matched_pairs.
Alternative scorers (reported next to, never instead of, the headline metric): S1 label-only, S2 state-equivalence, S3 lenient CONFLICT, S4 probe answer, S5 INVALID-tolerant.

Decision rules (fixed now):
- "Solvable without semantic reasoning": any non-LLM attacker that does not replay the story (everything except symbolic*) reaches delta-EM >= 0.50 on test_id, OR claim-level macro-F1 >= 0.80, OR matches >= 50% of the best LLM's preservation AND recall while exceeding it on delta-EM.
- "Phenomenon survives": for the best LLM condition per model, preservation CI upper < 0.97 or recall CI upper < 0.85 on every transformed set, delta-EM < 0.9, and no attacker meets the rule above.
- "Metric artifact": an error that vanishes under >=1 lenient scorer AND is state-equivalent to gold by oracle replay. "Model failure": persists under all. Residue = "ambiguous".
- Final status: GREENLIGHT / CONDITIONAL / KILL, with every killed hypothesis listed.
