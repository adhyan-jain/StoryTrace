# Repository Audit — Baseline (Before Cleanup)

Captured: 2026-09-19, prior to the final repository audit/cleanup/documentation-freeze pass.

## Git State

- **Branch**: `v2-development`
- **HEAD**: `e330db898475f5d4db1eb55ab5637c2cdc480883`
- **Working tree**: clean (no staged/unstaged changes; only gitignored paths present)
- **Remote**: `origin` → `git@github.com:adhyan-jain/StoryTrace.git`
- **Local branches**: `main`, `v2-development` (current), `backup-before-coauthor-strip`
- **Remote branches**: `origin/main`, `origin/v2-development`
- **Tags**: none

## Test Status

`python3 -m pytest -q` → **115 passed, 0 failed**, 5 deprecation warnings (httpx/starlette, google-genai, slowapi — all from third-party dependency code, not project code).

Note: `README.md` currently states "114/114" in its reproducibility section; the true collected/passing count is 115. This is a documentation correction to make in Phase 8, not a test change.

## Repository Size

Total (excluding `.git`): ~2.1G

| Directory | Size |
|---|---|
| `apps/` (incl. `node_modules/`) | 1010M |
| `venv/` | 539M |
| `data/` | 582M |
| `graphify-out/` | 2.8M |
| `.playwright-mcp/` | 4.0M |
| `backend/` | 820K |
| `scripts/` | 760K |
| `tests/` | 552K |
| `docs/` | 488K |
| `results/` | 124K |

`venv/`, `apps/web/node_modules/`, and most of `data/` are gitignored (dependency installs / regeneratable corpora) and do not affect the tracked repo size.

## File Counts

- Python files under `backend/`, `scripts/`, `tests/`: **94**
- Markdown files under `docs/`: **46** (see full listing in `DOCUMENTATION_INDEX.md`, written in Phase 9)
- Root-level Markdown reports: `AGENTS.md`, `CLAUDE.md`, `DEVLOG.md`, `EVAL_IMPROVEMENT_LOG.md`, `EVAL_REPORT.md`, `FINDINGS.md`, `PIPELINE_VERIFICATION.md`, `README.md`

## Ignored/Untracked Paths (sample, via `git status --ignored`)

`.claude/`, `.env`, `.playwright-mcp/`, `.pytest_cache/`, all `__pycache__/` dirs (project-wide), `apps/web/.env.local`, `apps/web/.next/`, `apps/web/node_modules/`, `apps/web/playwright-report/`, `apps/web/test-results/`, `data/annotation/`, `data/processed/`, `data/raw/`, `data/stage/`, `data/test_documents/`, `data/eval/screenplays/*.txt` (13 screenplay corpus files), `graphify-out/`.

All of the above are correctly gitignored per the root `.gitignore`'s `data/*` allowlist pattern (only `data/eval/golden_dataset*.py` and related eval config are tracked).

## Suspicious/Generated Files, Markers Found

- **TODO/FIXME/HACK/XXX**: one match — `scripts/eval/generalization_test.py:60`, a literal string `"TODO (human): ..."` inside a data field (a template placeholder for human annotators), not an actual code TODO. No other markers found across `backend/`, `scripts/`, `tests/`.
- **Dead-code candidates**: `tests/benchmark/` (5 files) and part of `tests/unit/test_llm.py` import an unvendored `echotales` package; already documented as unrunnable in `README.md` and excluded from collection via `pytest.ini`. Full classification in `DEAD_CODE_AUDIT.md`.
- **Duplicate files**: `docs/VIT_INVENTION_DISCLOSURE_PACKAGE.md` and `docs/patent/VIT_INVENTION_DISCLOSURE_PACKAGE.md` (same filename, two locations) — resolved in Phase 9.
- **Stale/overlapping docs**: heavy cluster of `V2_*_AUDIT.md` / `*_FINAL_*.md` research-log files in `docs/` (14 `V2_*` files, several `FINAL`-named) — reorganized, not deleted, in Phase 9.
- **Config/secrets risk**: `scripts/migrate_to_cloud.py:33` hardcodes `password="admin"` as a local ClickHouse migration default (dev-only script, not a live credential, not a tracked secret) — addressed in Phase 4/5.
- **Nested git repo**: `data/stage/` contains its own `.git` directory — flagged only, not modified (outside cleanup scope; likely a separate working copy for corpus staging).
- **Dev debug artifacts**: `.playwright-mcp/` holds ~90 dated console-log/snapshot files from prior interactive debugging sessions — gitignored and untracked; candidate for local deletion in Phase 14 since it holds no tracked/shared state.

No secrets (API keys, tokens, passwords, private keys) were found in tracked files. See `SECURITY_AUDIT.md` (Phase 5) for full detail.
