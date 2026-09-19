# Path Sanity, Logging/Error-Handling, and CLI Inventory (Phases 11–13)

## Phase 11 — Path / import / execution sanity

Searched `backend/`, `scripts/`, `tests/`, `apps/web/src/` for hardcoded absolute paths and import-time side effects.

- **Hardcoded paths**: exactly 2 matches, both benign — `scripts/v2/compare_v1_v2.py:281-282`, `file:///home/adhyan/Desktop/StoryTrace/...` links embedded in a *generated Markdown report string* (not executed code, not a runtime dependency). No `/Users/` matches anywhere. Confirms prior reconnaissance.
- **Import-time side effects**: none found. Checked `backend/clickhouse/client.py`, `backend/agent/investigator.py`, `backend/agent/tools.py`, `backend/pipeline/state_extraction.py`, `backend/candidate_detection/detector.py`, `backend/llm/provider.py` for module-level DB connections, network calls, or client instantiation. Only module-level statement of note is `load_dotenv()` in `backend/clickhouse/client.py` — reads local `.env`, does not connect to anything at import time. No database connections or model calls happen at import time; all are deferred into functions/methods.
- **OS-specific assumptions**: none found in the scanned Python/TS sources.

**Verdict**: repository is safe to import/use from a clean checkout on any OS; no action needed.

## Phase 12 — Logging / error-handling review

Reviewed `backend/agent/investigator.py`, `backend/clickhouse/client.py`, `backend/pipeline/state_extraction.py`, `backend/candidate_detection/detector.py` for swallowed exceptions, unhandled malformed-LLM-output cases, and secrets in logs.

- **`backend/agent/investigator.py:293`** — `except Exception: suggested_fix = ""` around the `_suggest_fix` call. Has an explanatory comment: `_suggest_fix` already catches its own internal errors, but a real run hit a `google-adk` `429 RESOURCE_EXHAUSTED` that escaped its own try/except and crashed the investigation; `suggested_fix` is a non-scientific UI nicety, never worth losing a correct verdict over. **Does not affect verdict/status/confidence** — only the optional "suggested fix" sentence. Intentional and documented, but the underlying exception is discarded without a log line (no `logger.warning`), so repeated `_suggest_fix` failures would be invisible in production logs. **Flagged as a minor observability gap, not a correctness bug** — not fixed here since it touches investigator code.
- **`backend/agent/investigator.py:441, 448`** — two more `except Exception` blocks inside `_suggest_fix` itself: one falls through from the ADK path to a plain-provider retry (`pass`, with a comment), one returns `""` on final failure. Same category as above — affects only the optional fix-suggestion text, not verdict correctness. Not logged either.
- **`backend/clickhouse/client.py:234-243`** (`_retry_call`) — `except Exception as e: if attempt == max_retries - 1: raise` — this is a proper retry-with-reraise pattern, not a swallow. Exception `e` is bound but unused on non-final attempts (no log line per attempt) — a very minor observability nit, not a defect.
- **`backend/pipeline/state_extraction.py`** — `except LLMError as exc` and `except Exception as exc` (lines 763/766, 1018/1024) both have comments (`# provider/parse failure of any other kind`) and, per surrounding code, propagate/record the failure rather than silently discard it (not swallowed — did not modify, verified by reading surrounding context).
- **`backend/candidate_detection/detector.py`** — no exception handling present in this file at all (pure SQL-window-function query construction); no findings.
- **Secrets in logs**: no `logger`/`print` statements found concatenating credential-like variables (`password`, `token`, `api_key`) in any of the four files.

**Overall verdict**: no exception is silently swallowed in a way that could alter a verdict, score, or metric. The three `except Exception` blocks in `investigator.py` all target the optional "suggested fix" text specifically, are commented, and are deliberate. The only real gap is missing log lines on those discarded exceptions — flagged for the user's awareness, **not changed**, since touching investigator.py is scientific-behavior-adjacent and out of scope for a cleanup pass without explicit confirmation.

## Phase 13 — CLI entrypoint inventory

**Primary supported entrypoints** (referenced by README.md):
- `python3 -m scripts.eval` (`scripts/eval/__main__.py`) — runs the full V1 eval; supports `--v2` flag to switch to `golden_dataset_v2`/`controlled_test_v2.txt` for the overfitting check, writes `EVAL_REPORT.md`/`EVAL_REPORT_V2.md`, exits 1 if F1 < 0.6.
- `scripts/v2/run_v2_eval.py` — V2 benchmark runner.
- `scripts/v2/run_held_out_green_mile.py` — Green Mile held-out evaluation runner.
- `scripts/v2/compare_v1_v2.py` — V1/V2 comparison report generator.
- `scripts/v2/score_v2_experiment.py`, `scripts/v2/audit_statistical.py`, `scripts/v2/audit_investigator.py`, `scripts/v2/audit_candidate_recall.py`, `scripts/v2/audit_robustness.py` — the V2 statistical/audit suite backing the frozen numbers in `docs/RESULTS/` and `docs/IP/`.

**Reproducibility/annotation-support entrypoints** (category B — needed for gold-dataset methodology, not one-off):
`scripts/eval/adjudicate_gold_dataset.py`, `scripts/eval/annotate_llm_pass.py`, `scripts/eval/build_annotation_template.py`, `scripts/eval/validate_gold_dataset.py`, `scripts/eval/compute_iaa.py`, `scripts/eval/compute_metrics.py`, `scripts/eval/audit_candidates.py`, `scripts/eval/fetch_stage_screenplay.py`.

**Historical / one-off research-run scripts** (category C — preserve for provenance, not part of the supported reproduction path, do not delete):
`scripts/eval/run_final_research_experiment.py`, `scripts/eval/run_one_film_preflight.py`, `scripts/eval/run_real_screenplay_validation.py`, `scripts/eval/run_scream2_and_build_report.py`, `scripts/eval/score_final_experiment.py`, `scripts/eval/run_ablation.py`, `scripts/eval/run_model_comparison.py`, `scripts/eval/one_shot_baseline.py`, `scripts/eval/generalization_test.py`.

**Top-level one-off/demo scripts** (category C/E — not part of the eval reproduction path, mostly demo/migration utilities):
`scripts/demo_pipeline.py`, `scripts/generate_demo_pdf.py`, `scripts/extract_imsdb.py`, `scripts/migrate_to_cloud.py` (has the hardcoded-password finding, see `SECURITY_AUDIT.md`), `scripts/run_full_ri_pipeline.py`, `scripts/run_pipeline_on_screenplay.py`, `scripts/run_pipeline_on_text.py`, `scripts/validate_ri_pipeline.py`, `scripts/compliance_check.py`.

No entrypoints were removed or renamed. This inventory is descriptive only — used to inform `DOCUMENTATION_INDEX.md` and `FINAL_REPOSITORY_AUDIT.md`.
