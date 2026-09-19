# Comprehensive Prior Art Landscape Matrix: Publications & Patents

**Project:** StoryTrace V2 (Neurosymbolic Narrative Continuity Verification Engine)  
**Date:** September 19, 2026  
**Search Scope:** Academic NLP/AI Literature (ACL, EMNLP, NAACL, AAAI, IEEE, ACM, arXiv) & Global Patent Databases (USPTO, WIPO, EPO, IPO)  

---

## 1. Academic Literature Prior Art Landscape

```
+------------------------------------+---------------------------------------------------------------+-----------------------------------+---------------------------------------------------------------+-------------------------------+
| REFERENCE RECORD                   | CORE TECHNICAL DISCLOSURE                                     | OVERLAP WITH STORYTRACE V2        | TECHNICAL DISTINCTION IN STORYTRACE V2                        | NOVELTY / RISK STATUS         |
+------------------------------------+---------------------------------------------------------------+-----------------------------------+---------------------------------------------------------------+-------------------------------+
| STAGE (Deng et al., 2026)          | Benchmark of 151 movies for character tracking & QA over      | Screenplay scene segmentation and | STAGE is a QA evaluation benchmark dataset, NOT an automated  | KNOWN BENCHMARK               |
| arXiv:2601.08510                   | screenplay state changes.                                     | entity tracking.                  | verification engine. Has no SQL rules or investigator agent.  | (Non-competing reference)     |
+------------------------------------+---------------------------------------------------------------+-----------------------------------+---------------------------------------------------------------+-------------------------------+
| ATLAS (Yuan et al., 2024/2025)     | Builds dynamic temporal knowledge graphs over narrative text  | Temporal tracking of entities and | Relies on probabilistic graph embeddings. Lacks closed state  | PARTIAL OVERLAP               |
| arXiv:2410.05558                   | using LLM extraction and vector graph traversal.              | sequential scenes.                | grammar, zero-LLM SQL window rules, and bounded FastMCP agent.| (Representation overlaps)     |
+------------------------------------+---------------------------------------------------------------+-----------------------------------+---------------------------------------------------------------+-------------------------------+
| ConStory-Checker (Wang et al.,2026)| Monolithic single-stage LLM-as-a-judge consistency scoring    | Narrative contradiction detection | Conflates discovery and verification in single generative call| PARTIAL OVERLAP               |
| arXiv:2603.05890 (ACL 2026)        | over narrative text spans (F1: 0.678).                        | across creative writing.          | (high FP rate). No persistent state or deterministic rules.   | (Problem domain overlap)      |
+------------------------------------+---------------------------------------------------------------+-----------------------------------+---------------------------------------------------------------+-------------------------------+
| E²RAG & IA-RAG (Zhang et al., 2026)| Event-centric retrieval-augmented generation over long        | Multi-hop information retrieval   | Uses vector cosine similarity over unstructured text chunks.  | PARTIAL OVERLAP               |
| arXiv:2506.05939 / 2606.06044      | fictional narrative text.                                     | for narrative fact checking.      | Cannot perform exact SQL window anomaly detection.            | (RAG mechanism differs)       |
+------------------------------------+---------------------------------------------------------------+-----------------------------------+---------------------------------------------------------------+-------------------------------+
| ReAct (Yao et al., 2023)           | Interleaving reasoning and acting in language models via      | Tool-calling agent execution loop | ReAct is a general prompting paradigm. StoryTrace applies it  | FOUNDATIONAL BASELINE         |
| arXiv:2210.03629                   | external tool execution.                                      | for hypothesis testing.           | within strict k<=6 bounds and two-tier calibrated schema.     | (Paradigm reused, not claimed)|
+------------------------------------+---------------------------------------------------------------+-----------------------------------+---------------------------------------------------------------+-------------------------------+
| CANVAS & PROVSEEK (Liu et al., 2026| Agent tool trace provenance and verifiable evidence grounding | Bounded tool calling with quote   | Evaluated on general domain QA / web browsing, not temporal   | PARTIAL OVERLAP               |
| arXiv:2604.13452                   | in question answering.                                        | citation and audit trails.        | OLAP narrative state or screenplay continuity.                | (Agent provenance shared)     |
+------------------------------------+---------------------------------------------------------------+-----------------------------------+---------------------------------------------------------------+-------------------------------+
| ScriptBook / Slated AI Analytics   | Statistical NLP and narrative arc scoring for screenplay box  | Screenplay ingestion and entity   | Commercial script coverage focusing on marketability and genre| PRIOR ART                     |
| Industry Commercial Tools          | office and pacing evaluation.                                 | character extraction.             | pacing, NOT microscopic continuity/prop/blocking verification.| (Distinct objective)          |
+------------------------------------+---------------------------------------------------------------+-----------------------------------+---------------------------------------------------------------+-------------------------------+
```

---

## 2. Patent Prior Art Landscape

```
+------------------------------------+---------------------------------------------------------------+-----------------------------------+---------------------------------------------------------------+-------------------------------+
| PATENT RECORD / JURISDICTION       | ASSIGNEE / INVENTOR & CORE DISCLOSURE                         | OVERLAP WITH STORYTRACE V2        | TECHNICAL DISTINCTION IN STORYTRACE V2                        | NOVELTY / RISK STATUS         |
+------------------------------------+---------------------------------------------------------------+-----------------------------------+---------------------------------------------------------------+-------------------------------+
| US Patent 10,489,482               | Automated screenplay parsing and entity extraction for        | Screenplay slugline parsing       | Static breakdown for call sheets. Does NOT track dynamic      | KNOWN PRIOR ART               |
| Issued: Oct 2019 (USPTO)           | production scheduling (characters, props, locations).         | (INT/EXT) and element tagging.    | physical state trajectories, temporal conflicts, or agents.   | (Parsing layer is standard)   |
+------------------------------------+---------------------------------------------------------------+-----------------------------------+---------------------------------------------------------------+-------------------------------+
| US Patent 11,256,928               | Natural language script analysis to validate continuity       | High-level goal of detecting      | Discloses a monolithic semantic classifier. Does NOT disclose | PARTIAL OVERLAP               |
| Issued: Feb 2022 (USPTO)           | across scenes using statistical semantic rules.               | continuity errors across scenes.  | an append-only OLAP state store, SQL window rules, or FastMCP.| (Mechanism differs completely)|
+------------------------------------+---------------------------------------------------------------+-----------------------------------+---------------------------------------------------------------+-------------------------------+
| US Pub. 2023/0289541               | Multi-modal alignment of video dailies with screenplay        | Temporal indexing of scene events | Computer-vision and audio alignment with film footage.        | PARTIAL OVERLAP               |
| Published: Sep 2023 (USPTO)        | text for production continuity tracking.                      | across production versions.       | StoryTrace is purely symbolic-textual pre-production analysis.| (Domain differs)              |
+------------------------------------+---------------------------------------------------------------+-----------------------------------+---------------------------------------------------------------+-------------------------------+
| US Pub. 2024/0119280               | Dynamic knowledge graph generation for narrative consistency  | Temporal graph tracking of script | Relies on graph embeddings and neural link prediction. Lacks   | PARTIAL OVERLAP               |
| Published: Apr 2024 (USPTO)        | verification in interactive gaming and storytelling.          | characters and narrative state.   | zero-LLM relational SQL window rules and bounded ReAct agent. | (Graph approach vs OLAP SQL)  |
+------------------------------------+---------------------------------------------------------------+-----------------------------------+---------------------------------------------------------------+-------------------------------+
| Global Patent Database Search on   | Comprehensive search across USPTO, WIPO, EPO, and IPO for     | --                                | No prior patent or application discloses the specific synergy | POTENTIALLY DISTINCTIVE       |
| "SQL Window Anomaly Detection over | "SQL window functions over structured screenplay state logs   |                                   | of append-only OLAP state logs + zero-LLM SQL window rules +   | (Target of Claim Architecture)|
| Temporal Narrative State"          | combined with tool-bounded ReAct investigation".              |                                   | FastMCP bounded ReAct investigation for continuity analysis.  |                               |
+------------------------------------+---------------------------------------------------------------+-----------------------------------+---------------------------------------------------------------+-------------------------------+
```

---

## 3. Prior-Art Collision & Differentiation Summary

1. **Screenplay Parsing (Conventional):** Extracting `INT./EXT.` sluglines and tagging character names is well disclosed by US 10,489,482 and standard production software (Final Draft, Movie Magic). StoryTrace does **not** claim scene parsing in isolation.
2. **Generative LLM Consistency Checkers (Monolithic Flaw):** ConStory-Checker and monolithic prompt systems attempt to do discovery and adjudication in a single prompt, resulting in low precision ($< 0.68$ F1) and inability to process 30,000-word scripts without context window failure.
3. **Graph-Based Systems (ATLAS, US 2024/0119280):** Rely on soft vector embeddings and fuzzy link prediction, which introduces graph hallucination. StoryTrace uses exact relational OLAP tables and deterministic SQL window joins.
4. **The Distinctive Architectural Gap:** The combination of **(a) Hierarchical Temporal State Extraction $\to$ (b) Append-Only OLAP Store $\to$ (c) Zero-LLM Parameterized SQL Window Candidate Detection $\to$ (d) FastMCP-Bounded ($k \le 6$) ReAct Investigation Agent $\to$ (e) Two-Tier Calibrated Verdicts with Verbatim Provenance** is absent from all surveyed literature and patent disclosures.
