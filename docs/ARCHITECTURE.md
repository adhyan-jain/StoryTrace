# StoryTrace — Architecture (Current Implementation)

This document describes what is actually implemented and reachable in the repository today, not historical or aspirational design. It reflects `v2-development` @ `e330db898475f5d4db1eb55ab5637c2cdc480883`.

## 1. System Overview

> StoryTrace builds a persistent, queryable model of a story's evolving world.

StoryTrace ingests a screenplay or novel (PDF, EPUB-derived text, Fountain, or plain text), parses it into document-type-agnostic `NarrativeUnit`s, extracts trackable story-state facts from each unit via an LLM, stores those facts as `StateEvent`s in ClickHouse, uses ClickHouse SQL window functions to deterministically detect suspicious state transitions ("candidate conflicts"), and hands each candidate to a single `InvestigationAgent` that adjudicates it (verified / resolved / uncertain) using read-only ClickHouse tools exposed over MCP. Verdicts, with full provenance back to the source text, are served through a FastAPI backend to a Next.js frontend ("Continuity Autopsy" UI).

## 2. Directory Structure

```
backend/
  ingestion/       NarrativeUnit model + PDF/EPUB/Fountain/plain-text parsers
  llm/              LLM provider abstraction (Ollama / Gemini / Vertex AI)
  pipeline/         State extraction (LLM) + entity resolution + integrity checks
  clickhouse/       ClickHouseClient — the temporal engine wrapper
  candidate_detection/  SQL window-function conflict detector
  agent/            InvestigationAgent + its MCP-backed ClickHouse tools
  api/              FastAPI app (main.py) — wires the above into HTTP endpoints
  auth.py           Signup/login, JWT issuance
  story_state/      StateEvent / CandidateConflict / InvestigationVerdict models
  eval/             Ablation-only extractor/investigator variants used by scripts/eval
  v2/               Parallel V2 implementation (see V1_V2_BOUNDARY.md) — evaluation-only,
                     not imported by api/main.py
apps/web/           Next.js (App Router) frontend
  src/lib/api.ts      Shared API client; treats a 401 on an authenticated request as
                       session expiry (redirect to /login)
  src/lib/auth.tsx    Auth state/provider
scripts/
  eval/             V1 evaluation harness (python3 -m scripts.eval)
  v2/               V2 evaluation/audit harness (run_v2_eval.py, run_held_out_green_mile.py, ...)
tests/
  unit/             pytest — auth, projects, diff, report, pipeline correctness/integrity
  v2/               pytest — V2 candidate detector, extractor, investigator, models
  (benchmark/ removed — imported unvendored `echotales`, see DEAD_CODE_AUDIT.md)
data/
  eval/             golden_dataset.py / golden_dataset_v2.py (tracked), corpus manifest,
                     scored metrics JSON
docs/               This documentation tree
results/v2/         V2 benchmark/Green-Mile output JSON
```

## 3. Data Flow (V1, the live API path)

1. **Ingestion** — `backend/ingestion/parsers.py`'s `ScreenplayParser`, `NovelParser`, `FountainParser`, or `PlainTextParser` reads the uploaded document and splits it into `NarrativeUnit`s (`backend/ingestion/models.py`), each carrying `unit_id`, `story_universe_id`, `document_id`, `unit_type` ("scene"/"chapter"/"passage"), `sequence_number`, `title`, `page_start`/`page_end`, and `raw_text`.
2. **Extraction** — `backend/pipeline/state_extraction.py`'s `extract_state_events` / `extract_state_events_batch` sends each unit's text to the configured `LLMProvider` with a structured-output prompt (`SYSTEM_PROMPT`) asking for controlled-vocabulary state facts (location, location.city, injury.\<body_part\>, clothing.\<item\>, possession.\<prop\>). Every fact is validated against a hallucination check (`_match_excerpt` — excerpt must be a verbatim substring of the unit text), a grounding check (`_location_grounded`, `_injury_grounded`), and a controlled-vocabulary normalizer (`_normalize_attribute`) before becoming a `StateEvent`.
3. **Entity resolution** — `backend/pipeline/entity_resolution.py`'s `EntityRegistry.resolve()` deterministically maps a character/prop/location name to a stable `entity_id` (scoped by `id_scope`, typically `project_id`, so the same entity resolves across versions of the same project).
4. **Storage** — `backend/clickhouse/client.py`'s `ClickHouseClient.insert_state_events` (and `insert_narrative_units`, `insert_entities`) writes into ClickHouse tables `narrative_units`, `entities`, `state_events`.
5. **Candidate detection** — `backend/candidate_detection/detector.py`'s `CandidateDetector.detect_conflicts` runs a single SQL query using ClickHouse's `lagInFrame()` window function (partitioned by `entity_id, attribute`, ordered by `sequence_number`) to find specific suspicious transitions: possession `lost → held`/`lost → acquired` with no bridging event, injury `injured → healed`, and `location.city` value changes. Results become `CandidateConflict` rows.
6. **Investigation** — `backend/agent/investigator.py`'s `InvestigationAgent.investigate_async` runs a bounded (max 8 calls) ReAct loop per candidate: the LLM picks a tool (`get_entity_timeline`, `get_unit_text`, `get_state_at_unit`, `find_attribute_changes`, or `finish`) from `backend/agent/tools.py`'s `AgentTools`, each executed as a real `run_query` MCP call against an `mcp-clickhouse` stdio server — never a direct `clickhouse_connect` client. On `finish`, the agent produces a `FinalVerdict` (status: verified/resolved/uncertain, severity, confidence, explanation) judged against the shared `_BRIDGE_CRITERIA` text, stored as an `InvestigationVerdict`.
7. **API** — `backend/api/main.py` (FastAPI) wires all of the above into upload/processing/diff/report endpoints, rate-limited via `slowapi`, auth via `backend/auth.py` (JWT).
8. **Frontend** — `apps/web` (Next.js) renders the Continuity Autopsy UI: dashboard, entity timeline, upload flow.

## 4. V2 State Representation

V2 mirrors the V1 shape (`backend/v2/story_state/models.py`) but is a fully parallel, evaluation-only implementation (`backend/v2/{agent,candidate_detection,clickhouse,pipeline,story_state}/`) exercised only by `tests/v2/*` and `scripts/v2/*`. `backend/api/main.py` imports exclusively from the V1 modules — see `docs/V1_V2_BOUNDARY.md` for the full V1/V2 split and what that means for "current default."

Both V1 and V2 use `NarrativeUnit` (not a "scene"-specific type) as the core temporal unit, per the document-type-agnostic requirement — `unit_type` is a field on the model, not a separate class hierarchy.

## 5. ClickHouse — the Temporal Engine

`backend/clickhouse/client.py`'s `ClickHouseClient` wraps `clickhouse_connect`. Key tables: `users`, `projects`, `project_versions`, `narrative_units`, `entities`, `state_events`, `candidate_conflicts`, `investigation_verdicts`, `processing_status`. `project_versions` is keyed so the same character/entity resolves across versions via `EntityRegistry`'s `id_scope`. `processing_status` uses `ReplacingMergeTree` semantics (each upsert call inserts a new row that supersedes the prior one on merge). Deletes use `ALTER TABLE ... DELETE` (async ClickHouse mutations). `CLICKHOUSE_PASSWORD` has no default and the client raises `RuntimeError` if unset — see `docs/SECURITY_AUDIT.md`.

`CandidateDetector` (Section 6) is the concrete use of ClickHouse as the temporal analytics engine via `lagInFrame()` — this is the "temporal engine" referenced in project rules, not a separate service.

## 6. Candidate Detection

`backend/candidate_detection/detector.py`'s single SQL query (see docstring/comments in that file) intentionally covers only structurally-safe patterns — a general "location changed" rule was tried and reverted after tanking detection precision (1.000 → 0.111 on a real eval run, since ordinary scene-to-scene movement looks identical to an unexplained jump at the SQL level). This is a disclosed, deliberate detection gap: whether a location change is narratively explained requires reading the text, which is the Investigation Agent's job, not the deterministic detector's.

## 7. Investigation Agent

Per the "One Investigation Agent" project rule, `InvestigationAgent` is the single adjudication agent — parsing/extraction/detection are deterministic or structured-LLM, not agentic. It is invoked once per candidate, with a hard `max_calls = 8` budget, tool-repeat detection (two identical repeat calls forces an immediate verdict rather than burning the budget), and a shared `_BRIDGE_CRITERIA` block that both the per-step decision prompt and the final-verdict prompt reference (so the verdict is judged against the same criteria used mid-investigation, not a separately-drifted standard).

## 8. Evidence / Provenance

Every `StateEvent` and downstream `CandidateConflict`/`InvestigationVerdict` retains `unit_id`, `page_ref` (from `NarrativeUnit.page_start`), and `raw_excerpt`. `raw_excerpt` is hallucination-checked (`_match_excerpt`) to be a real substring of the unit's `raw_text`, and what's stored is the source text's own slice, not the model's possibly-reworded rendering — so any finding traces back to exact, verbatim text in the document (per the "Provenance" project rule).

## 9. Evaluation Pipeline

- **V1**: `python3 -m scripts.eval` (see `scripts/eval/__main__.py`) runs the pipeline against `data/eval/golden_dataset.py` and computes precision/recall/F1 via `scripts/eval/compute_metrics.py`, writing `EVAL_REPORT.md`.
- **V2**: `scripts/v2/run_v2_eval.py`, `scripts/v2/run_held_out_green_mile.py`, `scripts/v2/score_v2_experiment.py`, `scripts/v2/compare_v1_v2.py`, and the `scripts/v2/audit_*.py` family (candidate recall, investigator, robustness, statistical) — evaluated against `data/eval/golden_dataset_v2.py`. Results live in `results/v2/*.json` and `docs/RESULTS/*` (post-reorg).

## 10. Configuration

- `MODEL_PROVIDER` env var selects the LLM backend for local testing/eval; per `CLAUDE.md`, this must stay `ollama` (the default) for all local iteration — `vertexai`/Gemini are opt-in only when explicitly requested for a specific task, since they cost money and are rate-limited.
- `backend/llm/provider.py`'s `get_llm_provider()` reads `MODEL_PROVIDER` and switches between `gemini`/`ollama` — note this appears to be a separate/older provider-selection path from the one actually wired into `backend/api/main.py` (which directly imports `GeminiProvider`, `OllamaProvider`, `VertexAIProvider` from `backend/llm/{client,ollama,vertexai}.py` and does its own selection inline). Flagged for `DEAD_CODE_AUDIT.md` to confirm whether `backend/llm/provider.py` is still a live entrypoint anywhere (e.g. `scripts/eval`) or superseded.
- ClickHouse connection: `CLICKHOUSE_HOST`/`PORT`/`USER`/`PASSWORD`/`DB`/`SECURE` env vars, no default password (see Section 5).
- Ollama model: `qwen2.5:7b` (per `CLAUDE.md`).

## 11. Test Architecture

- `tests/unit/` — auth, projects, diff, report, pipeline correctness/integrity (V1 path).
- `tests/v2/` — candidate detector, extractor, investigator, models (V2 path).
- `tests/benchmark/` and `tests/unit/test_llm.py` previously existed but imported an unvendored `echotales` package and could not be collected; both were deleted during the final repository cleanup pass (see `DEAD_CODE_AUDIT.md`).
- Current state: `python3 -m pytest -q` → **115 passed, 0 failed** (verified 2026-09-19, unchanged before/after the deletion above since those files were already excluded from collection).

## 12. Reproducibility Instructions

See `docs/REPRODUCIBILITY.md` for the full, verified walkthrough. Summary:

```bash
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in CLICKHOUSE_PASSWORD, JWT secret, etc.
docker compose up -d clickhouse   # or run ClickHouse locally
python3 -m pytest                 # 115 passed
python3 -m scripts.eval           # V1 eval against data/eval/golden_dataset.py
python3 -m scripts.eval --v2      # V2 eval against data/eval/golden_dataset_v2.py
```

Frontend: `cd apps/web && pnpm install && pnpm dev`.
