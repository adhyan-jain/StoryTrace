# StoryTrace Guidelines

StoryTrace is an agentic, multi-document narrative continuity engine.

## Core Rules

1. **Document-Type Agnostic**: The backend model uses `NarrativeUnit` (representing scenes, chapters, passages). Do not hardcode "scene" into the core temporal model.
2. **ClickHouse is the Temporal Engine**: Use ClickHouse to execute temporal analytics (e.g., `lagInFrame`) across vast sequences of story events spanning multiple documents.
3. **One Investigation Agent**: The parsing, extraction, and detection steps are strictly deterministic (or structured LLM). The single Investigation Agent is invoked only to adjudicate detected candidates using its ClickHouse MCP tools.
4. **Provenance**: Every extracted event must retain exact `unit_id`, `page_start/end`, and `raw_excerpt`. The user must be able to trace a finding back to the exact text.
5. **No Fake Intelligence**: If mocking API calls for local demos, clearly mark them.
6. **Polished Output**: Output code should be production-ready and the UI should feel like a premium tool for filmmakers and authors.

## Skills
Always apply the frontend-design skill for any UI work.
Apply web-design-guidelines when reviewing or writing frontend code.

## MCP Tools
- Use Playwright MCP to verify UI changes after implementing them
- Use Context7 MCP when working with any external library


## Code Structure

```text
backend/
  ingestion/       # PDF parsing to NarrativeUnits
  llm/             # Gemini structured clients
  pipeline/        # Event extraction & resolution
  clickhouse/      # State Engine connections
  candidate_detection/ # SQL window functions
  agent/           # Investigation Agent
  api/             # FastAPI backend (rate-limited auth via slowapi)
  auth.py          # Signup/login, JWT issuance
apps/
  web/             # Next.js Continuity Autopsy UI
    src/lib/api.ts   # Shared API client; 401 -> session-expiry redirect to /login
    src/lib/auth.tsx # Auth state/provider
tests/
  unit/            # pytest (FastAPI TestClient) — auth, projects, diff, report
data/
  eval/            # golden_dataset.py — hand-verified ground truth (not gitignored,
                   #   unlike the rest of data/, which holds regeneratable novel corpora)
scripts/
  eval/            # Preprocessing pipeline eval: python3 -m scripts.eval.
                   # Real precision/recall/F1 vs data/eval/golden_dataset.py,
                   # writes EVAL_REPORT.md. See README's Evaluation section.
Dockerfile          # Backend image (uvicorn)
apps/web/Dockerfile # Frontend image (Next.js standalone build)
docker-compose.yml  # clickhouse + backend + web, see README Deployment section
```

## Local Testing / Model Provider

> **RULE: For local testing and eval, ALWAYS use Ollama. NEVER use Vertex AI
> or the Gemini API unless the user explicitly names it for that specific
> request.** This applies to `python3 -m scripts.eval`, all pipeline scripts,
> and all iteration loops. Violating this rule wastes real money and quota.

- **Default to Ollama for all local testing and eval runs** (`MODEL_PROVIDER=ollama` in `.env`, already the default in `backend/llm/provider.py`/`scripts/eval/run_eval.py`'s `get_provider()` when the env var is unset). Do NOT switch `MODEL_PROVIDER` to `vertexai` (or run anything that hits Vertex AI/Gemini API) for local iteration unless the user explicitly asks for it in that message.
- Why: Vertex AI calls cost real money and are rate-limited (429 RESOURCE_EXHAUSTED was hit repeatedly during iterative eval runs); Ollama runs fully local and free against models already pulled (`qwen2.5:7b` is the current default — see `backend/llm/ollama.py`).
- This applies to `python3 -m scripts.eval` and any other local pipeline run. Only use Vertex/Gemini when the user names it explicitly for that task (e.g. a final demo run, or explicitly comparing provider quality).

## Deployment Notes
- `docker compose up --build` runs ClickHouse, backend, and web together; see README's Deployment section for required env vars.
- Login/signup are rate-limited (slowapi, in-memory per-process — not shared across replicas without Redis).
- ClickHouse has no true unique constraint; signup narrows (not eliminates) the duplicate-email race via a re-check-after-insert — see the comment in `backend/api/main.py`'s signup handler.
- The frontend's `src/lib/api.ts` treats a 401 on an authenticated request as session expiry (clears token, redirects to `/login`), distinct from a login-attempt 401.
