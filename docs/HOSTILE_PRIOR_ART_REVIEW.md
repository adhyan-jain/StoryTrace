# Hostile prior-art review (2026-10-01)

Method: each paper below was opened (arXiv abstract page via fetch, or search result page) and the answers are taken from what that page states.
**"Not stated" means the page I read does not say it; it is NOT a claim that the paper lacks it.** I did not read full texts, so every
"does not do X" below is provisional until the full paper is checked. No novelty ("first", "no prior work") claim is made anywhere in this repo.

| Work (verified source) | Task | Representation | Preservation of unaffected content | Controlled interventions | Narrative | Temporal scope | Overlap with ours |
|---|---|---|---|---|---|---|---|
| **DeltaLogic**, Dhanda, arXiv 2604.02733 (Apr 2026) | after a minimal premise edit δ(P), should the earlier conclusion stay or be revised | premise sets from FOLIO / ProofWriter; one conclusion | abstract frames "stable or revised"; reports **over-flip** (revising under an irrelevant edit) and **inertia** | yes: minimal premise insert/delete/replace | no (logic problems) | pre/post edit only | **Closest**: same "revise exactly what the edit warrants, leave the rest stable" idea, one conclusion instead of a multi-claim ledger |
| **RippleEdits**, Cohen et al., TACL 2024 (arXiv 2307.12976) | knowledge editing: do edits propagate | KB facts | **Preservation** + Relation-Specificity criteria (unrelated facts unchanged) | yes: 5K edits | no | no | same *evaluation idea* (propagate to dependents, preserve unrelated) in parametric editing |
| **Belief-R**, Wilie et al., 2024 (arXiv 2406.19764; EMNLP 2024 per search listing) | revise a conclusion given a defeating premise | premise sequences (modus ponens/tollens) | abstract: models that revise well often falter when no update is needed (i.e. over/under-revision trade-off) | yes | no | no | revision vs. non-revision, single conclusion |
| **PASTA**, Mitra et al. (TACL 2023, arXiv 2208.00329) | participant states in stories; counterfactual state → revised story | story + state text | not stated | counterfactual state perturbations | **yes** | no | narrative states and counterfactual revision; state tuples per participant |
| **PragWorld**, Vashistha et al., arXiv 2511.13021 | local world model under minimal linguistic alterations | dialogues, yes/no questions | not stated | minimal alterations (7 types) | dialogue | no | minimal-alteration protocol, entity tracking |
| **CICM / "When Context Changes"**, Guo et al., arXiv 2609.38866 (Sep 2026) | stale binding: using old vs updated values | variable updates in logs | measures that a fix preserves initially-correct answers | controlled | no | update order | update-failure phenomenon, mechanism work |
| **STALE**, Chao et al., arXiv 2605.06527 (May 2026) | detect memories invalidated by later observations (implicit conflict) | agent memory scenarios | not stated | expert-validated scenarios | no | yes (later invalidates earlier) | implicit conflict; 400 scenarios |
| **STAGE**, arXiv 2601.08510 | evolving-story reasoning over screenplays: character tracking, cross-scene evolution | KG / QA / role-play | not stated | no | **yes** (151 screenplays) | across scenes | narrative state evolution, naturalistic data |
| **NCP-Bench**, ICML 2026 (arXiv 2608.08160) | narrator must preserve established facts/commitments while a player pushes | YAML facts/commitments | the *point* is commitment preservation, via conflict audits | adversarial player | **yes** (interactive) | turn order | fact preservation in narratives, different protocol |
| **ConStory-Bench**, Findings of ACL 2026 (arXiv 2603.05890) | consistency errors in long story *generation* | free text, 5 error classes / 19 subtypes | n/a (detects contradictions) | no | yes | timeline errors | contradiction detection in generated stories |
| **NarraBench**, EACL 2026 (arXiv 2510.09869) | taxonomy of narrative tasks + survey of 78 benchmarks | taxonomy | n/a | n/a | yes | n/a | landscape; says only 27% of narrative aspects are well covered (snippet) |
| **DeepRewind**, arXiv 2609.36344 (Sep 2026) | premature commitment / rollback in deep-research agents | typed epistemic graph | dependency-aware rollback | no | no | n/a | method-side overlap for "dependency-aware revision"; different domain |
| *Not opened:* Entity Tracking in LMs (Kim & Schuster ACL 2023), AGM belief revision (minimal change), TRIP/ProPara/OpenPI | | | | | | | background; AGM *minimal change* is the formal ancestor of "preserve unaffected" |

## What this does to AGY's claims
- "No existing benchmark measures preservation of unaffected state" — **false as stated**: RippleEdits (Preservation), DeltaLogic (over-flip), Belief-R (unnecessary-update trade-off), CICM all measure some form.
- AGY's wrong venues/authors are listed in `docs/BENCHMARK_FAILURE_AUDIT.md` §7.

## The ten questions, for the closest works
| | same task? | structured state | evaluates Δ | evaluates preservation | controlled interventions w/ semantic gold | separates resolving/irrelevant/contradictory/temporal | nonlinear order | rev-P and rev-R separate | preservation measured | contains our method |
|---|---|---|---|---|---|---|---|---|---|---|
| DeltaLogic | partly | no (1 conclusion) | no | over-flip | yes | partly (insert/delete/replace) | no | not stated | yes (over-flip) | no |
| RippleEdits | analogous | KB triples | per-query | yes | yes | partly | no | no | yes | no |
| Belief-R | partly | no | no | trade-off | yes | partly | no | no | partly | no |
| PASTA | no | yes | story revision | no | counterfactual | no | no | no | no | no |
| STAGE / NCP-Bench | no | graph / YAML | no | commitments | no / adversarial | no | no | no | partly | no |

## Attacks A–T (verdict after this work)
- **A/B belief revision / Belief-R on stories — VALID in part.** DeltaLogic and Belief-R cover the principle. Defence is only the multi-claim, value-aware, temporally scoped ledger setting — an *evaluation-design* contribution, not a new principle.
- **C state tracking / D consistency / E contradiction detection — PARTIAL.** Contradiction is one of three evidence types here and is scored as conflict-on-the-right-claim; the others differ.
- **F counterfactual evaluation — PARTIAL**, the interventions are counterfactual edits by construction.
- **G Δ-metric is accuracy in disguise — PARTIAL.** Delta-EM is claim-level exactness; the final-answer-vs-Δ experiment tests whether it differs from QA (results below).
- **H benchmark generated from the same grammar as a solver — VALID.** A symbolic parser with the train grammar scores delta-EM 1.0; it fails (0.33) on held-out paraphrases. The benchmark measures LLM behaviour on a synthetic grammar, nothing more.
- **I label leakage — TESTED.** Shallow attackers: text-only macro-F1 up to ~0.58 (chance 0.33), claim-level F1 ≤ 0.46; residual cues are semantic (e.g. "yawned"). Not eliminated.
- **J credit for changing unrelated state — ADDRESSED by value-aware claim-level scoring + collateral rates.**
- **K instruction following vs reasoning — OPEN.** Prompts state the world rules explicitly; failures may reflect rule-application, not reasoning.
- **L rule baseline — TESTED**: always-keep and entity-mention rules are weak (see report); a grammar-aware symbolic parser is perfect.
- **M structured input advantage — ADDRESSED**: all conditions receive the identical ledger.
- **N domain-independent phenomenon — VALID.** Nothing here is narrative-specific beyond the surface text; the paper must not claim narrative-specific insight unless the temporal/nonlinear/dependent results show it.
- **O synthetic too artificial / P real data has no ground truth — VALID, unaddressed.** No real-text evaluation exists in this repo.
- **Q significance from n / R tuned on test — ADDRESSED**: story-clustered bootstrap, Holm; prompts tuned on dev only, gates pre-registered.
- **S/T engineering, extra representation — N/A**: no method is proposed.
