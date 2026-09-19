# Reproducibility Guide

This document distinguishes the three corpora used in this repository and gives verified setup/run commands. Verification method for each command is noted explicitly — some were run live (pytest, static file checks); the pipeline/eval/benchmark commands were verified by reading their source (`argparse` definitions, entrypoints, output paths) rather than executed, since they make real LLM/ClickHouse calls with no dry-run mode. See "Corpora" below before running any of them.

## Corpora

- **DEVELOPMENT CORPUS**: `data/test_documents/controlled_test.txt` (and `controlled_test_v2.txt` for the `--v2` overfitting check) — a small, hand-authored test document used for day-to-day iteration and the `scripts/eval` gate (`data/eval/golden_dataset.py` / `golden_dataset_v2.py`). Tracked in git (allowlisted in `.gitignore`).
- **BENCHMARK CORPUS**: the 10-film screenplay set referenced by `data/eval/corpus_manifest.json`, stored under `data/eval/screenplays/*.txt` (gitignored — regeneratable/licensed source text, not redistributed). This is the corpus behind the frozen V2 benchmark numbers (see `FINAL_NUMBERS_SOURCE_OF_TRUTH.md`) and is not rerun by this pass, per explicit instruction.
- **HELD-OUT CORPUS**: `the_green_mile_film` (`data/eval/screenplays/the_green_mile_film.txt`), marked `"corpus_role": "held_out"` in `corpus_manifest.json` — evaluated once via `scripts/v2/run_held_out_green_mile.py`, never used for tuning. Results are frozen in `results/v2/held_out_green_mile/green_mile_raw_output.json` and `docs/RESULTS/GREEN_MILE_HELDOUT_EVALUATION.md`.

Screenplay text under `data/eval/screenplays/` is licensed source material and is gitignored — it is not distributed with this repository. Contact the maintainer for access if reproducing the benchmark/held-out results from scratch.

## Environment

- **Python**: 3.14 (verified: `python3 --version` → `Python 3.14.7` in this environment; no `pyproject.toml`/version pin exists in the repo, so any recent Python 3.x compatible with `requirements.txt`'s pins should work).
- **Dependencies**: `pip install -r requirements.txt` (18 lines; see `docs/DEPENDENCY_AUDIT.md` for the full per-package audit).
- **Frontend**: `apps/web` — Next.js 16 / React 19, `pnpm` (per `apps/web/package.json`'s `packageManager` field).

## Install (verified this pass)

```bash
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in CLICKHOUSE_PASSWORD, JWT_SECRET, etc. -- see inline comments in .env.example
```

`.env.example` is a clean template with every value blank and inline documentation for each variable (verified by reading the file — no leaked values, confirmed in `SECURITY_AUDIT.md`).

## ClickHouse setup

```bash
docker compose up -d
docker exec -i storytrace-clickhouse-1 clickhouse-client --database storytrace < backend/clickhouse/schema.sql
```

`docker-compose.yml` requires `CLICKHOUSE_LOCAL_PASSWORD` (local container) and `CLICKHOUSE_PASSWORD`/`JWT_SECRET` (backend service) to be set with no insecure fallback — generate with `openssl rand -hex 24`/`openssl rand -hex 32` respectively (per the compose file's own inline error messages).

## Model provider

Per `CLAUDE.md`'s explicit rule: **local testing and eval must use Ollama** (`MODEL_PROVIDER=ollama`, the default in `backend/llm/provider.py`/`scripts/eval`'s `get_provider()`), never Vertex AI or the Gemini API, unless a task explicitly names one of those providers. `ollama pull qwen2.5:7b` before running anything locally.

## Running tests

```bash
python3 -m pytest
```

**Verified live this pass: 114 passed, 0 failed** (final count, after fixing `pytest.ini` to scope collection to `testpaths = tests` — see `DEAD_CODE_AUDIT.md` for why), 5 third-party deprecation warnings (httpx/starlette, google-genai, slowapi — not project code). Runtime ~4-7s.

## Running candidate detection / investigation (V1, live API path)

```bash
uvicorn backend.api.main:app --reload --port 8000
```

Then use the frontend (`cd apps/web && pnpm install && pnpm dev`) or call the API directly to upload a document (`POST /screenplay/upload`) and poll `GET /screenplay/{id}/overview`.

## Running the V1 eval gate

```bash
python3 -m scripts.eval          # against data/eval/golden_dataset.py (controlled_test.txt)
python3 -m scripts.eval --v2     # against data/eval/golden_dataset_v2.py (controlled_test_v2.txt, overfitting check)
```

Verified by reading `scripts/eval/__main__.py`: no `--help` flag exists (only `--v2` is checked via `"--v2" in sys.argv`); running the script bare immediately starts the real pipeline (ClickHouse connection + an `mcp-clickhouse` subprocess + live LLM calls) — there is no dry-run mode. **Do not run this speculatively**; it was not executed live during this cleanup pass to avoid an unintended pipeline run (confirmed via source inspection instead — see the note at the top of this document). Writes `EVAL_REPORT.md` (or `EVAL_REPORT_V2.md`) to the repo root; exits non-zero if F1 < 0.6.

## Reproducing the V2 benchmark (NOT rerun this pass — frozen results only)

```bash
python3 -m scripts.v2.run_v2_eval --film all      # or --film <slug>, --limit N
```

Verified via `scripts/v2/run_v2_eval.py`'s `argparse` setup (`--film`, `--limit`). This is the command that produced the frozen commit-`4064cf7` benchmark numbers. **Per explicit instruction, this pass does not rerun it.**

## Reproducing the held-out Green Mile evaluation (NOT rerun this pass — frozen results only)

```bash
python3 -m scripts.v2.run_held_out_green_mile
```

Verified via source inspection (`scripts/v2/run_held_out_green_mile.py`, no CLI args). Produced `results/v2/held_out_green_mile/green_mile_raw_output.json`, summarized in `docs/RESULTS/GREEN_MILE_HELDOUT_EVALUATION.md`. **Per explicit instruction, this pass does not rerun it.**

## Statistical / V1-vs-V2 comparison

```bash
python3 -m scripts.v2.compare_v1_v2
python3 -m scripts.v2.audit_statistical
```

Both verified via source inspection only (no CLI args, no `--help`). Not rerun this pass.

## Inspecting existing results

All frozen results are static files — no code required to inspect them:
- `results/v2/*.json` (per-film metrics, confusion matrix, Green Mile raw output)
- `docs/RESULTS/*.md` (human-readable summaries)
- `docs/FINAL_NUMBERS_SOURCE_OF_TRUTH.md` (the authoritative numbers block, cross-checked against these files)
