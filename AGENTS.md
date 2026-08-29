# Agent Architecture

StoryTrace uses **ONE Investigation Agent**. The pipeline itself is deterministic, NOT agentic.

## What is and isn't an agent
- **Is an agent:** The Investigation Agent, which investigates candidate continuity conflicts.
- **Isn't an agent:** Document parsing, entity resolution, state extraction, and candidate generation. These are deterministic or structured LLM calls.

## Investigation Agent
- **Purpose:** Receives a candidate conflict and autonomously determines what evidence it needs from the Story Universe to reach a verdict. It can search across NarrativeUnits and documents.
- **Max Tool Calls:** 6 per investigation.
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
