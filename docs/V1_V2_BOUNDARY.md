# V1 / V2 Boundary

## CURRENT DEFAULT

**V2** is the validated, scientifically current pipeline. Its benchmark (commit `4064cf7`: Micro-F1 0.7821, 989 gold items, Green Mile held-out eval) is the source of truth for all patent/paper claims (see `FINAL_NUMBERS_SOURCE_OF_TRUTH.md`).

## HISTORICAL BASELINE

**V1** is the frozen baseline used for comparison (`main` @ `eab6ef63975ca906c1c615d5d69e6e03c6fd2b87`). It is not deleted or deprecated in-place — it remains the reference point V2 is measured against.

## How the split is actually implemented

This is **not** a feature-flag split inside shared files. V1 and V2 are two fully parallel package trees:

- **V1**: `backend/agent/investigator.py`, `backend/candidate_detection/detector.py`, `backend/clickhouse/client.py`, `backend/pipeline/{state_extraction,entity_resolution,integrity}.py`, `backend/story_state/{interval,models}.py`
- **V2**: `backend/v2/agent/investigator.py` (`InvestigationAgentV2`), `backend/v2/candidate_detection/detector.py` (`CandidateDetectorV2`), `backend/v2/clickhouse/client.py` (`ClickHouseClientV2`), `backend/v2/pipeline/*` (`EnrichedExtractor`, etc.), `backend/v2/story_state/*` (`CandidateConflictV2`, etc.)

No shared file branches internally on a V1/V2 flag — every V2 symbol is a distinctly named class/module in its own `backend/v2/` subtree.

## Flagged fact — confirm before relying on it

**`backend/api/main.py` (the live FastAPI app) imports only V1 modules.** A grep for `backend.v2` in `backend/api/main.py` returns zero matches — it imports directly from `backend.agent.investigator`, `backend.candidate_detection.detector`, `backend.pipeline.entity_resolution`/`state_extraction`, and `backend.clickhouse.client`.

This means: **the deployed/live API currently runs V1's pipeline, not V2's**, even though V2 is the scientifically validated and reported pipeline. V2 is exercised exclusively by:
- `tests/v2/*` (candidate detector, extractor, investigator, model unit tests)
- `scripts/v2/*` (`run_v2_eval.py`, `run_held_out_green_mile.py`, `score_v2_experiment.py`, `compare_v1_v2.py`, `audit_candidate_recall.py`, `audit_investigator.py`, `audit_robustness.py`, `audit_statistical.py`)

This was left as-is per the plan's guardrail against behavior-changing edits — wiring V2 into `main.py` would change live application behavior and is out of scope for a documentation/cleanup pass. **The user should confirm whether this is intentional** (e.g., V2 is still eval/research-only and not yet promoted to the live API) or whether it's an oversight that should be tracked as a follow-up engineering task.

## REPRODUCTION ONLY

The following exist solely to reproduce/compare historical results and are not part of any live execution path:
- V1 benchmark/scoring artifacts referenced by `scripts/eval/*` (non-`v2` scripts): `run_eval.py`, `report.py`, `compute_metrics.py`, `run_ablation.py`, etc., scored against `data/eval/golden_dataset.py`
- `scripts/v2/compare_v1_v2.py` and its inputs (`data/eval/v2/v1_vs_v2_comparison.json`) — the direct V1-vs-V2 comparison artifact for the paper
- One-off historical experiment scripts (`scripts/eval/run_final_research_experiment.py`, `run_scream2_and_build_report.py`, etc. — see `DEAD_CODE_AUDIT.md` category C)

None of these were modified, rerun, or deleted in this pass.
