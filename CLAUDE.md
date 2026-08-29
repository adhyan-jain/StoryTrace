# StoryTrace Guidelines

StoryTrace is an agentic, multi-document narrative continuity engine.

## Core Rules

1. **Document-Type Agnostic**: The backend model uses `NarrativeUnit` (representing scenes, chapters, passages). Do not hardcode "scene" into the core temporal model.
2. **ClickHouse is the Temporal Engine**: Use ClickHouse to execute temporal analytics (e.g., `lagInFrame`) across vast sequences of story events spanning multiple documents.
3. **One Investigation Agent**: The parsing, extraction, and detection steps are strictly deterministic (or structured LLM). The single Investigation Agent is invoked only to adjudicate detected candidates using its ClickHouse MCP tools.
4. **Provenance**: Every extracted event must retain exact `unit_id`, `page_start/end`, and `raw_excerpt`. The user must be able to trace a finding back to the exact text.
5. **No Fake Intelligence**: If mocking API calls for local demos, clearly mark them.
6. **Polished Output**: Output code should be production-ready and the UI should feel like a premium tool for filmmakers and authors.

## Code Structure

```text
backend/
  ingestion/       # PDF parsing to NarrativeUnits
  llm/             # Gemini structured clients
  pipeline/        # Event extraction & resolution
  clickhouse/      # State Engine connections
  candidate_detection/ # SQL window functions
  agent/           # Investigation Agent
  api/             # FastAPI backend
apps/
  web/             # Next.js Continuity Autopsy UI
```
