# StoryTrace Documentation Index

A map for finding the right document quickly. Documentation is organized into
four subdirectories under `docs/` — `RESULTS/`, `RESEARCH/`, `IP/`, `HISTORY/`
— plus a set of core reference docs that stay at `docs/` root.

## Where to go for...

| Topic | Document(s) |
|---|---|
| **Architecture** (system design, components, data flow) | [`ARCHITECTURE.md`](ARCHITECTURE.md) |
| **Setup / reproducibility** (installing, running, reproducing results) | `REPRODUCIBILITY.md` *(being added separately — see repo root / docs/ once available)* |
| **V1 baseline / V1-V2 boundary** (what changed between versions and why) | [`V1_V2_BOUNDARY.md`](V1_V2_BOUNDARY.md) |
| **V2 results** (benchmark numbers, final results, statistical analysis) | [`RESULTS/`](RESULTS/) — see [`RESULTS/V2_BENCHMARK_RESULTS.md`](RESULTS/V2_BENCHMARK_RESULTS.md), [`RESULTS/V2_FINAL_RESULTS.md`](RESULTS/V2_FINAL_RESULTS.md) |
| **Green Mile held-out evaluation** | [`RESULTS/GREEN_MILE_HELDOUT_EVALUATION.md`](RESULTS/GREEN_MILE_HELDOUT_EVALUATION.md) |
| **Gold dataset methodology** (annotation process, reconciliation) | [`RESEARCH/GOLD_DATASET_RECONCILIATION.md`](RESEARCH/GOLD_DATASET_RECONCILIATION.md), [`RESEARCH/ANNOTATION_GUIDELINES.md`](RESEARCH/ANNOTATION_GUIDELINES.md), [`RESEARCH/HUMAN_ANNOTATION_WORKFLOW.md`](RESEARCH/HUMAN_ANNOTATION_WORKFLOW.md), [`RESEARCH/LLM_ASSISTED_GOLD_DATASET_REPORT.md`](RESEARCH/LLM_ASSISTED_GOLD_DATASET_REPORT.md) |
| **Statistical audit** (significance testing, robustness checks) | [`RESULTS/STATISTICAL_ANALYSIS.md`](RESULTS/STATISTICAL_ANALYSIS.md), [`RESEARCH/V2_STATISTICAL_AUDIT.md`](RESEARCH/V2_STATISTICAL_AUDIT.md) |
| **IP / patent material** (claims, prior art, disclosure) | [`IP/`](IP/) — see [`IP/PATENT_CLAIM_ARCHITECTURE.md`](IP/PATENT_CLAIM_ARCHITECTURE.md), [`IP/PRIOR_ART_MATRIX.md`](IP/PRIOR_ART_MATRIX.md), [`IP/VIT_INVENTION_DISCLOSURE_PACKAGE.md`](IP/VIT_INVENTION_DISCLOSURE_PACKAGE.md) |
| **Historical development** (dev logs, superseded status docs) | [`HISTORY/`](HISTORY/) — see [`HISTORY/DEVLOG.md`](HISTORY/DEVLOG.md), [`HISTORY/FINDINGS.md`](HISTORY/FINDINGS.md), [`HISTORY/EVAL_IMPROVEMENT_LOG.md`](HISTORY/EVAL_IMPROVEMENT_LOG.md), [`HISTORY/PIPELINE_VERIFICATION.md`](HISTORY/PIPELINE_VERIFICATION.md) |

## Directory guide

### `docs/RESULTS/` — current/final validated results
Benchmark numbers, final V2 results, the Green Mile held-out evaluation, and
the statistical analysis backing them. Read this first for "what did
StoryTrace V2 actually achieve."

### `docs/RESEARCH/` — specs, audits, methodology
Component specs (candidate detector, extraction, investigation agent),
research-integrity audits (recall, claims, design, investigator, leakage,
robustness, statistical), gold-dataset methodology and reconciliation,
annotation guidelines and workflow, error taxonomy, and paper-facing material
(`RESEARCH/paper/`, `RESEARCH/pitch/`).

### `docs/IP/` — patent/claim material
Patent claim architecture, patent readiness audit, claim red list / element
matrix / scope analysis, inventive core analysis, IP technical core, prior
art matrix, India IP filing checklist, invention disclosure, and the VIT
invention disclosure package.

### `docs/HISTORY/` — superseded/dev-log artifacts
Development logs and status snapshots from earlier phases of the project:
`DEVLOG.md`, `FINDINGS.md`, `EVAL_IMPROVEMENT_LOG.md`,
`PIPELINE_VERIFICATION.md`, `REPOSITORY_AUDIT_BEFORE.md`, and the V2 final
scientific-status/strategic-decision snapshots. These are historical records,
not current guidance — check `RESULTS/` and `ARCHITECTURE.md` for the
current state instead.

### `docs/` root — core reference docs (not moved)
`ARCHITECTURE.md`, `SECURITY_AUDIT.md`, `DEPENDENCY_AUDIT.md`,
`DEAD_CODE_AUDIT.md`, `V1_V2_BOUNDARY.md`, `PATH_LOGGING_CLI_AUDIT.md`,
`SCIENTIFIC_ARTIFACT_INVENTORY.md`, `data-model.md`, `design.md`,
`agent.md`, `investigation.md`, `deployment-improvements.md`.

## Note on `EVAL_REPORT.md`

`EVAL_REPORT.md` at the repository root is **not** part of this index's
directory structure. It is a live, regenerated artifact — `scripts/eval`
rewrites it to the repo root every time `python3 -m scripts.eval` runs — so
it intentionally stays at root rather than living under `docs/RESULTS/`.
