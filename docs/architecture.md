# System Architecture

## Overview
StoryTrace is built around a deterministic data extraction pipeline feeding a temporal database, coupled with a single agentic component for reasoning about continuity.

## Data Flow
1. **Screenplay PDF** -> `ingestion/` (PDF/Text Parser, PyMuPDF) -> Raw Text
2. **Raw Text** -> `pipeline/` (Scene Parser) -> Scenes
3. **Scenes** -> `candidate_detection/` (Entity Resolver) -> Entities
4. **Entities & Scenes** -> `llm/` (Gemini Structured State Extraction) -> State Events
5. **State Events** -> `story_state/` (Event Builder) -> ClickHouse Story State DB
6. **ClickHouse** -> `candidate_detection/` (SQL queries) -> Candidate Conflicts
7. **Candidates** -> `agent/` (Investigation Agent w/ ClickHouse MCP) -> Verdicts
8. **Verdicts** -> `api/` (FastAPI) -> Next.js UI

## Services & Dependencies
- **Backend**: FastAPI, Python 3.10+
- **Database**: ClickHouse (temporal state engine)
- **AI**: Google Gemini (via official SDK), ClickHouse MCP
- **Frontend**: Next.js, React, Tailwind, shadcn/ui

## Runtime Flow
- The backend API accepts a PDF and queues it.
- A worker processes the PDF through the deterministic extraction pipeline.
- Data is written to ClickHouse in an append-only fashion.
- Background jobs run SQL window functions over ClickHouse to detect suspicious transitions.
- The Investigation Agent runs asynchronously for each candidate, querying the MCP, and writes a final verdict.
- The frontend polls or receives WebSocket updates and displays the Continuity Autopsy.

## ClickHouse & MCP Role
ClickHouse is the source of truth for all temporal state. The MCP allows the Investigation Agent to securely run parameterized queries (`get_entity_timeline`, etc.) without writing raw SQL.
