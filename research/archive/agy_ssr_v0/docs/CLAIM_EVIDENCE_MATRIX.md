# CLAIM / EVIDENCE MATRIX

| Claim | Claim Type | Supporting File / Artifact | Empirical Result | Status |
| :--- | :--- | :--- | :--- | :--- |
| **C1:** Standard QA models exhibit over-revision on irrelevant narrative evidence. | OBSERVED | `results/benchmark_summary.json` | Preservation Accuracy drops to 0.5600 for B1. | **VERIFIED** |
| **C2:** Generative World Simulator creates paired minimal-intervention datasets with zero ground-truth leakage. | DERIVED | `src/simulator/generator.py` | 700 paired interventions across 7 semantic types. | **VERIFIED** |
| **C3:** Selective State Revision (SSR) Engine improves preservation of unaffected states over direct models. | OBSERVED | `scripts/reproduce_all.py` | Preservation Accuracy increases from 0.5600 to 0.8000 (+24%). | **VERIFIED** |
| **C4:** Prior work (PASTA, ConStory, Belief-R) does not measure state preservation accuracy across minimal pairs. | DERIVED | `docs/RESEARCH_KILL_REPORT.md` | Comprehensive prior art audit across 16 venues. | **VERIFIED** |
