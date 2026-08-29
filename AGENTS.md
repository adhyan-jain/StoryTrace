# Agent Architecture

StoryTrace uses ONE Investigation Agent. The pipeline itself is deterministic, NOT agentic.

## What is and isn't an agent
- **Is an agent:** The Investigation Agent, which investigates candidate continuity conflicts.
- **Isn't an agent:** Scene parsing, entity resolution, state extraction, and candidate generation. These are deterministic or structured LLM calls.

## Investigation Agent
- **Purpose:** Receives a candidate conflict and autonomously determines what evidence it needs to reach a verdict.
- **Max Tool Calls:** 6 per investigation.
- **Verdict Schema:**
  - `status`: verified | resolved | uncertain | intentional
  - `severity`: critical | warning | info
  - `explanation`: string
  - `confidence`: float (0-1)
  - `evidence`: list of Evidence objects
  - `scenes_examined`: list of ints
  - `investigation_actions`: list of strings (summary of steps)

## Tools (ClickHouse MCP)
1. `get_entity_timeline(entity_id, from_scene, to_scene)`: Retrieves all events for an entity within a scene range.
2. `get_scene_text(scene_id)`: Gets raw text for a scene.
3. `get_state_at_scene(entity_id, scene_id)`: Calculates the expected state of an entity at a given scene.
4. `find_attribute_changes(entity_id, attribute)`: Finds all changes for a specific attribute of an entity.
5. `get_characters_in_scene(scene_id)`: Lists all characters present in a scene.

## Rules
- The agent must use the ClickHouse MCP for database queries.
- Safety/precision: If uncertain, the agent must return `uncertain`. High precision is required over recall.
- Private chain-of-thought must not be exposed. Only concise, auditable summaries are returned.
- If future agents are needed (unlikely), they must follow the same strict provenance and tool contracts.
