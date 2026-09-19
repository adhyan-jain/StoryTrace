# Security / Configuration Audit

## Secrets scan

Repo-wide grep (excluding `.git`, `node_modules`, `venv`) for common secret patterns (`sk-`, `AIza`, `AKIA`, private-key headers, Slack/GitHub tokens) found **zero hits**. Keyword search for `password`/`api_key`/`jwt_secret` in tracked files surfaced only legitimate code:
- `backend/auth.py` — password hash/verify function names, not values
- `backend/api/main.py` — Pydantic field names (`password: str`) for request schemas
- `backend/clickhouse/client.py` — a `password` constructor parameter, sourced from env vars at call time

**One finding, fixed this pass**: `scripts/migrate_to_cloud.py:33` hardcoded `password="admin"` as a local ClickHouse migration default. Not a live credential (it's a one-off local-dev migration script, not imported elsewhere), but stale and insecure-looking — `docker-compose.yml` now requires an explicit `CLICKHOUSE_LOCAL_PASSWORD` with no fallback, so `"admin"` was also factually wrong. Fixed to read `os.environ["CLICKHOUSE_LOCAL_PASSWORD"]` instead.

## `.env` handling

- `.env` (repo root) and `apps/web/.env.local` both exist locally, are **untracked**, and are correctly covered by `.gitignore` — confirmed via `git status --ignored`.
- `.env.example` is a clean template: every value is blank, with inline documentation of what each variable does. No leaked values.
- No `.env` file, of any name, appears in `git ls-files`.

## `.gitignore` coverage

Root `.gitignore` covers: `venv/`, `__pycache__/`, `*.pyc`, `.env`, Playwright artifacts, `graphify-out/`, and a documented `data/*` + `!data/eval/` + `!data/eval/golden_dataset*.py` allowlist (with an inline comment explaining the trailing-slash gotcha) so only the gold dataset stays tracked while `data/annotation/`, `data/processed/`, `data/raw/`, `data/stage/`, `data/test_documents/` remain ignored. `apps/web/.gitignore` separately covers `node_modules/`, `.next/`, `.env*`, and build artifacts.

No gaps found — nothing sensitive is tracked that shouldn't be.

## Docker / deployment config

- `Dockerfile` — backend uvicorn image.
- `apps/web/Dockerfile` — Next.js standalone build.
- `docker-compose.yml` — orchestrates ClickHouse, backend, web:
  - ClickHouse ports are loopback-only (`127.0.0.1:8123`/`9000`), with inline commentary explaining why (avoiding a prior insecure `0.0.0.0` + default-password exposure).
  - Local ClickHouse password is `${CLICKHOUSE_LOCAL_PASSWORD:?CLICKHOUSE_LOCAL_PASSWORD must be set...}` — required, no insecure fallback, deliberately kept separate from `CLICKHOUSE_PASSWORD` (the Cloud/remote credential) per an inline comment warning against accidentally rotating the local container's password on next recreate.
  - Backend service requires `CLICKHOUSE_PASSWORD` and `JWT_SECRET` via the same required-var syntax.
  - Web service maps port `3002→3000`.

No rotation or revocation of credentials was performed (none were found to rotate), and no push occurred.

## Conclusion

No real secrets are tracked in this repository. One stale hardcoded credential-shaped default in a non-production migration script was corrected to read from the environment, matching the pattern already enforced by `docker-compose.yml`. `.gitignore` and `.env` handling were already correct before this pass and required no changes.
