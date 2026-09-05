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
8.  **Auth & Projects**: Email/password + JWT auth (`backend/auth.py`) gates every route. A `project` groups multiple document uploads as *versions* of the same work — re-uploading a revised draft under the same `project_id` compares its detected conflicts against the previous version (`GET /projects/{id}/versions/{n}/diff`), joined on `(entity_id, attribute)` rather than any per-upload ID, since `EntityRegistry` is now scoped by `project_id` so the same character keeps the same `entity_id` across versions.

## Auth

Every route requires `Authorization: Bearer <token>` from `POST /auth/signup` or `POST /auth/login`. Passwords are bcrypt-hashed; JWTs are HS256-signed with `JWT_SECRET` (set your own in `.env`, generated via `openssl rand -hex 32` — never commit a real value). Every project/version/conflict/report route checks the caller owns the resource before returning anything.

Login and signup are rate-limited (`slowapi`, 5 requests/minute per IP) to blunt credential-stuffing/brute-force attempts against `/auth/login`.

Known limitation: `users`/`projects` live in ClickHouse (not a real OLTP store), so there's no database-enforced unique constraint on email. Signup does a pre-insert existence check *and* a post-insert re-check (picks the earliest `(created_at, id)` row for the email and rejects the request if it isn't the one it just wrote) to close most of the race window between two near-simultaneous signups for the same address, but ReplacingMergeTree still gives no atomic compare-and-swap, so a vanishingly rare double-signup remains possible in theory. Acceptable for this project's scope; a production deployment would use a real relational store with a unique constraint for these tables.

The frontend also has no server-side session store: a 24h-old JWT is simply rejected with 401, and the API client (`apps/web/src/lib/api.ts`) treats any 401 on an authenticated request as an expired session, clearing the stored token and redirecting to `/login`.

## Running the project

```bash
# 1. ClickHouse (via docker-compose) + schema
docker compose up -d
docker exec -i storytrace-clickhouse-1 clickhouse-client --database storytrace < backend/clickhouse/schema.sql

# 2. Python deps
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# 3. Configure environment
cp .env.example .env    # then set GEMINI_API_KEY (or leave MODEL_PROVIDER=ollama for local-only)
                         # and JWT_SECRET (openssl rand -hex 32) -- required for any auth/upload call

# 4. Local LLM (optional, for MODEL_PROVIDER=ollama -- the default, no API key needed)
ollama pull qwen2.5:7b

# 5. Backend API
uvicorn backend.api.main:app --reload --port 8000

# 6. Frontend
cd apps/web && npm install && npm run dev
```

Sign up (`POST /auth/signup`) and log in via the web UI, then upload a `.pdf`, `.epub`, `.txt`, or `.fountain` document (`POST /screenplay/upload`) to kick off the full parse -> extract -> detect -> investigate pipeline as a background job; poll `GET /screenplay/{id}/overview` for progress. Uploading again with the same `project_id` adds a new version to that project instead of starting a new one, and `GET /projects/{id}/versions/{n}/diff` compares it against the version before it. `FRONTEND_ORIGIN` (default `http://localhost:3000`) controls which origin CORS allows -- set it to your deployed frontend's URL in production.

To run the pipeline directly from the CLI against a plain-text document instead of through the API:

```bash
python3 -m scripts.run_pipeline_on_text data/test_documents/controlled_test.txt
python3 -m scripts.run_pipeline_on_screenplay data/test_documents/<screenplay>.txt
```

Set `MODEL_PROVIDER=gemini` to use the Gemini API (API key auth) instead of the local Ollama default (Gemini's free tier is capped at 20 requests/day per model -- see `FINDINGS.md`). Set `MODEL_PROVIDER=vertexai` to use Vertex AI instead -- same Gemini models, but authenticated against a GCP project via Application Default Credentials rather than an API key, with GCP's normal Vertex AI rate limits rather than the free-tier per-day cap. Requires `GOOGLE_CLOUD_PROJECT` (and `gcloud auth application-default login` locally, or `GOOGLE_APPLICATION_CREDENTIALS` pointing at a service-account key for deployment) -- see `.env.example`.

## Deployment

The whole stack (ClickHouse, backend, frontend) runs via Docker Compose:

```bash
cp .env.example .env   # set JWT_SECRET (openssl rand -hex 32) at minimum
export JWT_SECRET=$(grep ^JWT_SECRET= .env | cut -d= -f2)
docker compose up --build
```

This builds the backend (`Dockerfile`, FastAPI + uvicorn on port 8000) and frontend (`apps/web/Dockerfile`, Next.js standalone build on port 3000) images, starts ClickHouse first, waits for its healthcheck, loads `backend/clickhouse/schema.sql` automatically via ClickHouse's `docker-entrypoint-initdb.d`, then brings up the backend and finally the frontend once the backend's healthcheck passes.

Environment variables the compose file reads from the shell (see `.env.example` for the full list):

-   `JWT_SECRET` (required) -- compose refuses to start the backend without it.
-   `FRONTEND_ORIGIN` -- CORS allow-list; set to your deployed frontend's public URL.
-   `NEXT_PUBLIC_API_URL` -- the URL the *browser* uses to reach the API; baked into the frontend at build time, so it must be the API's public URL, not the in-network `backend` service name.
-   `MODEL_PROVIDER`, `GEMINI_API_KEY` / `GOOGLE_API_KEY` -- only needed if using `MODEL_PROVIDER=gemini`; `ollama` (the default) needs a reachable Ollama instance instead, which this compose file does not provision.
-   `MODEL_PROVIDER=vertexai`, `GOOGLE_CLOUD_PROJECT`, `GOOGLE_CLOUD_LOCATION`, `VERTEX_MODEL`, `GOOGLE_APPLICATION_CREDENTIALS` -- only needed if using `MODEL_PROVIDER=vertexai`. `GOOGLE_APPLICATION_CREDENTIALS` should point at a mounted service-account key (see the commented-out `volumes:` entry on the `backend` service in `docker-compose.yml`); on Cloud Run, prefer attaching a service account directly (`gcloud run services update <service> --service-account=<sa>@<project>.iam.gserviceaccount.com` with `roles/aiplatform.user` granted) over shipping a key file, so `GOOGLE_APPLICATION_CREDENTIALS` can be left unset entirely.
-   ClickHouse connection vars (`CLICKHOUSE_HOST`/`PORT`/`USER`/`PASSWORD`/`DB`) are pre-wired to the `clickhouse` service and don't need overriding for local/single-host deployment.

Not covered by this setup: TLS termination, a reverse proxy/domain, and Ollama's own container (bring your own, or set `MODEL_PROVIDER=gemini`/`vertexai`) -- add those in front of this compose file for a real public deployment.

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
