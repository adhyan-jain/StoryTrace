# StoryTrace (formerly SceneSentry)

**Your story's continuity guardian.**

StoryTrace is an agentic, multi-document narrative continuity engine. It converts screenplay or novel documents into a structured temporal model of a shared story universe (`NarrativeUnit`s), tracks state over time (character presence, location, prop possession, etc.) across those documents, detects conflicts, and uses an Investigation Agent to verify findings against the original narrative text.

## Architecture

1.  **Document Parsers**: A `ScreenplayParser` and `NovelParser` each extract raw text into document-type-agnostic `NarrativeUnit`s (scenes, chapters, or passages), maintaining exact page boundaries.
2.  **Entity Resolver & State Extraction**: Uses Gemini to structure state events from each `NarrativeUnit`.
3.  **Story State Engine**: ClickHouse database storing append-only temporal events, keyed by `story_universe_id` and `sequence_number` rather than any per-document numbering.
4.  **Candidate Detector**: SQL window functions finding suspicious state transitions.
5.  **Investigation Agent**: ONE genuinely agentic component (using ClickHouse MCP) that investigates conflicts and outputs an `InvestigationVerdict`.
6.  **Continuity Autopsy**: The user-facing presentation of an `InvestigationVerdict` — not a separate agent or stage. See [docs/architecture.md](docs/architecture.md).
7.  **Frontend**: Next.js UI providing a premium professional filmmaking tool experience.

## Documentation

-   [Architecture](docs/architecture.md)
-   [Data Model](docs/data-model.md)
-   [Agent Architecture](AGENTS.md)
-   [Investigation / Autopsy](docs/investigation.md)
-   [Design System](docs/design.md)
-   [Development Guidelines](CLAUDE.md)

## Reused Infrastructure

This project was initialized using carefully selected components from the **Echotales** codebase. Status reflects what has actually been adapted to run against `backend.*`, not just copied:

-   `backend/llm/base.py`: Robust JSON extraction/healing logic and Pydantic validation. Adapted and in active use (`backend/llm/client.py`, `backend/agent/investigator.py`).
-   `backend/story_state/interval.py`: Temporal modeling concepts. Adapted and in use.
-   `backend/story_state/models.py`: Data schema, adapted for ClickHouse and for the document-agnostic `NarrativeUnit` model (`story_universe_id`/`unit_id`/`sequence_number`, not `screenplay_id`/`scene_id`/`scene_number`).
-   `tests/unit/test_llm.py` & `tests/benchmark/`: **Not yet adapted.** These still import the `echotales` package directly (`echotales.pipeline.llm.router`, `echotales.core.store`, etc.), which isn't vendored into this repo, so they cannot be collected or run here. They are excluded via `pytest.ini` until ported. Treat `FakeProvider`/`GoldSet` as Echotales-side test fixtures, not as dependencies of this codebase's runtime or test suite.
