# Scientific Artifact Inventory (Phase 10)

Checklist confirming the do-not-touch scientific artifacts are present, tracked, and unmodified as of this audit. This is a status check, not an edit — nothing listed below was opened for writing.

| Artifact | Present | Tracked | Git status | Size |
|---|---|---|---|---|
| `data/eval/golden_dataset.py` | yes | yes | clean | 24K |
| `data/eval/golden_dataset_v2.py` | yes | yes | clean | 12K |
| `data/eval/corpus_manifest.json` | yes | yes | clean | 8.0K |
| `data/eval/research_experiment_scored_metrics.json` | yes | yes | clean | 16K |
| `data/eval/v2/v1_vs_v2_comparison.json` | yes | yes | clean | 4.0K |
| `data/eval/v2/v2_experiment_scored_metrics.json` | yes | yes | clean | 40K |
| `results/v2/green_mile_metrics.json` | yes | yes | clean | 56K |
| `results/v2/held_out_green_mile/green_mile_raw_output.json` | yes | yes | clean | 56K |
| `results/v2/investigator_confusion_matrix.json` | yes | yes | clean | 4.0K |
| `results/v2/per_film_metrics.json` | yes | yes | clean | 4.0K |
| `results/v2/per_rule_metrics.json` | yes | yes | clean | 4.0K |

All 9 JSON files parse successfully (`json.load` round-trip verified). All 11 files are tracked in git and show a clean status (no local modifications relative to HEAD). No file in this list was edited, regenerated, or reformatted as part of this audit pass.

**Conclusion**: the frozen V2 benchmark, Green Mile held-out evaluation, and gold-dataset artifacts are intact and unmodified. Safe to reference from `FINAL_NUMBERS_SOURCE_OF_TRUTH.md` and the patent/paper documentation.
