# Agent Architecture

StoryTrace uses **ONE Investigation Agent**. The pipeline itself is deterministic, NOT agentic.

## What is and isn't an agent
- **Is an agent:** The Investigation Agent, which investigates candidate continuity conflicts.
- **Isn't an agent:** Document parsing, entity resolution, state extraction, and candidate generation. These are deterministic or structured LLM calls.

## Investigation Agent
- **Purpose:** Receives a candidate conflict and autonomously determines what evidence it needs from the Story Universe to reach a verdict. It can search across NarrativeUnits and documents.
- **Max Tool Calls:** 8 per investigation.
- **Verdict Schema:**
  - `status`: verified | resolved | uncertain | intentional
  - `severity`: critical | warning | info
  - `explanation`: string
  - `confidence`: float (0-1)
  - `investigation_actions`: list of strings (summary of steps)

## Tools (ClickHouse MCP)
1. `get_entity_timeline(entity_id, from_sequence, to_sequence)`: Retrieves all events for an entity within a temporal sequence range.
2. `get_unit_text(unit_id)`: Gets raw text for a specific NarrativeUnit.
3. `get_state_at_unit(entity_id, sequence_number)`: Calculates the expected state of an entity up to a sequence point.
4. `find_attribute_changes(entity_id, attribute)`: Finds all changes for a specific attribute of an entity across the universe.

## Rules
- The agent MUST use the ClickHouse MCP for database queries.
- If uncertain, the agent must return `uncertain`. High precision is required over recall.
- Private chain-of-thought must not be exposed. Only concise, auditable summaries are returned.
- A bad tool call (wrong/hallucinated argument name, wrong type) is fed back to the
  model as an observation and the loop continues, rather than aborting the
  investigation on the first mistake -- `max_calls` (6) is the real backstop, not
  the first exception. See `backend/agent/investigator.py`'s `_run_loop`.

## Local Testing / Model Provider

> **RULE: Do NOT use Vertex AI or Gemini API for local work unless the user
> explicitly requests it in that specific message.** This applies to all eval
> runs (`python3 -m scripts.eval`), pipeline scripts, and any iteration loop.

- **Default to Ollama for ALL local testing and eval runs.**
  Set `MODEL_PROVIDER=ollama` in `.env` (already the default in
  `backend/llm/provider.py` and `scripts/eval/run_eval.py`'s `get_provider()`
  when the env var is absent).
- Why: Vertex AI calls are metered and rate-limited (hit real 429
  RESOURCE_EXHAUSTED errors during repeated local eval runs); Ollama runs
  fully local against already-pulled models (default `qwen2.5:7b`, see
  `backend/llm/ollama.py`) at no cost and no quota risk.
- Only use Vertex AI / Gemini when the user explicitly names it for that
  specific task (e.g., "run the final demo on Vertex AI" or "compare Gemini
  quality vs Ollama"). A general "improve F1" or "run eval" instruction
  always means Ollama.
- `_suggest_fix` in `backend/agent/investigator.py` only routes through the
  google-adk `Agent`/`Runner` path when `provider.tier == "api"` (Gemini/
  Vertex) — Ollama's `tier` is not `"api"`, so this path is skipped
  automatically when testing locally on Ollama.
