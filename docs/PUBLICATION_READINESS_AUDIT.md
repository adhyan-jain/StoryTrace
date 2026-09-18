# Publication Readiness Audit & Research Checklist

**Target Venue:** EMNLP / ACL / NAACL 2027 (System Demonstration / Empirical NLP Track)  
**Project:** StoryTrace (Multi-Document Narrative Continuity Verification Engine)  
**Author:** Adhyan Jain (VIT Vellore)  
**Date:** September 18, 2026  

---

## 1. Publication Readiness Checklist (20 Items)

```
+--------------------------------------------------------------------------------------------------+
|                                  PUBLICATION STATUS OVERVIEW                                     |
+--------------------------------------------------------------------------------------------------+
|                                                                                                  |
|   [ALREADY COMPLETE]                                                                             |
|   ├── Core Architecture & Pipeline (Parser -> Closed Extractor -> ClickHouse -> Detector -> MCP)|
|   ├── Frozen 10-Film Benchmark Framework & A/B/C/D Ablation Protocol                             |
|   ├── Automated Metric Scoring Engine (Micro/Macro P/R/F1, Candidate Stage, Verbatim Grounding)  |
|   └── Initial Preflight & Phase 0 Validation Runs                                                |
|                                                                                                  |
|   [NEEDS ANALYSIS] (Pending Active Run Completion)                                               |
|   ├── Final 10-film aggregate numerical matrices across Conditions A, B, C, D                    |
|   ├── Paired Statistical Significance Tests (Permutation / Paired Bootstrap p-values)            |
|   └── Multi-hop / Long-range temporal span correlation analysis                                  |
|                                                                                                  |
|   [NEEDS WRITING]                                                                                |
|   ├── Final LaTeX tables & figure generation for paper draft                                     |
|   ├── Qualitative Error & Failure Taxonomy Discussion                                            |
|   └── Methodological Limitations & Model Provider Fairness Section                              |
|                                                                                                  |
|   [OPTIONAL STRENGTHENING]                                                                       |
|   ├── Multi-Annotator Inter-Annotator Agreement (IAA) Study (Cohen's / Fleiss' kappa)            |
|   └── Frontier Multi-Model Comparison (Gemini 1.5 Pro / GPT-4o vs Qwen-2.5-7B)                  |
+--------------------------------------------------------------------------------------------------+
```

### Detailed Itemized Audit

| # | Item Description | Status Category | Implementation Reference / Action Item |
| :--- | :--- | :---: | :--- |
| **1** | **Final 10-Film A/B/C/D Raw Results** | `NEEDS ANALYSIS` | 25/40 runs complete; actively processing Film 7–10 in background. |
| **2** | **Micro Precision / Recall / F1** | `ALREADY COMPLETE` | Implemented in [`scripts/eval/score_final_experiment.py`](file:///home/adhyan/Desktop/StoryTrace/scripts/eval/score_final_experiment.py). |
| **3** | **Macro Precision / Recall / F1** | `ALREADY COMPLETE` | Implemented in [`scripts/eval/score_final_experiment.py`](file:///home/adhyan/Desktop/StoryTrace/scripts/eval/score_final_experiment.py). |
| **4** | **Per-Film Metric Breakdown** | `ALREADY COMPLETE` | Generated per screenplay in `data/eval/research_experiment_scored_metrics.json`. |
| **5** | **Per-Category Metrics** | `ALREADY COMPLETE` | Categorized across `possession`, `injury`, `location`, `clothing`. |
| **6** | **Candidate-Stage Metrics** | `ALREADY COMPLETE` | Evaluates raw SQL detector output before agent adjudication. |
| **7** | **Final-Verdict Metrics** | `ALREADY COMPLETE` | Evaluates final `verified` verdicts against gold annotations. |
| **8** | **Condition A vs B Analysis** | `NEEDS WRITING` | Quantifies the exact precision gain delivered by the Investigation Agent. |
| **9** | **Condition A vs C Analysis** | `NEEDS WRITING` | Quantifies the noise reduction delivered by the closed-vocabulary grammar. |
| **10** | **Condition A vs D Analysis** | `NEEDS WRITING` | Quantifies the gain of the neurosymbolic system over a monolithic one-shot LLM. |
| **11** | **Paired Statistical Tests** | `NEEDS ANALYSIS` | Paired bootstrap resampling across 10 films ($p < 0.05$ threshold). |
| **12** | **Bootstrap Confidence Intervals** | `NEEDS ANALYSIS` | 95% CIs for Micro/Macro F1 across all conditions. |
| **13** | **Effect Size Estimation** | `NEEDS ANALYSIS` | Cohen's $d$ / Cliff's delta for runtime and precision gains. |
| **14** | **Long-Range Dependency Analysis** | `NEEDS ANALYSIS` | Correlation between scene sequence distance $(\Delta \text{seq})$ and detection accuracy. |
| **15** | **Runtime & Inference Cost Audit** | `ALREADY COMPLETE` | Tracks wall-clock seconds and token counts per condition per film. |
| **16** | **Evidence Grounding Verification** | `ALREADY COMPLETE` | Substring match check on `raw_excerpt` against `NarrativeUnit.text`. |
| **17** | **Failure Taxonomy** | `NEEDS WRITING` | Detailed categorization of False Positives and False Negatives. |
| **18** | **Gold-Set Methodology Disclosure** | `NEEDS WRITING` | **Explicitly documented in Section 2 below.** |
| **19** | **Methodological Limitations** | `NEEDS WRITING` | Documented in paper draft Section 8. |
| **20** | **Reproducibility Package** | `ALREADY COMPLETE` | Deterministic runner, frozen prompt templates, Ollama local model configs. |

---

## 2. Explicit Gold Dataset Methodology Disclosure

> [!WARNING]
> **CRITICAL METHODOLOGICAL DISCLOSURE FOR PUBLICATION INTEGRITY:**  
> The current gold standard evaluation dataset (`data/eval/gold_dataset_v3.json`) was constructed via an **LLM-assisted consensus and human-audited extraction workflow**, **NOT** a double-blind, multi-human independent annotation study.
> 
> * **Annotation Procedure**: Candidate continuity errors were initially curated using LLM-assisted multi-agent consensus prompts and subsequently audited and refined by a single human annotator.
> * **Publication Requirement**: The final paper must explicitly disclose this methodology in the *Dataset & Annotations* section. To elevate the paper to top-tier empirical NLP standards (ACL/EMNLP main conference), we recommend conducting an **Inter-Annotator Agreement (IAA) study** with 2 independent human annotators on a 20% random sample to report Cohen's $\kappa$ / Fleiss' $\kappa$.

---

## 3. Neighboring-Work Comparison Framework

To prevent flawed apples-to-oranges comparisons, the table below outlines the exact structural comparison framework to be included in the paper:

| Dimension | StoryTrace (Ours) | STAGE (2026) | ATLAS (2025) | ConStory-Checker (ACL '26) |
| :--- | :--- | :--- | :--- | :--- |
| **Primary Research Goal** | Multi-hop continuity error verification | Narrative change understanding benchmark | Dynamic character graph tracking | General narrative consistency checking |
| **Input Modality** | Full screenplay raw text (`.txt` / `.pdf`) | Dialogue & scene checkpoint Q&A | Prose narrative paragraphs | Natural language narrative text |
| **Core Representation** | Append-only OLAP event log (ClickHouse) | Narrative checkpoint questions | Dynamic Knowledge Graph (Nodes/Edges) | Raw text context window |
| **State Semantics** | **Controlled Closed Grammar** ($\Sigma_{\text{poss}}, \Sigma_{\text{inj}}$) | Free-text questions & roles | Open-vocabulary graph relations | Unstructured natural language |
| **Candidate Detection** | **Deterministic SQL (`lagInFrame`)** | N/A (Pre-defined QA) | Graph traversal & path search | Generative LLM judge pass |
| **Adjudication Method** | **Bounded ReAct Agent via MCP (max 6 calls)** | Model QA Accuracy | Path-based LLM generation | Monolithic single-pass judge |
| **Evidence Grounding** | **Verbatim sequence-indexed citations** | Multiple choice options | Retrieved graph subgraphs | Free-form explanation string |
| **Inference Cost** | Zero model calls for detection; bounded for agent | High (Multi-query QA) | High (Iterative graph updates) | Medium (Single monolithic pass) |

---

## 4. Model Fairness & Experimental Variable Isolation

A common reviewer inquiry in agentic NLP research is: *"Does the architectural contribution hold independently of the underlying foundation model?"*

### 4.1 Rigorous Theoretical & Experimental Response
1. **Model as an Experimental Variable, Not the Contribution**:
   - The foundation model (`qwen2.5:7b`) is a modular plug-in. StoryTrace's contribution is neurosymbolic and architectural: the separation of closed-vocabulary state extraction, OLAP-based SQL window detection, and bounded ReAct MCP adjudication.
2. **Controlled 4-Way Frozen Model Design**:
   - By freezing the underlying model (`qwen2.5:7b`, local Ollama, temperature 0.0) across all 4 experimental conditions (A, B, C, D) on the exact same 10 screenplays, all model-specific capabilities and biases are held strictly constant.
   - Any observed variance in precision, recall, or runtime is mathematically isolated to the architectural interventions:
     - **$\Delta(A, B)$** isolates the exact empirical value of the **Investigation Agent**.
     - **$\Delta(A, C)$** isolates the exact empirical value of the **Controlled-Vocabulary Grammar**.
     - **$\Delta(A, D)$** isolates the exact empirical value of the **Neurosymbolic Pipeline vs. Monolithic LLM**.
3. **Future Work Note**:
   - Cross-model replication across frontier models (e.g., `gemini-1.5-pro`, `gpt-4o`) is designated as **Future Work** to demonstrate scale-invariance, but the internal validity of the current architectural ablation is fully established by the frozen open-weights baseline.
