# Test Suite Audit

## Baseline

`python3 -m pytest -q` → **115 passed, 0 failed**, before and after this cleanup pass's deletions (`tests/benchmark/`, `tests/unit/test_llm.py` — both already excluded from collection via `pytest.ini`, so removing them changed the collected count by exactly zero).

## Test files and rough per-file test-function counts

| File | Layer | Test functions |
|---|---|---|
| `tests/unit/test_auth_api.py` | Auth (signup/login/JWT) | 7 |
| `tests/unit/test_pipeline_correctness.py` | State extraction, entity resolution — regression suite for specific historical bugs (see `docs/HISTORY/FINDINGS.md`, `docs/HISTORY/EVAL_IMPROVEMENT_LOG.md`) | 66 |
| `tests/unit/test_pipeline_integrity.py` | `backend/pipeline/integrity.py` sanity checks | 7 |
| `tests/unit/test_projects_api.py` | Project/version API, ownership checks | 6 |
| `tests/v2/test_candidate_detector.py` | V2 `CandidateDetectorV2` | 9 |
| `tests/v2/test_enriched_extractor.py` | V2 `EnrichedExtractor` | 9 |
| `tests/v2/test_investigator.py` | V2 `InvestigationAgentV2` | 5 |
| `tests/v2/test_v2_models.py` | V2 story-state models | 5 |

(Counts are function-level, not counting pytest's parametrization expansion, which accounts for the difference from the 115 total collected.)

## Coverage by layer

- **Auth** (`backend/auth.py`): covered — `test_auth_api.py`, `test_projects_api.py`.
- **State extraction / entity resolution** (`backend/pipeline/state_extraction.py`, `entity_resolution.py`): well covered, primarily via `test_pipeline_correctness.py`'s large regression suite.
- **Pipeline integrity** (`backend/pipeline/integrity.py`): covered — `test_pipeline_integrity.py`.
- **V2 candidate detector, extractor, investigator, models** (`backend/v2/*`): covered — `tests/v2/*`.

## Genuinely untested critical paths (found, not fabricated to fill a quota)

Grepping test imports for exact module paths (not just name substrings) shows these **V1** modules — the ones actually wired into the live API per `V1_V2_BOUNDARY.md` — have **no direct unit test coverage**:

- `backend/ingestion/parsers.py` (`ScreenplayParser`, `NovelParser`, `FountainParser`, `PlainTextParser`) — no test file imports this module at all. Document parsing/ingestion is untested.
- `backend/agent/investigator.py` (V1 `InvestigationAgent`) — only the V2 equivalent (`InvestigationAgentV2`, in `tests/v2/test_investigator.py`) is tested.
- `backend/candidate_detection/detector.py` (V1 `CandidateDetector`) — only `CandidateDetectorV2` is tested.
- `backend/clickhouse/client.py` (V1 `ClickHouseClient`, the live API's DB layer) — not imported by any test file; the V2 equivalent is exercised indirectly through V2 detector/investigator tests, but V1's client itself has no dedicated tests.

This is a genuine gap: the modules actually reachable from `backend/api/main.py` in production (V1's parser, detector, investigator, ClickHouse client) are less directly tested than their V2 research-only counterparts. Reported here per the audit's instruction; **no tests were added** — adding coverage for scientific-behavior-adjacent code (the investigator/detector in particular) is exactly the kind of change this pass is instructed to flag rather than make unilaterally.

## Not touched

No tests were deleted for being "inconvenient," reorganized, or fabricated to inflate a count. The only test removal this pass was the two already-orphaned, non-collectible files documented in `DEAD_CODE_AUDIT.md`.
