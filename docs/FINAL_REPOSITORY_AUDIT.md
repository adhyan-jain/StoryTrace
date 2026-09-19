# Final Repository Audit

Final quality pass on StoryTrace V2 ahead of VIT IPR review, paper authoring, and eventual controlled release. All work stayed local (branch `v2-development`); nothing was pushed.

## 1. Repository Health

Working tree clean, 9 local commits ahead of `origin/v2-development`, 0 behind. Total repo size ~2.1G, dominated by gitignored `venv/` (539M), `apps/web/node_modules/` (718M), and `data/` (582M, mostly gitignored source corpora). Tracked content is small and organized.

## 2. Architecture Summary

Documented in `docs/ARCHITECTURE.md`, traced from actual code (not aspirational). Key fact: `backend/api/main.py`, the live FastAPI app, imports only **V1** modules; **V2** is a fully parallel, evaluation-only implementation under `backend/v2/`, exercised solely by `tests/v2/*` and `scripts/v2/*`. See `docs/V1_V2_BOUNDARY.md` for the full detail — **flagged for the user to confirm this is intentional**, since it means the scientifically validated pipeline is not (yet) what the live API actually runs.

## 3. Files Removed

- `tests/benchmark/` (5 files) and `tests/unit/test_llm.py` — confirmed orphaned, imported an unvendored `echotales` package, already excluded from pytest collection, pre-documented as dead in README.
- `docs/patent/VIT_INVENTION_DISCLOSURE_PACKAGE.md` — byte-identical duplicate of `docs/VIT_INVENTION_DISCLOSURE_PACKAGE.md` (confirmed via diff and `git log --follow`, both created in the same commit). Kept one copy at `docs/IP/`.
- `.playwright-mcp/` (~90 files) — untracked, gitignored dev-debug console logs/snapshots.

## 4. Files Moved

44 documentation files reorganized from a flat `docs/` into `docs/{RESULTS,RESEARCH,IP,HISTORY}/` via `git mv` (full mapping in `docs/FINAL_REPOSITORY_TREE.md`), plus 4 root-level dev logs (`DEVLOG.md`, `FINDINGS.md`, `EVAL_IMPROVEMENT_LOG.md`, `PIPELINE_VERIFICATION.md`) moved into `docs/HISTORY/`. `docs/architecture.md` (stale, pre-V2, duplicate-named against the new `docs/ARCHITECTURE.md`) was consolidated into the new file. `test_ri.py` relocated from repo root to `scripts/generate_ri_parsed_dataset.py` (see item 10). `docs/paper/tables.tex` moved to join the rest of the paper artifacts at `docs/RESEARCH/paper/`. Every cross-reference (README, code comments in `scripts/eval/__main__.py`, `scripts/validate_ri_pipeline.py`, `tests/unit/test_pipeline_correctness.py`, and internal doc links) was updated to the new paths.

**`EVAL_REPORT.md` was deliberately NOT moved** — `scripts/eval/__main__.py` writes it to the repo root by hardcoded relative path; moving the doc would create a stale duplicate diverging from what the script actually produces.

## 5. Files Retained as Historical Artifacts

All gold dataset, corpus manifest, raw benchmark/Green-Mile JSON, and scored-metrics files under `data/eval/` and `results/v2/` — verified present and git-clean, none modified (`docs/SCIENTIFIC_ARTIFACT_INVENTORY.md`). All patent/IP documents preserved under `docs/IP/`. All research specs/audits preserved under `docs/RESEARCH/`. `docs/HISTORY/V2_FINAL_SCIENTIFIC_STATUS.md` and `V2_FINAL_STRATEGIC_DECISION.md` were both kept (not one deleted as "superseded" by the other) — they were created ~24 minutes apart on the same freeze date but cover different concerns (scientific verdict vs. IP/publication strategy); calling one a strict supersession of the other would have been a guess, so both are preserved with that ambiguity documented.

## 6. Dead Code Findings

Full table in `docs/DEAD_CODE_AUDIT.md`. Summary: two confirmed-dead directories deleted (above); one duplicate-but-tested module (`backend/llm/provider.py`'s `get_llm_provider()`, superseded by `backend/api/main.py:_default_provider()` but still imported by `tests/unit/test_pipeline_correctness.py`) flagged for the user's decision, not deleted, since removing it would require changing test code; ablation-only `backend/eval/*` modules confirmed legitimately in-use, not dead.

## 7. Dependency Findings

Full table in `docs/DEPENDENCY_AUDIT.md`. No dependency was confidently unused; nothing removed or version-bumped. One dependency (`beautifulsoup4`) has only a single call site — worth a manual look before any future removal, not acted on here.

## 8. Security Findings

Full detail in `docs/SECURITY_AUDIT.md`. No real secrets found tracked anywhere. One stale/insecure hardcoded default fixed: `scripts/migrate_to_cloud.py`'s `password="admin"` (no longer even the real local default per `docker-compose.yml`) now reads `CLICKHOUSE_LOCAL_PASSWORD` from the environment. `.gitignore`/`.env` handling was already correct.

## 9. Documentation Changes

Full reorg as described in items 3-4. New docs added: `ARCHITECTURE.md`, `V1_V2_BOUNDARY.md`, `DEAD_CODE_AUDIT.md`, `SECURITY_AUDIT.md`, `DEPENDENCY_AUDIT.md`, `TEST_AUDIT.md`, `REPRODUCIBILITY.md`, `PATH_LOGGING_CLI_AUDIT.md`, `SCIENTIFIC_ARTIFACT_INVENTORY.md`, `FINAL_NUMBERS_SOURCE_OF_TRUTH.md`, `DOCUMENTATION_INDEX.md`, this file, and `FINAL_REPOSITORY_TREE.md`. README updated: fixed stale links, corrected the now-inaccurate echotales note, added links to the new docs.

## 10. Test Status

**114 passed, 0 failed** (final). This required a real fix, not just a count: `test_ri.py` (repo root) was a mislabeled data-generation script — no assertions, just parse-and-write logic — whose `test_*.py` name matched pytest's default discovery and was **silently executed on every `pytest` run**, writing `data/processed/ri_parsed.json` as an undeclared side effect (confirmed: this session's own pytest runs regenerated that gitignored file). Fixed by adding `testpaths = tests` to `pytest.ini` and relocating the script to `scripts/generate_ri_parsed_dataset.py`. This is a test-hygiene/config fix, not a change to any pipeline, detector, or investigator logic — no scientific behavior was touched. Coverage gap found and reported, not filled: `backend/ingestion/parsers.py`, and the **V1** `investigator.py`/`detector.py`/`clickhouse/client.py` (the modules actually reachable from the live API) have no direct unit tests — only their V2 research-only counterparts are tested (`docs/TEST_AUDIT.md`).

## 11. Reproducibility Status

`docs/REPRODUCIBILITY.md` distinguishes DEVELOPMENT / BENCHMARK / HELD-OUT corpora and gives verified commands. Commands with no dry-run mode (`scripts.eval`, `scripts.v2.*`) were verified by source inspection (argparse definitions, output paths) rather than executed, to avoid triggering unintended real pipeline/LLM runs — one such accidental trigger did occur mid-session (`python3 -m scripts.eval --help`, which has no `--help` support and began a live run) and was caught and killed within seconds, before any LLM call or data write occurred.

## 12. Scientific Artifact Integrity

All gold dataset, corpus manifest, benchmark, and Green-Mile result files verified present, git-tracked, and unmodified (`docs/SCIENTIFIC_ARTIFACT_INVENTORY.md`). No result JSON, gold label, or scoring methodology was changed. One **unresolved cross-check discrepancy** is reported, not silently fixed, in `docs/FINAL_NUMBERS_SOURCE_OF_TRUTH.md`: the raw `results/v2/investigator_confusion_matrix.json` records `max_tool_calls_observed: 3`, not the canonical "max 6" figure (which matches the code's `max_calls=6` hard bound). This needs the user's judgment on whether the result JSON has a computation bug or the canonical figure was describing the code bound rather than the measured data.

## 13. Patent/IP Artifact Integrity

All IP documents preserved under `docs/IP/`, no substantive claim language changed. Only fixes made: deduping the byte-identical `VIT_INVENTION_DISCLOSURE_PACKAGE.md` copy and repointing one stale `docs/architecture.md` reference in `docs/IP/PATENT_READINESS_AUDIT.md` to the consolidated `docs/ARCHITECTURE.md`.

## 14. Remaining Warnings

- `backend/api/main.py` wires V1, not V2, into the live API (item 2) — confirm intentional.
- `backend/llm/provider.py` vs `backend/api/main.py:_default_provider()` duplication (item 6) — needs a decision.
- `results/v2/investigator_confusion_matrix.json`'s `max_tool_calls_observed` discrepancy (item 12) — needs a decision.
- Several `scripts/v2/*.py` scripts (`compare_v1_v2.py`, `audit_statistical.py`, `audit_robustness.py`, `audit_investigator.py`, `run_held_out_green_mile.py`) and `scripts/eval/score_final_experiment.py` still hardcode output paths into the old flat `docs/` location — rerunning them would recreate a stale duplicate outside the new `RESULTS/`/`RESEARCH/` tree. Left untouched (source-code behavior change, out of scope), documented in `docs/FINAL_REPOSITORY_TREE.md`.
- `data/stage/` contains its own nested `.git` — flagged, not touched.
- `backend/ingestion/parsers.py` and V1's `investigator.py`/`detector.py`/`clickhouse/client.py` have no direct unit test coverage (item 10).
- Frontend `eslint` (pre-existing, not caused by this pass, frontend untouched): 5 errors, 3 warnings — mostly React-hooks purity issues (`Cannot access ref value during render`, `setState` called synchronously in an effect). Reported for awareness only; not fixed (frontend logic change, out of scope for this pass).
- `backend/llm/base.py` deprecation: importing PyMuPDF via the legacy `fitz` alias (`backend/ingestion/parsers.py`) triggers a deprecation warning; not fixed (cosmetic, no behavior change either way, left as a minor future note).

## 15. Local Commits Created

9 commits this pass (`5b214fa` through `ff6158c`), each scoped to one concern: dead-code removal, the migration-script password fix, the audit-doc batch, the architecture consolidation, the full doc reorg, the final-numbers cross-check, the pytest-collection fix, and the `tables.tex` relocation. Full list via `git log --oneline`.

## 16. Current HEAD / Remote HEAD / Push Performed

- **CURRENT HEAD**: `ff6158c` (branch `v2-development`)
- **REMOTE HEAD**: `origin/v2-development` unchanged, 9 commits behind local
- **PUSH PERFORMED: NO**

## Final Verdict

**READY FOR**: VIT IPR review (with the two flagged decisions above surfaced first), paper manuscript authoring, future controlled public release preparation.

This is a research/patent repository, not a production deployment — "production ready" does not apply and is not claimed here. Scientific validity, IP evidence, and reproducibility were prioritized over cleanup cosmetics throughout, per instruction; every behavior-adjacent finding was flagged rather than silently resolved.
