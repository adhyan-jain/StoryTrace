# StoryTrace — Build Log

A real, honest account of how this got built: what worked, what broke, and
what we learned along the way. Compiled from the actual commit history (70
commits, Aug 29 → Sep 8) and the project's own findings docs
(`FINDINGS.md`, `PIPELINE_VERIFICATION.md`, `docs/deployment-improvements.md`,
`EVAL_REPORT.md`) — nothing here is invented for the pitch.

## Timeline

### Phase 1 — Core pipeline (Aug 29)
Built the backbone in one long session: PDF parsing, ClickHouse schema,
Gemini-backed structured entity/state extraction, deterministic entity
resolution, SQL window-function candidate detection, the Investigation Agent,
FastAPI backend, and a first Next.js frontend with the Continuity Autopsy UI —
plus a Playwright e2e pass to prove it worked end to end.

### Phase 2 — Making it document-agnostic (Aug 29-30)
Renamed `screenplay_id`/`scene_id`/`scene_number` to `story_universe_id`/
`unit_id`/`sequence_number` across the entire stack so the temporal model
wasn't hardcoded to screenplays — the architecture doc was rewritten around
`NarrativeUnit`s that work for novels and chapters too, not just scenes.

### Phase 3 — Real-document testing surfaces real bugs (Aug 30-31)
Running actual chapters through the pipeline (Reverend Insanity, a 501-chapter
web novel) immediately found things a synthetic test never would have:
- An O(N²) string-concatenation bug in `NovelParser` that only showed up at
  real chapter-count scale.
- The extraction prompt logging an injury on the *attacker* instead of the
  *victim* ("Fang Yuan had beheaded the puppet!" → wrongly attributed to Fang
  Yuan) — fixed with an explicit injury-attribution rule.
- Free-form attribute values (`possession.silver pistol` vs `possession.gun`
  for the same prop) breaking the detector's exact-match window function —
  led to constraining `possession`/`injury` values to a closed vocabulary
  and switching to dotted attributes.
- Gemini's free tier turned out to be capped at **20 requests/day per
  project per model** (not just per-minute — only discovered via a live 429
  naming the exact quota). That cap was exhausted mid-run on the very first
  controlled-test attempt, wiping a run that had already caught a real
  planted error. Every subsequent test that day ran on local Ollama
  (`qwen2.5:7b`) instead, out of necessity.

### Phase 4 — Agent wiring, MCP, and the honesty of failure (Sep 1)
The Investigation Agent was rewired to genuinely call ClickHouse through a
real `mcp-clickhouse` MCP stdio server instead of a direct client. This is
also where the project's failure modes got documented instead of hidden:
- The local model, acting as the investigation agent, regularly **hit its
  6-tool-call budget without reaching a verdict** — logged honestly as
  `uncertain, "Max tool calls reached"` rather than papered over.
- One real tool call was observed passing `entity_id: 'gun'` (a guess from
  prose, not the real DB key) and got 0 rows back — correct behavior for a
  garbage query, but proof the agent needed the literal entity_id/attribute
  handed to it in-context rather than left to infer.
- Three separate attempts to run the full pipeline against a real screenplay
  (Se7en, substituted for The Dark Knight, which turned out not to be hosted
  on IMSDB at all — disclosed rather than silently swapped) **failed outright**:
  the local Ollama server silently stopped responding partway through each
  multi-hour background run, with no crash log and no confirmable OOM. This
  was reported as an environment/sandbox limitation, not quietly retried
  until it looked fine.
- Later, a paid run against a larger document through the metered API (rather
  than the Ollama/free-tier path) burned real spend — on the order of single-digit
  dollars — without producing meaningfully better pipeline results than the
  free local runs. That's part of why Vertex AI (project-billed, ADC-authenticated,
  no daily cap) was later added as a third provider alongside Gemini's free
  tier and local Ollama — so a real evaluation run could be budgeted deliberately
  instead of hitting an unpredictable quota wall or an unplanned bill mid-run.

### Phase 5 — Auth, projects, and a real product shape (Sep 2)
Email/password auth with JWT, a projects/versions data model, a dashboard,
and version-to-version diffing (so re-uploading a revised draft shows what
changed) — the point where this stopped being a CLI pipeline and became an
actual web product.

### Phase 6 — Production hardening (Sep 3-5)
Vertex AI as a third LLM provider, batched/parallel extraction (a full
screenplay run went from 20+ minutes to single digits), rate limiting,
signup-race mitigation, Docker packaging, and a full visual redesign into the
current noir case-file aesthetic. Also where real deployment bugs got found
and fixed by actually running the stack end-to-end rather than trusting
`docker compose config`:
- `.dockerignore` excluding all of `apps/web/` broke the *web* image's build,
  because both Dockerfiles share the same root build context.
- `FRONTEND_ORIGIN` CORS mismatch silently blocked every login/signup
  preflight request when the frontend ended up on a different port than
  assumed.
- Ollama bound to `127.0.0.1` only, a leftover watchdog script re-binding it
  right back to loopback after every kill, and finally a host firewall
  silently dropping bridge-network traffic — three stacked networking bugs
  that only "actually running a document through the pipeline" surfaced, not
  static config validation. Fixed by moving the backend to
  `network_mode: host`.

### Phase 7 — Schema robustness and PDF reports (Sep 6)
Investigation tool-calling and verdict parsing made resilient to malformed
model output — a bad tool call or unparseable action used to abort the whole
investigation loop; it now logs the error and lets the agent retry within
its call budget instead of losing the rest of its budget to one mistake. The
continuity report also switched from Markdown to a real PDF.

### Phase 8 — Honest evaluation (Sep 8)
Built a real precision/recall/F1 evaluation framework (`scripts/eval/`)
against a hand-verified golden dataset, run against the live pipeline (not
mocked) — plus an adversarial baseline that strips the extraction prompt's
vocabulary/few-shot examples to quantify what that engineering is actually
worth (0.174 F1 with it vs 0.000 without, on a 5-unit sample).

## The Good

- **Every documented finding is from a real run.** No fabricated demo data —
  `FINDINGS.md`, `PIPELINE_VERIFICATION.md`, and `EVAL_REPORT.md` all state
  this explicitly and back it with real logs, real SQL output, and real
  extracted facts, including honest zeros (Pulp Fiction and Gladiator
  genuinely produced 0 candidates, and that's reported as such, not hidden).
- **The MCP-backed Investigation Agent is real**, not a stub — verified live
  `mcp-clickhouse` tool calls, with the full trace (tool, SQL, row count,
  timestamp) surfaced in the UI's Autopsy panel for provenance.
- **Prompt engineering measurably matters**: the vocabulary + few-shot
  extraction prompt outperforms an unconstrained prompt by a wide margin in
  the adversarial eval, and the controlled vocabulary (verified via direct
  ClickHouse query in `PIPELINE_VERIFICATION.md`) holds 100% for
  `possession`/`injury` values.
- **Real bugs found by real runs, not by inspection**: the O(N²) parser bug,
  the injury-attribution bug, three separate Docker networking bugs, and the
  CORS/dockerignore bugs were all caught by actually executing the pipeline
  end-to-end, which is exactly what this project claims to do for narrative
  continuity.
- **Resilience work paid off**: investigation tool-calling failures no longer
  abort a whole investigation — they're retried within budget, which is
  itself dogfooding the project's own "don't silently give up" philosophy.

## The Bad (disclosed honestly, not smoothed over)

- **Gemini's free tier (20 requests/day) was exhausted mid-testing more than
  once**, forcing a fallback to a materially weaker local model (Ollama
  `qwen2.5:7b`) for most controlled-test and screenplay runs — which is
  directly why several investigation verdicts came back `uncertain` instead
  of resolved: the local model couldn't reliably complete a 6-step
  tool-calling loop with well-formed arguments.
- **A paid API run against a larger document cost real money (roughly
  single-digit dollars) without producing results meaningfully better than
  the free-tier/local runs** — an expensive way to confirm that model choice,
  not just prompt/detector quality, was a real bottleneck at that point in
  development.
- **Three multi-hour background runs against a full real screenplay (Se7en)
  all silently died** partway through in the dev sandbox — never resolved
  in that environment, reported as an unmet goal rather than faked.
- **The SQL candidate detector only ever checks two hardcoded transition
  patterns** (`possession: lost→held`, `injury: injured→healed`). It has no
  location-contradiction rule at all, so a Chicago→New York jump with no
  travel scene is structurally invisible to it — a known, disclosed scope
  gap, not a bug.
- **Free-form attribute naming still causes real fragmentation**: the same
  injury has shown up as `injury.right_forearm`, `injury.arm`, and
  `injury.arm.forearm` across different runs of the same document, and the
  detector's exact `(entity, attribute)` partitioning means these never line
  up as one sequence.
- **Headline eval numbers are currently low** (Overall F1 0.347 as of the
  Sep 8 eval run) — driven partly by real extraction/detection gaps and
  partly by the golden dataset only curating ~10 "notable" facts rather than
  every true fact in the test document, which structurally penalizes correct
  extractions that simply weren't added to the fixture.
- **ClickHouse has no true unique constraint**, so the signup duplicate-email
  race is narrowed, not eliminated; rate limiting is in-memory per-process
  and won't hold across replicas without Redis. Both are disclosed
  limitations, not silent gaps.

## Where it stands now

Three LLM providers (Gemini API, Vertex AI, local Ollama) behind one
`LLMProvider` interface so cost/quota/latency tradeoffs are a config switch,
not a rewrite. Full Docker Compose deployment (ClickHouse + FastAPI + Next.js)
with auth, rate limiting, version diffing, PDF reports, and a real evaluation
framework gating quality with actual numbers instead of vibes. The
"$9 lesson" fed directly into that provider abstraction — the fix wasn't
"stop testing," it was "make it possible to choose the right-priced model for
the job."
