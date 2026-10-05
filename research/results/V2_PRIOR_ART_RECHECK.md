# V2 prior-art recheck (searched 2026-10-03)

Method and limits (read first): web search plus page fetches. The fetch tool summarises pages with a small model, so every "not stated" below means the fetched summary did not state it; it is NOT a claim that the paper lacks it. Full texts were not read.
ReviseQA's OpenReview PDF could not be fetched (verification wall), so its row comes from the search-result abstract only. **"WorkflowJudge" was searched five ways and not found**; I did not substitute a different paper. "TRACE" names at least four different 2026 papers (ICLR self-evolving agent benchmarks; WWW'26 deep-research trajectory evaluation; and two efficiency/safety methods), none of which is a state-revision benchmark; none is treated as the intended one.
No novelty ("first") claim is made anywhere in the V2 materials.

## Close papers
| work (source) | research question | task structure | reference needed? | multiple valid outcomes? | preservation / minimality? | sequential state reconstructed? | story-dependence causally tested? | scale | domain | models | key difference from V2 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| DeltaLogic, arXiv 2604.02733 | belief revision under minimal premise edit | episode: conclusion under P, then edit delta(P), "stable or revised?" | yes (gold stable/revised) | not stated | yes: inertia, over-flip, abstention | no (explicit premise edits) | not stated | 30-episode Qwen subset reported | logic (FOLIO, ProofWriter) | Qwen 0.6B-4B, Phi-4-mini | one conclusion, no ledger, no story-blind control stated |
| ReviseQA, OpenReview Z4KBiAYXlI (abstract only) | belief revision in multi-turn logical reasoning | each turn adds/removes facts and rules | not verified | not verified | not verified | multi-turn, not narrative | not verified | not verified | logic | not verified | multi-turn logic, not narrative state |
| Belief-R, arXiv 2406.19764 (EMNLP 2024) | defeating-premise revision | premise sequences | yes | not stated | trade-off with unnecessary updates (from earlier V1 review) | no | no | - | logic | - | single conclusion |
| Agent-Diff, arXiv 2602.11224 | fair agent evaluation on enterprise APIs | code against API replicas, state-diff contract | no trace required | **yes: success = expected state change, process ignored** | not stated | not stated | partial (documentation ablation only) | 224 tasks, 9 LLMs | enterprise APIs | 9 LLMs | outcome-state evaluation that accepts alternative procedures; not a revise-after-evidence task |
| When Models Edit Too Much, arXiv 2609.04061 | over-editing in code repair | injected AST corruptions with known minimal patch | known minimal patch | partial: authors audit valid alternative fixes (17 of 100 audited) | **yes: excess Levenshtein, cognitive complexity** | not stated | no | 400 problems | code repair | frontier models incl. GPT-5.5 | closest on minimality + valid alternatives, but code domain, no narrative state |
| StateMemBench, arXiv 2608.19652 | can memory systems track evolving state | 234 multi-session scenarios, closed-pool grading | pool-based | not stated | superseded-state errors separated | not explicit | **length/cost-matched control** attributes +15 to +32 points to state structure | 234 scenarios | agent memory | DeepSeek-V4-Flash, Qwen-3.5-9B + 6 backends | has a matched control; no pair-level story dependence, no preservation per claim |
| STALE, arXiv 2605.06527 | detect invalidated memories | 400 conflict scenarios, 1,200 queries | LLM-as-judge | not stated | n/a (invalidation) | yes (sparse dialogue) | not stated | 400 scenarios | user-assistant dialogue | GPT-4o-mini, GPT-5.4, Gemini-3.1, Llama-3.3-70B, Qwen3.5 | recognition vs application gap; no story-blind control stated |
| Multi-Constraint State Tracking with Negation (MCST), ACL-SRW 2026 | maintain/update world state with negation | inventory, movement, temporal order, negation | not stated | not stated | not stated | yes | not stated | 100,847 questions, 12 domains | synthetic worlds | 14 LLMs | large synthetic state tracking; preservation, set-valued gold, pair control not stated |
| Do LMs Track Entities Across State Changes?, arXiv 2605.30233 | mechanism of entity tracking | PUT/REMOVE/MOVE operations | not stated | not stated | not stated | yes (mechanistic) | not stated | not stated | synthetic | transformer LMs | interpretability, not behaviour benchmark |
| PetriBench, arXiv 2609.19883 | reasoning over dynamic state spaces | procedurally generated Petri nets, 6 tasks, 3 difficulty levels | deterministic exact match | not stated | not stated | yes | depth/horizon controlled | 4,800 questions | Petri nets | proprietary + open-weight | typed exact answers, no revision/preservation |
| NCP-Bench, arXiv 2608.08160 | narrative commitment preservation | interactive narrator vs adversarial player | commitment audits | n/a | preservation is the point | yes (interactive) | not stated | - | interactive fiction | - | interactive adversarial, no matched story pairs |
| EnvTrace, arXiv 2511.09964 | semantic evaluation of LLM code by execution trace alignment | simulation traces | ground-truth trace | **yes: semantic equivalence by state-change alignment** | not stated | yes | not stated | - | synchrotron control code | - | semantic trace equivalence, different task |
| Also seen, not read beyond titles: BeliefShift 2603.23848, BayesBench, DERELAB 2608.30413, BeliefTrack, CodeTracer 2604.11641, WorkflowPerturb 2602.17990 | belief/opinion dynamics, defeasible reasoning, workflow metrics | - | - | - | - | - | - | - | - | - | listed so a reader can check them; no claim about them |

## Novelty-gap statement (falsifiable, provisional)
On the pages read, each ingredient of V2 appears somewhere on its own: revision with a stable-vs-revised label and over-flip (DeltaLogic), state-diff evaluation that accepts alternative procedures (Agent-Diff), minimal-edit fidelity with an audit of valid alternatives (code over-editing), a length-matched control for state structure (StateMemBench), large synthetic state tracking (MCST), and depth/horizon control (PetriBench). **None of the fetched summaries states the combination V2 tests:** (a) multi-claim revision with per-claim preservation after a single piece of narrative evidence; (b) matched story pairs whose evidence text and claim set are byte-identical and differ by one earlier event, so a story-blind solver is provably unable to get both right; (c) causal-support-size depth with a length-matched control; (d) invariant/set-valued gold; (e) an explicit rule-following vs state-reconstruction decomposition (prior-state-given, no-evidence and rule-paraphrase conditions).
This gap is narrow, it rests on summaries not full texts, and a reviewer could argue it is a recombination of known measurement ideas. It would be falsified by any paper that already reports story-blind-insufficient matched pairs plus a rule-following decomposition on a revision task. Recommended action before any paper claim: read the full texts of DeltaLogic, Agent-Diff, StateMemBench, MCST and the code over-editing paper.

## Sources
- https://arxiv.org/abs/2604.02733 (DeltaLogic)
- https://openreview.net/pdf?id=Z4KBiAYXlI (ReviseQA, search abstract only)
- https://arxiv.org/abs/2406.19764 (Belief-R)
- https://arxiv.org/abs/2602.11224 (Agent-Diff)
- https://arxiv.org/abs/2609.04061 (When Models Edit Too Much)
- https://arxiv.org/abs/2608.19652 (StateMemBench)
- https://arxiv.org/html/2605.06527v1 (STALE)
- https://aclanthology.org/2026.acl-srw.119/ (MCST)
- https://arxiv.org/abs/2605.30233 (entity tracking mechanisms)
- https://arxiv.org/abs/2609.19883 (PetriBench)
- https://huggingface.co/papers/2608.08160 (NCP-Bench)
- https://arxiv.org/abs/2511.09964 (EnvTrace)
