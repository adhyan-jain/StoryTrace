# StoryTrace

## Project Purpose
StoryTrace (formerly SceneSentry) is an agentic screenplay continuity analysis system. It acts as a filmmaker's continuity guardian. It converts a screenplay PDF into a structured temporal model of its story world and tracks character presence, character location, prop possession, injuries, and clothing changes.

## Architecture
- **Pipeline (Deterministic)**: PDF Parser -> Scene Parser -> Entity Resolver -> Gemini State Extraction -> Story State Builder -> ClickHouse
- **Detection (Deterministic)**: SQL-based candidate conflict detection from ClickHouse.
- **Investigation (Agentic)**: ONE Investigation Agent (Gemini + ADK + ClickHouse MCP) verifies candidates using database queries.
- **Frontend**: Next.js UI reading from a FastAPI backend.

## Constraints & Rules
- Do NOT simply ask an LLM to read the screenplay and hallucinate continuity errors.
- Every extracted fact must retain exact screenplay evidence (scene, page, excerpt, confidence, establishment type).
- Only ONE genuinely agentic Investigation Agent.
- ClickHouse must be real and queried through the official MCP integration.
- Evidence is first-class data. No finding should exist without provenance.
- Do not use generic AI-dashboard design; build a professional production tool.

## Design Principles
- Excellent typography, spacing, and hierarchy.
- Restrained visual language with meaningful color.
- No glowing AI effects, giant rounded cards, or chatbot bubbles.

## Testing Commands
- `pytest tests/unit`
- `pytest tests/integration`
- Playwright CLI for frontend testing.

## Environment Variables
- `GEMINI_API_KEY`
- `CLICKHOUSE_URL`
- `CLICKHOUSE_USER`
- `CLICKHOUSE_PASSWORD`

## Important Implementation Decisions
- See `docs/decisions/`
- Avoid vector databases unless absolutely required.
- Use append-only temporal events.

## "Do Not" Rules
- Do not add random agents to solve reliability problems.
- Do not expose private chain-of-thought to the UI.
- Do not fake agent traces or database queries.
