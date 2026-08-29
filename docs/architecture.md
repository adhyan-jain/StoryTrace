# StoryTrace Architecture

StoryTrace is a general narrative continuity engine. It parses narrative documents (screenplays, novels) into a unified temporal event stream, stores them in an analytical database (ClickHouse), and uses an agent to investigate candidate continuity errors.

## Core Thesis
> StoryTrace builds a persistent, queryable model of a story's evolving world.

By supporting both screenplays and novels, and scaling to multi-book universes, StoryTrace uses ClickHouse as a genuine temporal Story State Engine.

## High-Level Architecture

```text
Screenplay PDF ──→ Screenplay Parser ──┐
                                       │
Novel PDF ───────→ Novel Parser ───────┤
                                       ↓
                                Narrative Units
                                       ↓
                             Entity/State Extraction
                                       ↓
                                Story State Events
                                       ↓
                                   ClickHouse
                                       ↓
                            Temporal Candidate Detection
                                       ↓
                              Investigation Agent
                                       ↓
                            Evidence-backed Verdict
```

## 1. Document Ingestion Layer
Parses PDFs into agnostic `NarrativeUnit` objects (e.g., scenes for screenplays, chapters/passages for novels) preserving exact page boundaries and raw text.

## 2. Event Extraction
Gemini strictly extracts temporal state events (presence, location, possession, injury, clothing) from each `NarrativeUnit` using Pydantic schemas.

## 3. Temporal State Engine (ClickHouse)
ClickHouse stores all extracted state events as an append-only log. It supports cross-document queries and complex window functions (like `lagInFrame`) to identify suspicious state transitions.

## 4. Continuity Autopsy (Investigation Agent)
A single Investigation Agent queries ClickHouse (via an MCP-like tool interface) to verify candidate conflicts. It can search across units, document history, or universe history to deduce bridging events.
