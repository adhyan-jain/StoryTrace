# StoryTrace (formerly SceneSentry)

**Your story's continuity guardian.**

StoryTrace is an agentic, multi-document narrative continuity engine. It converts screenplay or novel documents into a structured temporal model of a shared story universe (`NarrativeUnit`s), tracks state over time (character presence, location, prop possession, etc.) across those documents, detects conflicts, and uses an Investigation Agent to verify findings against the original narrative text.

## Architecture

1.  **Document Parsers**: A `ScreenplayParser` and `NovelParser` each extract raw text into document-type-agnostic `NarrativeUnit`s (scenes, chapters, or passages), maintaining exact page boundaries.
2.  **Entity Resolver & State Extraction**: Uses Gemini to structure state events from each `NarrativeUnit`.
3.  **Story State Engine**: ClickHouse database storing append-only temporal events, keyed by `story_universe_id` and `sequence_number` rather than any per-document numbering.
4.  **Candidate Detector**: SQL window functions finding suspicious state transitions.
5.  **Investigation Agent**: ONE genuinely agentic component (using ClickHouse MCP) that investigates conflicts and outputs an `InvestigationVerdict`.
6.  **Continuity Autopsy**: The user-facing presentation of an `InvestigationVerdict` — not a separate agent or stage. See [docs/architecture.md](docs/architecture.md).
7.  **Frontend**: Next.js UI providing a premium professional filmmaking tool experience.

## Running the project

```bash
# 1. ClickHouse (via docker-compose) + schema
docker compose up -d
docker exec -i storytrace-clickhouse-1 clickhouse-client --database storytrace < backend/clickhouse/schema.sql

# 2. Python deps
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# 3. Configure environment
cp .env.example .env    # then set GEMINI_API_KEY, or leave MODEL_PROVIDER=ollama for local-only

# 4. Local LLM (optional, for MODEL_PROVIDER=ollama -- the default, no API key needed)
ollama pull qwen2.5:7b

# 5. Backend API
uvicorn backend.api.main:app --reload --port 8000

# 6. Frontend
cd apps/web && npm install && npm run dev
```

Upload a `.pdf`, `.epub`, `.txt`, or `.fountain` document via `POST /screenplay/upload` (or the web UI) to kick off the full parse -> extract -> detect -> investigate pipeline as a background job; poll `GET /screenplay/{id}/overview` for progress.

To run the pipeline directly from the CLI against a plain-text document instead of through the API:

```bash
python3 -m scripts.run_pipeline_on_text data/test_documents/controlled_test.txt
python3 -m scripts.run_pipeline_on_screenplay data/test_documents/<screenplay>.txt
```

Set `MODEL_PROVIDER=gemini` to use Gemini instead of the local Ollama default (Gemini's free tier is capped at 20 requests/day per model -- see `FINDINGS.md`).

## Documentation

-   [Architecture](docs/architecture.md)
-   [Data Model](docs/data-model.md)
-   [Agent Architecture](AGENTS.md)
-   [Investigation / Autopsy](docs/investigation.md)
-   [Design System](docs/design.md)
-   [Development Guidelines](CLAUDE.md)

## Reused Infrastructure

This project was initialized using carefully selected components from the **Echotales** codebase. Status reflects what has actually been adapted to run against `backend.*`, not just copied:

-   `backend/llm/base.py`: Robust JSON extraction/healing logic and Pydantic validation. Adapted and in active use (`backend/llm/client.py`, `backend/agent/investigator.py`).
-   `backend/story_state/interval.py`: Temporal modeling concepts. Adapted and in use.
-   `backend/story_state/models.py`: Data schema, adapted for ClickHouse and for the document-agnostic `NarrativeUnit` model (`story_universe_id`/`unit_id`/`sequence_number`, not `screenplay_id`/`scene_id`/`scene_number`).
-   `tests/unit/test_llm.py` & `tests/benchmark/`: **Not yet adapted.** These still import the `echotales` package directly (`echotales.pipeline.llm.router`, `echotales.core.store`, etc.), which isn't vendored into this repo, so they cannot be collected or run here. They are excluded via `pytest.ini` until ported. Treat `FakeProvider`/`GoldSet` as Echotales-side test fixtures, not as dependencies of this codebase's runtime or test suite.
