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
Dockerfile          # Backend image (uvicorn)
apps/web/Dockerfile # Frontend image (Next.js standalone build)
docker-compose.yml  # clickhouse + backend + web, see README Deployment section
```

## Deployment Notes
- `docker compose up --build` runs ClickHouse, backend, and web together; see README's Deployment section for required env vars.
- Login/signup are rate-limited (slowapi, in-memory per-process — not shared across replicas without Redis).
- ClickHouse has no true unique constraint; signup narrows (not eliminates) the duplicate-email race via a re-check-after-insert — see the comment in `backend/api/main.py`'s signup handler.
- The frontend's `src/lib/api.ts` treats a 401 on an authenticated request as session expiry (clears token, redirects to `/login`), distinct from a login-attempt 401.
