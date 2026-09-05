# Deployment Readiness — What Changed (2026-09-02 → 2026-09-03)

This document summarizes everything done to take StoryTrace from "works on
my machine during dev" to "runs as three Docker services with auth, rate
limiting, tests, and a populated demo experience for new users." It covers
both the planned hardening work and the real bugs found and fixed while
actually running it end-to-end.

## 1. Session & auth hardening

- **Session-expiry handling** (`apps/web/src/lib/api.ts`, `src/lib/auth.tsx`):
  the shared API client now treats a 401 on an *authenticated* request as an
  expired JWT (24h lifetime) — it clears the stored token and redirects to
  `/login`. A 401 on the login/signup call itself (bad credentials) is not
  confused with this, since no token was sent on that request.
- **Rate limiting** (`backend/api/main.py`, `requirements.txt`): `/auth/login`
  and `/auth/signup` are limited to 5 requests/minute per IP via `slowapi`,
  returning `429` once exceeded. In-memory per-process — will not hold a
  shared limit across multiple backend replicas without a Redis-backed store.
- **Signup race mitigation** (`backend/api/main.py`, `backend/clickhouse/client.py`):
  ClickHouse's `users` table has no real unique constraint. Signup now
  re-checks after insert — `get_earliest_user_id_for_email` finds whichever
  row for that email was written first; if this request didn't win, it's
  rejected with `409` instead of silently creating a duplicate account. This
  narrows the race window but cannot close it entirely (documented inline
  in the signup handler).

## 2. Deployment packaging

- **`Dockerfile`** (backend): Python 3.12-slim, installs `requirements.txt`,
  runs uvicorn.
- **`apps/web/Dockerfile`**: multi-stage Next.js build using `output: "standalone"`
  (added to `next.config.ts`).
- **`docker-compose.yml`**: three services — `clickhouse`, `backend`, `web` —
  wired with healthchecks and `depends_on: condition: service_healthy`.
- **`.dockerignore`** (root + `apps/web/`): keeps build contexts small.

### Bug found while validating: `.dockerignore` broke the web build

Both Dockerfiles build from the **repo root** as context (so the backend
image can `COPY backend/`). The root `.dockerignore` originally excluded all
of `apps/web/` to keep the backend build lean — but that same ignore file
also applies to the web image's build, so `COPY apps/web/ ./` had nothing to
copy and the build failed outright. Fixed by narrowing the exclusion to just
`apps/web/node_modules/` and `apps/web/.next/` (the actual heavy/generated
directories), not the whole app.

### Bug found while validating: CORS blocked sign-in

`FRONTEND_ORIGIN` (used by the backend's CORS middleware) defaulted to
`http://localhost:3000`. Ports 3000 and 3001 were both already occupied by
other local processes on the test machine, so the `web` container was
actually reachable at `http://localhost:3002` — a mismatched origin, so the
browser's preflight `OPTIONS` request was rejected with `400` and no
signup/login request ever reached the backend. Fixed by setting
`FRONTEND_ORIGIN=http://localhost:3002` in `.env` to match wherever `web`
actually ends up bound, and restarting the `backend` container to pick it up.
**Takeaway for future deploys:** `FRONTEND_ORIGIN` must always match the
*actual* browser-facing URL of the frontend, not an assumed default.

### Bug found while validating: Ollama unreachable from the backend container

Three layered problems, found by actually running a document through the
pipeline with `MODEL_PROVIDER=ollama`:

1. Ollama was running bound to `127.0.0.1:11434` only — not reachable from
   any container regardless of networking mode. Fixed by restarting it with
   `OLLAMA_HOST=0.0.0.0:11434`.
2. A leftover watchdog shell loop from an earlier session kept respawning
   Ollama on the default (loopback-only) binding every time it was killed —
   had to be killed too before the fix would stick.
3. Even after Ollama listened on all interfaces, the host's firewall
   silently dropped traffic forwarded from the Docker bridge network to a
   host-bound port (curl from the host to the bridge gateway IP worked;
   the same call from inside the container timed out). Fixed by switching
   the `backend` service to `network_mode: host` in `docker-compose.yml`
   (documented inline) — it now reaches ClickHouse and Ollama via
   `localhost` directly, sidestepping the bridge and its firewall rule
   entirely. No sudo/firewall changes were made to the host.

**Takeaway:** `docker compose config` validating and images building cleanly
is not the same as the services actually being able to talk to each other or
to host-bound dependencies — only a real end-to-end run surfaces that.

## 3. Tests

- `tests/unit/test_auth_api.py` (7 tests): signup success/short-password/duplicate/
  race-loss, login success/invalid, rate-limit trip.
- `tests/unit/test_projects_api.py` (6 tests): project listing, version auth
  (403/200), diff (first-version/unknown-version), report markdown.
- All 13 pass via FastAPI's `TestClient` with ClickHouse mocked.

## 4. UI polish

Dashboard and project-version pages (not the already-polished analysis view)
got loading skeletons, real empty states (icon + copy + CTA), and a
responsive pass for mobile widths, matching the existing Tailwind design
language.

## 5. Live pipeline run — 3 demo datasets

To sanity-check the full stack (ClickHouse → backend → Ollama → investigation
agent → frontend), three small documents were run through the pipeline
end-to-end under `docker compose`:

| Dataset | Units | Entities | Conflicts found | Result |
|---|---|---|---|---|
| `data/test_documents/controlled_test.txt` | 17 | 4 | 2 | Cole's gun reappears after being lost with no bridging scene; his arm wound heals with no bridging scene — both flagged `uncertain` (the investigation agent hit its 6-tool-call cap without resolving them) |
| `data/test_documents/controlled_test_v2.txt` | 18 | 5 | 2 | Same two conflicts persist; this version also introduces 2 props |
| `demo/screenplay.pdf` | 5 | 1 | 0 | Clean — no continuity issues detected |

These are genuinely-computed results (not fabricated for demo purposes) —
real narrative units, entities, state events, and investigation verdicts
computed by the actual pipeline against local Ollama (`qwen2.5:7b`). The
`uncertain` verdicts on the controlled tests are an accurate reflection of a
known, disclosed limitation: local Ollama investigation is materially weaker
than Gemini at resolving ambiguous candidates within the 6-tool-call budget.

The 3 larger screenplays in `data/test_documents/` (`gladiator.txt`,
`pulp_fiction.txt`, `seven.txt`, ~150-300KB each) were **not** run — each
would take substantially longer with local Ollama (one LLM call per scene,
hundreds of scenes) and were out of scope for a smoke test.

## 6. Default demo projects for every account

Per request, the 3 dummy runs above are no longer one-off — they're now
seeded as **permanent default projects on every user account**, existing and
future:

- `backend/seed_demo_projects.py` clones the 3 source runs (narrative units,
  entities, state events, candidate conflicts, verdicts, processing status,
  project + version) into a fresh, fully independent copy scoped to a target
  user, via ClickHouse `INSERT ... SELECT` with `replaceAll()` re-scoping the
  id columns (entity/candidate/unit ids embed the source project_id or
  story_universe_id as a string prefix, so a substring swap re-scopes an
  entire row tree without re-running any pipeline logic).
- **New signups**: `backend/api/main.py`'s `/auth/signup` handler calls
  `seed_demo_projects_for_user()` automatically right after account
  creation. Seeding failure is caught and swallowed (logged, not raised) so
  it can never block a real signup.
- **Existing accounts**: seeded once via
  `python -m backend.seed_demo_projects --all-users` (or `--user-id <id>`
  for one account). `has_demo_projects()` guards against double-seeding.
- The 3 source runs themselves (`9d442bd...` / `2a96509...` / `911d59b...`
  projects, listed by id in `backend/seed_demo_projects.py`'s
  `DEMO_SOURCES`) must not be deleted — every account's copy is cloned from
  them, on demand, not from a static snapshot.

Verified: a brand-new signup (`newsignuptest2@example.com`) immediately shows
3 projects — "Demo: Screenplay Sample" (resolved), "Demo: Controlled Test
(v1)" (warning), "Demo: Controlled Test (v2)" (warning) — with reports
byte-for-byte matching the original runs.

## Residual caveats (carried over, still true)

- No TLS/reverse proxy/domain in `docker-compose.yml` — layer one in front
  for a real deploy.
- Rate limiting won't hold across multiple backend replicas without Redis.
- ClickHouse signup race is narrowed, not eliminated.
- `MODEL_PROVIDER=gemini` is untested here (this run used `ollama`
  end-to-end) — needs its own smoke test before relying on it in prod.
- No CI — the test suite exists but nothing runs it automatically on push.
