# SSR-Bench design log (every iteration, including failures)

## Iteration 1 (2026-10-01) — FAILED gates G1, G2
First full generation, tuned only on distribution inspection of test_id (no shallow attacker had been run).
Leakage run: G3-G8 passed. **G1 failed**: text-only macro-F1 0.46-0.82 (limit 0.60) on all splits except ood_lex. **G2 failed**: 0.40-0.49.
Cause (train split): evidence *family* was confounded with category — give/pickup/drop evidence is ~always contradictory
(random candidates are rarely valid), move/injure ~always resolving, noop/assertion never resolving; contradictory evidence is longer.
Fix: sample evidence by (category, family) with near category-independent family weights using state-aware recipes; add
"injured characters cannot move" precondition so moves can be contradictory (both oracles updated).

## Iteration 2 (2026-10-01) — G1 passes (max 0.593 on test_ood_ent, tight), G2 still FAILS (0.42-0.45 vs 0.40)
Family-balanced sampling + "injured cannot move" precondition (both oracles). G3-G8 still pass.
Cause of G2: evidence length — contradictory evidence 43.7 chars / 8.7 words vs 37-38 / 7.5 for resolving & irrelevant.
Fix: per-split balanced rejection on evidence word-count bins so the length distribution is equal across categories.

## Iteration 3 (2026-10-01) — length balancing: G2 now 0.27-0.41; ONE nominal G2 failure (test_ood_nonlinear 0.409 vs 0.40); G1, G3-G8 pass
Mean G2 over splits ~0.34 (chance 0.333). With 120 items per OOD split the best-of-two attacker statistic has SD ~0.035, so a 0.409 is
~noise (max over 9 splits). Thresholds are NOT changed. Redesign = more statistical power: all OOD/challenge splits enlarged from 40 to 100 stories (300 items).
LLM stage will use a fixed, seeded subsample (declared before any model run).

## Iteration 4 (2026-10-01) — ALL PREREGISTERED GATES PASS (research/results/leakage_report.json)
G1 text-only 0.47-0.58 (<=0.60); G2 meta-only 0.30-0.39 (<=0.40); G3 per-claim shallow F1 0.40-0.46 (<=0.70), mention-rule F1 0.27-0.31;
G4 p=0.45; G5 no gold words/keys in task files; G6 >=0.95 distinct (all 1.0); G7 splits disjoint; G8 oracles A==B on 100% of items.
Property tests (hypothesis, 400 random worlds x 3 pools) + hand fixtures + isolation test: research/tests (16 pass).
Caveat to carry into the paper: text-only attacker reaches ~0.5 macro-F1 (chance 0.33) — residual *semantic* cues (e.g. "yawned" is
irrelevant by meaning). Not removable without removing the distractor class.

## Prompt iteration 1 (dev split only) — value vocabulary
qwen2.5:7b dev smoke (4 stories/12 items): revision P/R = 0.0 for P1/P2/P3. Inspection of raw outputs showed the pipeline is correct but the
prompts did not specify the value vocabulary (model wrote "floor" for a put-down prop; gold value is "nobody"). Fix: all prompts now state the
value domain. Superseded dev smoke outputs deleted (dev only, never used for any reported number).
