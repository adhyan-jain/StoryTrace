# Final Repository Tree

Important directories/files after the cleanup pass (excludes `.git`, `venv/`, `node_modules/`, `__pycache__/`, `.pytest_cache/`, `.next/`, build/test-result caches, and personal tool caches like `graphify-out/`, `.claude/`, `.agents/`).

```
StoryTrace/
├── README.md                    Entry point: architecture, auth, setup, evaluation, deployment
├── CLAUDE.md / AGENTS.md         Development guidelines
├── LICENSE
├── EVAL_REPORT.md                Live output of `python3 -m scripts.eval` (regenerated at repo root by design)
├── requirements.txt              Python dependencies (see docs/DEPENDENCY_AUDIT.md)
├── pytest.ini                    testpaths = tests (fixed this pass, see DEAD_CODE_AUDIT.md)
├── docker-compose.yml / Dockerfile
│
├── backend/                      Python backend
│   ├── ingestion/                NarrativeUnit model + PDF/EPUB/Fountain/plain-text parsers
│   ├── llm/                      LLM provider abstraction (Ollama / Gemini / Vertex AI)
│   ├── pipeline/                 State extraction, entity resolution, integrity checks
│   ├── clickhouse/                ClickHouseClient (temporal engine wrapper) + schema.sql
│   ├── candidate_detection/       SQL window-function conflict detector (V1)
│   ├── agent/                     InvestigationAgent (V1) + MCP-backed ClickHouse tools
│   ├── api/                       FastAPI app (main.py) -- live runtime, wires V1 modules
│   ├── auth.py                    Signup/login, JWT
│   ├── story_state/                V1 state models
│   ├── eval/                       Ablation-only extractor/investigator variants
│   └── v2/                         Parallel V2 implementation (eval-only, see V1_V2_BOUNDARY.md)
│
├── apps/web/                      Next.js frontend (App Router)
│
├── scripts/
│   ├── eval/                      V1 evaluation harness (python3 -m scripts.eval)
│   ├── v2/                        V2 evaluation/audit harness (run_v2_eval.py, audit_*.py, ...)
│   ├── migrate_to_cloud.py        ClickHouse Cloud migration (password fixed this pass)
│   ├── generate_ri_parsed_dataset.py  Relocated/renamed this pass (was mislabeled test_ri.py)
│   └── (other one-off pipeline/demo scripts)
│
├── tests/
│   ├── unit/                       auth, projects, pipeline correctness/integrity (V1)
│   └── v2/                         candidate detector, extractor, investigator, models (V2)
│   (tests/benchmark/ and tests/unit/test_llm.py removed this pass -- see DEAD_CODE_AUDIT.md)
│
├── data/                           Mostly gitignored; only eval config/gold data tracked
│   ├── eval/
│   │   ├── golden_dataset.py / golden_dataset_v2.py   Tracked (gitignore allowlist)
│   │   ├── corpus_manifest.json                        Tracked
│   │   ├── gold_dataset_v3.json                        Tracked -- 989 verified gold items
│   │   └── screenplays/                                 Gitignored (licensed source text)
│   ├── raw/, processed/, annotation/, test_documents/   Gitignored
│   └── stage/                                           Gitignored; contains its own nested
│                                                          .git (flagged, not touched)
│
├── results/v2/                    Frozen V2 benchmark/Green-Mile output JSON (untouched)
│
└── docs/
    ├── ARCHITECTURE.md            Current implementation (this pass)
    ├── V1_V2_BOUNDARY.md          Flags that main.py wires V1, not V2, into the live API
    ├── DEAD_CODE_AUDIT.md
    ├── SECURITY_AUDIT.md
    ├── DEPENDENCY_AUDIT.md
    ├── TEST_AUDIT.md
    ├── REPRODUCIBILITY.md
    ├── PATH_LOGGING_CLI_AUDIT.md
    ├── SCIENTIFIC_ARTIFACT_INVENTORY.md
    ├── FINAL_NUMBERS_SOURCE_OF_TRUTH.md   Flags one unresolved discrepancy (investigator max tool calls)
    ├── FINAL_REPOSITORY_AUDIT.md
    ├── FINAL_REPOSITORY_TREE.md    (this file)
    ├── DOCUMENTATION_INDEX.md      Map of the tree below
    ├── data-model.md, design.md, agent.md, investigation.md, deployment-improvements.md
    │
    ├── RESULTS/                    Current/final validated results
    │   ├── V2_BENCHMARK_RESULTS.md, V2_FINAL_RESULTS.md
    │   ├── GREEN_MILE_HELDOUT_EVALUATION.md
    │   └── STATISTICAL_ANALYSIS.md
    │
    ├── RESEARCH/                   Specs, audits, methodology, paper drafts
    │   ├── V2_*_SPEC.md, V2_*_AUDIT.md
    │   ├── GOLD_DATASET_RECONCILIATION.md, ANNOTATION_GUIDELINES.md, ERROR_TAXONOMY.md
    │   └── paper/, pitch/
    │
    ├── IP/                         Patent/claim material
    │   ├── PATENT_CLAIM_ARCHITECTURE.md, PATENT_READINESS_AUDIT.md
    │   ├── CLAIM_*.md, PRIOR_ART_MATRIX.md, INVENTIVE_CORE_ANALYSIS.md
    │   ├── VIT_INVENTION_DISCLOSURE_PACKAGE.md  (deduped this pass, was 2 identical copies)
    │   └── invention_disclosure.md
    │
    └── HISTORY/                    Superseded/dev-log artifacts (not live outputs)
        ├── DEVLOG.md, FINDINGS.md, EVAL_IMPROVEMENT_LOG.md, PIPELINE_VERIFICATION.md
        ├── REPOSITORY_AUDIT_BEFORE.md  (baseline snapshot, this pass)
        └── V2_FINAL_SCIENTIFIC_STATUS.md, V2_FINAL_STRATEGIC_DECISION.md
```

## Known intentional exceptions (documented, not oversights)

- `EVAL_REPORT.md` stays at repo root -- `scripts/eval/__main__.py` writes there by hardcoded relative path; moving the doc would create a stale duplicate.
- Several `scripts/v2/*.py` (`compare_v1_v2.py`, `audit_statistical.py`, `audit_robustness.py`, `audit_investigator.py`, `run_held_out_green_mile.py`) and `scripts/eval/score_final_experiment.py` still hardcode output paths into the pre-reorg flat `docs/` location (e.g. `docs/V2_BENCHMARK_RESULTS.md`). Left untouched -- redirecting them is a source-code behavior change, out of scope. If any of them are rerun, they will recreate a file at the old flat path, diverging from the reorganized copy under `RESULTS/`/`RESEARCH/`.
- `data/stage/` contains its own nested `.git` -- flagged, not touched (outside this pass's scope, likely a separate corpus-staging working copy).
