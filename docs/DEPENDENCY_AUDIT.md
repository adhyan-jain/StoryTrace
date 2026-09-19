# Dependency Audit

Scope: every dependency in `requirements.txt` (Python, all pinned exact-version) and `apps/web/package.json` (Next.js frontend). No versions were changed and no dependency files were modified during this audit — findings only.

## Python (`requirements.txt`)

| Dependency | Version | Where used | Classification | Notes |
|---|---|---|---|---|
| pymupdf | 1.28.2 | `backend/ingestion/parsers.py:1`, `backend/api/main.py:11` (imported as `fitz`) | Runtime (ingestion) | PDF parsing per CLAUDE.md's `ingestion/` role. |
| pydantic | 2.13.5 | 18 files across `backend/` | Runtime (core) | Schema/validation backbone for structured LLM output and API models. |
| pytest | 9.1.1 | Test collection (`tests/`, `pytest.ini`) | Development-only | Test runner, not a runtime dependency. |
| python-multipart | 0.0.32 | Not directly imported; required transitively by FastAPI's `UploadFile`/`Form` handling (`backend/api/main.py:278` uses `UploadFile`) | Runtime (transitive, required by FastAPI) | FastAPI raises at request time without it when multipart form parsing is used; correctly listed even though there's no direct `import python_multipart`. |
| beautifulsoup4 | 4.15.0 | 1 file (imported as `bs4`) | Runtime | Used narrowly — confirm the one call site still needs it before any future removal; not removed here per audit rules (single hit isn't "confidently unused"). |
| clickhouse-connect | 1.7.2 | 2 files (`backend/clickhouse/client.py` and one other) | Runtime (core) | The temporal engine client per CLAUDE.md rule 2. |
| fastapi | 0.141.1 | 4 files, incl. `backend/api/main.py` | Runtime (core) | API framework. |
| uvicorn | 0.52.4 | Not imported in Python source; invoked as a CLI process (`Dockerfile:32`, `README.md:47`) | Runtime (ASGI server, process-level) | Correctly a runtime dep even with zero `import` hits — it's the server entrypoint, not a library call. |
| httpx | 0.28.1 | 1 file | Runtime | Also pulled in transitively by `starlette.testclient` (see pytest deprecation warning in `TEST_AUDIT.md`) but that's a test-only transitive use; the direct hit is production code. |
| google-genai | 2.20.0 | 3 files (`backend/llm/gemini.py`, `client.py`, etc.) | Runtime (LLM provider) | Gemini structured client per CLAUDE.md. |
| google-adk | 2.8.0 | 2 files (`backend/agent/adk_runner.py` and one other) | Runtime (Investigation Agent) | Google Agent Development Kit — powers the single Investigation Agent (CLAUDE.md rule 3). |
| google-cloud-aiplatform | 2.1.0 | Not imported directly as `google.cloud.aiplatform`; used via the `vertexai` package (`backend/llm/vertexai.py` and 8 other files import `vertexai`) | Runtime (Vertex AI provider) | `vertexai` is the import surface this package installs; grep for the raw module path under-counts it. Only exercised when `MODEL_PROVIDER=vertexai` — per CLAUDE.md, local/eval work defaults to Ollama, so this dependency is live but intentionally dormant in normal local runs. |
| fpdf2 | 2.8.8 | 2 files (imported as `fpdf`) | Development/demo-only | Used by `scripts/generate_demo_pdf.py`-style tooling, not the core pipeline. |
| mcp-clickhouse | 0.4.1 | 1 file | Runtime (Investigation Agent) | Provides the agent's ClickHouse MCP tools per CLAUDE.md rule 3. |
| pyjwt | 2.13.0 | 1 file (imported as `jwt`) | Runtime (auth) | JWT issuance in `backend/auth.py`. |
| bcrypt | 5.0.0 | 1 file | Runtime (auth) | Password hashing. |
| email-validator | 2.3.0 | Not imported directly; required transitively by Pydantic's `EmailStr` type (`backend/api/main.py:159,164`) | Runtime (transitive, required by Pydantic) | Pydantic delegates email format validation to this package at import time when `EmailStr` fields are used — correct to list even with no direct `import email_validator`. |
| slowapi | 0.1.10 | 1 file | Runtime (auth) | Rate-limits login/signup per CLAUDE.md's deployment notes. |

**Flagged for manual review (not removed):** `beautifulsoup4` — only one usage site found. Classified "possibly narrow" rather than "confidently unused," so left in place per the audit rule (only remove when *confidently* unused). Worth a human check of that call site before any future removal.

**None removed.** Every dependency maps to either a direct import, a CLI/process-level use (`uvicorn`), or a documented transitive requirement (`python-multipart`, `email-validator`). No redundant or duplicate-purpose packages found.

## Frontend (`apps/web/package.json`)

| Dependency | Version | Where used | Classification | Notes |
|---|---|---|---|---|
| next | 16.3.3 | Framework (App Router, `apps/web/src/app/`) | Runtime (core) | |
| react / react-dom | 19.2.8 | Framework | Runtime (core) | |
| clsx | ^2.1.1 | 8 combined hits with tailwind-merge across `apps/web/src` | Runtime | Conditional className composition. |
| tailwind-merge | ^3.6.0 | (see clsx row — grepped together) | Runtime | Pairs with `clsx` for the common `cn()` utility pattern. |
| lucide-react | ^1.37.0 | 2 files | Runtime | Icon set; low usage count but confirmed in-use, not flagged. |
| @playwright/test | ^1.62.1 | `apps/web/tests/` (Playwright E2E, referenced in CLAUDE.md's MCP tooling section) | Development-only | |
| @tailwindcss/postcss, tailwindcss | ^4 | `apps/web/postcss.config.mjs` present | Development-only (build) | Confirmed config file exists and references the package. |
| @types/node, @types/react, @types/react-dom, typescript | — | TS build | Development-only | |
| eslint, eslint-config-next | ^9 / 16.3.3 | `apps/web/eslint.config.mjs` present | Development-only | |

No unused or redundant frontend dependencies found. `packageManager: pnpm@10.33.0` is pinned in `package.json` — reproducibility-relevant, left untouched.

## Reproducibility note

Per CLAUDE.md, `MODEL_PROVIDER=ollama` is the default for all local testing/eval; `google-genai`/`google-cloud-aiplatform`/Vertex-path dependencies are installed and functional but should not be exercised in local iteration loops unless explicitly requested. This is a runtime-provider-selection fact, not a dependency-audit finding, but it explains why `vertexai`/`google-genai` import counts look low relative to their role — they're real, correctly-declared dependencies for a code path that's intentionally not the default local path.
