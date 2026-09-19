# StoryTrace V2: Final Strategic Decisions & Roadmap

**Date:** September 19, 2026  
**Auditor:** Antigravity Executive IP & Academic Publishing Group  
**Status:** **APPROVED & FROZEN (READY FOR PROVISIONAL PATENT FILING & PAPER SUBMISSION)**  

---

## 1. Twelve Executive Strategic Decisions

```
+----+---------------------------------------------------+--------------------+------------------------------------------------------------------+
| #  | STRATEGIC QUESTION                                | DECISION / VERDICT | EVIDENCE & RATIONALE                                             |
+----+---------------------------------------------------+--------------------+------------------------------------------------------------------+
| 1  | Should StoryTrace V2 now be frozen?               | **YES (FROZEN)**   | Commit 4064cf7 is fully validated with 114/114 passing tests.    |
| 2  | Is another engineering phase justified?           | **NO**             | Further tuning risks overfitting and invalidates frozen data.    |
| 3  | Is current architecture sufficient for paper?     | **YES**            | Complete 10-film x 5-condition ablation + Green Mile held-out.   |
| 4  | What is the strongest paper contribution?         | **C5 & C2**        | Proving structured state expansion solves the recall bottleneck. |
| 5  | What is the strongest potential patent core?      | **Level 5 Core**   | Coupling OLAP SQL window anomaly rules with bounded FastMCP agent|
| 6  | What is the closest prior art?                    | **ATLAS & US 11M** | ATLAS (temporal graph) & US 11,256,928 (script NLP AI).          |
| 7  | What parts are clearly not novel?                 | **Components**     | LLMs, SQL, ClickHouse, MCP, RAG, and regex parsing in isolation. |
| 8  | What combination is most defensible?              | **Synergistic Core**| Hierarchical State -> OLAP Store -> SQL Window -> FastMCP Agent. |
| 9  | What evidence belongs in patent specification?    | **System Artifacts**| SQL rules, schema DDL, FastMCP tool specs, execution traces.     |
| 10 | What evidence belongs in research paper?          | **Empirical Data** | A/B/C/D vs V2 ablation, confusion matrix, permutation p-values.  |
| 11 | Should patent filing precede paper submission?    | **YES (CRITICAL)** | India has no general academic grace period; Form 2 must precede. |
| 12 | What artifacts go to VIT IPR Cell?                | **IP Package**     | IP_TECHNICAL_CORE, PRIOR_ART_MATRIX, PATENT_CLAIM_ARCHITECTURE.  |
+----+---------------------------------------------------+--------------------+------------------------------------------------------------------+
```

---

## 2. Integrated Strategy Summary

### A. Patent Strategy:
- **Core Claim Target:** A computer-implemented system coupling an append-only relational state store with parameterized SQL analytical window anomaly detectors ($O(1)$ inference cost) and a tool-augmented ReAct agent operating under a strict hard bound ($k \le 6$) and two-tier calibrated verdict space.
- **Filing Venue:** Indian Patent Office (IPO) through Vellore Institute of Technology (VIT) IPR Cell.
- **Timing:** File Provisional Patent Application (Form 1 & Form 2) **prior** to any public paper release.

### B. Paper Strategy:
- **Title:** *StoryTrace: Resolving Representational Bottlenecks in Long-Form Narrative Continuity Verification via Neurosymbolic State Tracking and Bounded Agentic Adjudication*
- **Target Venues:** ACL 2027 / EMNLP 2026 / NAACL 2027 / ACM Multimedia.
- **Core Narrative:** How expanding state representation from flat macroscopic tags to hierarchical temporal-spatial models converts an 8.49% recall ceiling into an 82.10% addressable space, demonstrating the superiority of structured verification over unconstrained LLMs ($0.7821$ vs $0.1333$ F1, $p < 0.001$).

### C. Prior-Art Risk Assessment:
- **Risk Level:** **LOW TO MODERATE**.
- Standard NLP components (LLM, RAG, embeddings) are heavily crowded, but the specific neurosymbolic bridge between columnar OLAP window functions and bounded MCP tool investigation is entirely unencumbered in published literature and patent disclosures.

---

## 3. Immediate Next 3 Actions

```
[ACTION 1: Hand-Off IP Package to VIT IPR Cell]
Submit docs/IP_TECHNICAL_CORE.md, docs/PRIOR_ART_MATRIX.md, docs/PATENT_CLAIM_ARCHITECTURE.md,
and docs/INDIA_IP_CHECKLIST.md to VIT IPR Cell for internal review and Form 1/Form 2 drafting.

[ACTION 2: Draft Academic Research Paper]
Assemble full paper manuscript using docs/PAPER_CONTRIBUTIONS.md, docs/PAPER_EXPERIMENTAL_STORY.md,
and docs/V2_FINAL_RESULTS.md following ACL/EMNLP LaTeX format.

[ACTION 3: Coordinated Filing & Submission]
Secure Provisional Patent Application Filing Number at the Indian Patent Office, then immediately
submit the finalized paper to target conference / arXiv.
```
