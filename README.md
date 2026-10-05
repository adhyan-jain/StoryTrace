# StoryTrace: Narrative Continuity Engine & SSR-Bench V2

**Your story's continuity guardian and a benchmark for Sequential State Revision in LLMs.**

StoryTrace is a dual-purpose system:
1. **Agentic Narrative Continuity Engine**: A production multi-document continuity tracker that converts screenplays, novels, and controlled narratives into a structured temporal model (`NarrativeUnit`s), tracks state transitions across documents in ClickHouse, detects candidate continuity errors via SQL window functions, and verifies them using an autonomous **Investigation Agent** with ClickHouse MCP tools.
2. **SSR-Bench V2 (Sequential State Revision Benchmark)**: A rigorous, leak-free benchmark evaluating how Large Language Models perform causally localized state updates across sequential trajectories while preserving causally unaffected state.

---

## 🔬 SSR-Bench V2 Core Novelty & Empirical Discoveries

SSR-Bench V2 evaluates LLMs on **Sequential State Revision** using minimal matched narrative pairs $(S_1, S_2)$ that differ by exactly one pivot event sentence, sharing identical evidence prompts and claim keys.

### 1. Leak-Free Validity & Integrity (G9 Gate PASS)
- **Story-Blind Attackers (8 classifiers)**: Item semantic state-EM = **0.000**, pair-both = **0.000** (Gradient Boosting, Logistic Regression, TF-IDF, positional, lexical, majority prior).
- **Story-Blind Bayes Bound**: **0.500** item-level, **0.000** pair-both.
- **Story-Replay Oracle**: **1.000** (300/300 `test_main`, 30/30 `set_valued`, 1240/1240 `train`).
- **Hard Pair Invariants**: 0 validator violations across all dataset splits.
- **Adversarial Invariance**: All 8 adversarial transforms (entity swapping, paraphrase, shuffle, novel templates, etc.) maintain 100% oracle invariance and 0 validator violations.

### 2. Empirical Benchmark Findings (4 Models × 17 Experimental Conditions)

| Model | $K_1$ (Standard Prompt) | $K_2$ (No Rules) | $K_4$ (Implicit Laws) | $PG$ (Prior State Given) | Required Change Recall | Preservation Rate | Collateral Edit Rate |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **qwen2.5:7b** | **0.000** | 0.026 | 0.000 | **0.163** | 72.1% | 47.1% | 52.9% |
| **llama3:latest** | **0.007** | 0.013 | 0.007 | **0.083** | 72.8% | 57.0% | 43.0% |
| **qwen3:8b** | **0.020** | 0.026 | 0.010 | **0.203** | 73.5% | 60.5% | 39.5% |
| **mistral:7b** | **0.000** | 0.000 | 0.000 | **0.133** | 75.5% | 50.8% | 49.2% |

### Key Scientific Conclusions
1. **The Phenomenon is Real**: Standard LLMs achieve near-zero semantic state exact match ($0.000$–$0.020$) despite high required change recall (~72–75%).
2. **Collateral Over-Revision**: The primary cause of failure is high collateral edit rate (~40–53%)—models unintentionally modify state claims that are causally unaffected by the narrative event.
3. **Rule-Following Hypothesis REJECTED**: Prompt variations omitting explicit rules ($K_2$), framing as implicit constraints ($K_4$), or providing 3-shot examples ($K_{1\text{-fs}}$) fail to rescue performance ($\le 0.030$), disproving prompt-artifact explanations.
4. **Prior State Tracking Bottleneck**: Providing the ground-truth prior state in the prompt ($PG$) dramatically increases state preservation to **72%–87%** ($p < 0.0001$, McNemar test with Holm adjustment), isolating **sequential prior-state tracking and state preservation** as the fundamental bottleneck.

---

## 🏗 Engine Architecture

1. **Document Parsers**: `ScreenplayParser` and `NovelParser` extract raw text into `NarrativeUnit`s while preserving page/line metadata.
2. **Entity Resolver & State Extraction**: Extracts structured state transitions from narrative units into ClickHouse.
3. **ClickHouse Story State Engine**: Append-only temporal state store, keyed by `story_universe_id` and `sequence_number`.
4. **SQL Candidate Detector**: Window functions identifying candidate state discrepancies across narrative trajectories.
5. **Investigation Agent**: Autonomous ReAct agent utilizing ClickHouse MCP tools (`get_entity_timeline`, `get_unit_text`, `get_state_at_unit`, `find_attribute_changes`) to gather evidence and render auditable verdicts. Max call limit: 8 per investigation.
6. **Frontend UI**: Next.js dashboard for multi-version screenplay diffing and conflict inspection.

---

## 🚀 Getting Started

### 1. Requirements & Setup
```bash
# Clone and enter repo
cd StoryTrace

# Start ClickHouse database
docker compose up -d
docker exec -i storytrace-clickhouse-1 clickhouse-client --database storytrace < backend/clickhouse/schema.sql

# Create Python environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Start local LLM server (Ollama)
ollama pull qwen2.5:7b
```

### 2. Running the API & Web App
```bash
# Start backend API (port 8000)
uvicorn backend.api.main:app --reload --port 8000

# Start Next.js Frontend (port 3000)
cd apps/web && npm install && npm run dev
```

### 3. Executing SSR-Bench V2 Benchmarks
```bash
# Run G9 leakage gates and story-blind attackers
python3 -m research.ssr_v2.g9

# Run LLM evaluations (Ollama)
python3 -m research.ssr_v2.run_llm --stage A
python3 -m research.ssr_v2.run_llm --stage B
python3 -m research.ssr_v2.run_llm --stage T
python3 -m research.ssr_v2.run_llm --stage E

# Compute scored analysis, pair consistency, and Holm-adjusted contrasts
python3 -m research.ssr_v2.analyze_v2
```

---

## 📚 Documentation & Research Artifacts

- [Architecture Guide](docs/ARCHITECTURE.md)
- [Agent Architecture & Rules](AGENTS.md)
- [V2 Benchmark Preregistration](research/ssr_bench/V2_PREREGISTRATION.md)
- [G9 Leakage Diagnostic Report](research/results/V2_G9_DIAGNOSTIC.md)
- [V2 Scored Analysis Artifacts](research/results/v2/analysis.json)
- [V1 Audit & Benchmark Post-Mortem](docs/BENCHMARK_FAILURE_AUDIT.md)
