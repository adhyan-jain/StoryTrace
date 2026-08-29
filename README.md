# StoryTrace (formerly SceneSentry)

**Your screenplay's continuity guardian.**

StoryTrace is an agentic screenplay continuity analysis system. It converts a screenplay PDF into a structured temporal model of its story world, tracks state over time (character presence, location, prop possession, etc.), detects conflicts, and uses an Investigation Agent to verify findings against the original screenplay text.

## Architecture

1.  **PDF/Text Parser**: Extracts raw text while maintaining page and coordinate mappings.
2.  **Scene Parser**: Deterministically segments text into scenes.
3.  **Entity Resolver & State Extraction**: Uses Gemini to structure state events.
4.  **Story State Engine**: ClickHouse database storing append-only temporal events.
5.  **Candidate Detector**: SQL window functions finding suspicious state transitions.
6.  **Investigation Agent**: ONE genuinely agentic component (using ClickHouse MCP) that investigates conflicts and outputs an evidence-backed verdict.
7.  **Frontend**: Next.js UI providing a premium professional filmmaking tool experience.

## Documentation

-   [Architecture](docs/architecture.md)
-   [Data Model](docs/data-model.md)
-   [Agent Architecture](AGENTS.md)
-   [Investigation / Autopsy](docs/investigation.md)
-   [Design System](docs/design.md)
-   [Development Guidelines](CLAUDE.md)

## Reused Infrastructure

This project was initialized using carefully selected components from the **Echotales** codebase:

-   `backend/llm/base.py`: Robust JSON extraction/healing logic and Pydantic validation.
-   `backend/story_state/interval.py`: Temporal modeling concepts.
-   `backend/story_state/models.py`: Useful data schema concepts to be adapted for ClickHouse.
-   `tests/unit/test_llm.py` & `tests/benchmark/`: FakeProvider testing patterns and gold-standard evaluation harnesses.
