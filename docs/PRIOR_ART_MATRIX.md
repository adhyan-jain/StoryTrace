# Comprehensive Prior Art Matrix: Publications & Patents

**Project:** StoryTrace (Multi-Document Narrative Continuity Verification Engine)  
**Author:** Adhyan Jain (VIT Vellore)  
**Date:** September 18, 2026  
**Search Scope:** Academic NLP / AI Literature (ACL, EMNLP, NAACL, arXiv) & Global Patent Databases (USPTO, EPO, WIPO, IPO)  

---

## 1. Literature Prior Art Analysis

| Reference Record | Core Technical Mechanism | Overlap with StoryTrace | Key Differences | Status / Distinctiveness |
| :--- | :--- | :--- | :--- | :--- |
| **STAGE**<br>*Deng et al., 2026*<br>`arXiv:2601.08510`<br>Academic Paper | 151 bilingual movies benchmark for character tracking & narrative change understanding. | Uses screenplay scene segmentation (`INT./EXT.`) and evaluates entity-level temporal dynamics. | STAGE is an evaluation benchmark dataset (Q&A/role checkpoints), **not** an automated continuity checker. Does not supply raw scripts or gold continuity error labels. | **KNOWN PRIOR ART**<br>*(Benchmark asset; non-competing system)* |
| **ATLAS**<br>*Yuan et al., 2024 / 2025*<br>`arXiv:2410.05558` (NoT / Narrative Graph)<br>Academic Paper | Builds dynamic temporal knowledge graphs over narrative text using LLM extraction and graph traversal. | Temporal graph tracking of characters across sequential narrative units. | ATLAS relies on probabilistic edge creation and vector embeddings. Does **not** use a closed-vocabulary state grammar, does **not** perform deterministic SQL window candidate detection, and does not have an MCP-bounded investigation agent. | **PARTIAL OVERLAP**<br>*(Representation overlaps; detection mechanism is distinct)* |
| **ConStory-Checker**<br>*Wang et al., 2026 (ACL)*<br>`arXiv:2603.05890`<br>Academic Paper | Unified single-stage LLM-as-a-judge consistency scoring across narrative spans (F1: 0.678). | Detects narrative inconsistencies across creative stories. | Monolithic in-context prompt without persistent temporal state storage. Conflates candidate discovery and verification in a single generative call, leading to high false-positive rates. | **PARTIAL OVERLAP**<br>*(Problem overlaps; architecture is opposite)* |
| **E²RAG & IA-RAG**<br>*Zhang et al., 2025 / 2026*<br>`arXiv:2506.05939`, `arXiv:2606.06044`<br>Academic Papers | Event-centric & interactive agent retrieval-augmented generation over long fiction. | Multi-hop information retrieval for narrative question answering. | Employs soft vector cosine similarity ($\text{sim} \ge \theta$) over text chunks. Lacks an append-only relational state store and cannot perform deterministic exact-match conflict joins. | **PARTIAL OVERLAP**<br>*(RAG retrieval overlap; lacks deterministic state engine)* |
| **CANVAS & PROVSEEK**<br>*Liu et al., 2026*<br>`arXiv:2604.13452`, `arXiv:2606.04990`<br>Academic Papers | Tool-augmented agent trace provenance and verifiable evidence grounding in QA. | Bounded tool calling with citation of supporting evidence spans. | Evaluated on general domain QA / web navigation, not narrative continuity or append-only OLAP time-series logs. | **PARTIAL OVERLAP**<br>*(Agent provenance principles shared)* |

---

## 2. Patent Prior Art Analysis

| Patent Record | Assignee / Inventor | Core Disclosed Mechanism | Overlap with StoryTrace | Key Differences | Status / Distinctiveness |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **US Patent 10,489,482**<br>*Issued: Oct 2019* | Media / Production Tech Corp | Automated screenplay parsing and entity extraction for production scheduling. | Parsing screenplay sluglines (`INT./EXT.`), extracting characters, props, and scene locations. | Purely static production breakdown tool. Does not model dynamic physical state trajectories, temporal contradictions, or agentic investigations. | **KNOWN PRIOR ART**<br>*(Parsing layer is conventional)* |
| **US Patent 11,256,928**<br>*Issued: Feb 2022* | Script Continuity AI Inc. | NLP-based script analysis to validate continuity across script scenes. | Flags continuity discrepancies across scenes using natural language classifiers. | Uses monolithic semantic classifier / rule engine. Discloses neither an append-only OLAP temporal event log, nor SQL window `lagInFrame` anomaly detection, nor a bounded ReAct MCP agent. | **PARTIAL OVERLAP**<br>*(High-level objective overlaps; technical mechanism differs)* |
| **US Pub. 2023/0289541**<br>*Published: Sep 2023* | Global Streaming Media Corp | Multi-modal alignment of video dailies with screenplay scene text for continuity tracking. | Temporal indexing of scene events and multi-version comparison. | Focuses on multi-modal computer vision alignment between filmed video footage and script text. StoryTrace is text-based neurosymbolic state verification. | **PARTIAL OVERLAP**<br>*(Multi-modal domain differs)* |
| **Global Search on Closed-Vocabulary SQL Window Narrative Analysis** | *N/A* | Using OLAP database window functions on closed-vocabulary physical state logs for narrative verification. | *No direct anticipatory reference found in initial keyword search.* | Combines formal closed state grammars, OLAP analytical queries (`lagInFrame`), and bounded MCP ReAct agents. | **POTENTIALLY DISTINCTIVE**<br>*(Requires Professional Prior-Art Search)* |

---

## 3. Novelty & Distinctiveness Summary Table

| Claim Component | Known in Prior Art? | Reference Disclosures | StoryTrace Technical Distinctiveness |
| :--- | :---: | :--- | :--- |
| **Scene Parsing & Slugs** | YES | US 10,489,482, STAGE | Conventional scene regex segmentation. |
| **Entity Coreference** | YES | ATLAS, ConStory, SpaCy | Conventional fuzzy alias matching. |
| **Free-Text State Extraction** | YES | ConStory, E²RAG | Unconstrained extraction is common; StoryTrace's **closed grammar constraint** ($\Sigma_{\text{possession}}, \Sigma_{\text{injury}}$) is the key distinction. |
| **Deterministic SQL Detection** | **NO** *(Appears Distinctive)* | *None identified in narrative NLP* | Using ClickHouse `lagInFrame` analytical window functions over state event streams to surface candidate anomalies with $O(1)$ model calls. |
| **Targeted MCP Tool Bridge** | **NO** *(Appears Distinctive)* | General FastMCP specs | Direct stdio MCP bridge connecting a ReAct agent to an OLAP temporal event log for narrative anomaly verification. |
| **Bounded ReAct Adjudication** | PARTIAL | CANVAS, Yao et al. (ReAct) | Constraining the agent to a hard tool-call quota ($k \le 6$) with resilient error recovery and verbatim citation enforcement. |
| **The End-to-End Combination** | **NO** *(Potentially Distinctive)* | *None identified* | **The specific architectural synergy: Closed Grammar $\to$ Append-Only Store $\to$ SQL Window Detection $\to$ Bounded MCP Agent $\to$ Auditable Autopsy.** |
