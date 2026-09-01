"""Investigation Agent's ClickHouse tools -- executed over the mcp-clickhouse
MCP server (not a direct clickhouse_connect client) so every query the agent
runs at investigation time is a real MCP tool call, logged for the autopsy
trace.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, List

from mcp import ClientSession


class AgentTools:
    def __init__(self, session: ClientSession, story_universe_id: str, log: List[dict] | None = None):
        self.session = session
        self.story_universe_id = story_universe_id
        self.log: List[dict] = log if log is not None else []

    async def _query(self, sql: str, tool_name: str) -> List[Dict[str, Any]]:
        result = await self.session.call_tool("run_query", arguments={"query": sql})
        text = result.content[0].text if result.content else "{}"
        data = json.loads(text)
        rows = data.get("rows", [])
        self.log.append(
            {
                "tool": tool_name,
                "sql": sql,
                "result_rows": len(rows),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )
        if "columns" not in data:
            raise RuntimeError(f"MCP query error from tool '{tool_name}': {text}")
        return [dict(zip(data["columns"], row)) for row in rows]

    async def get_entity_timeline(self, entity_id: str, from_sequence: int, to_sequence: int) -> List[Dict[str, Any]]:
        sql = f"""
        SELECT sequence_number, attribute, value, raw_excerpt, confidence
        FROM state_events
        WHERE story_universe_id = '{self.story_universe_id}'
          AND entity_id = '{entity_id}'
          AND sequence_number >= {int(from_sequence)}
          AND sequence_number <= {int(to_sequence)}
        ORDER BY sequence_number
        """
        return await self._query(sql, "get_entity_timeline")

    async def get_unit_text(self, unit_id: str) -> str:
        sql = f"""
        SELECT text, title, start_page
        FROM narrative_units
        WHERE story_universe_id = '{self.story_universe_id}' AND id = '{unit_id}'
        LIMIT 1
        """
        rows = await self._query(sql, "get_unit_text")
        return rows[0]["text"] if rows else ""

    async def get_state_at_unit(self, entity_id: str, sequence_number: int) -> List[Dict[str, Any]]:
        sql = f"""
        SELECT attribute,
               argMax(value, sequence_number) AS current_value,
               argMax(raw_excerpt, sequence_number) AS excerpt
        FROM state_events
        WHERE story_universe_id = '{self.story_universe_id}'
          AND entity_id = '{entity_id}'
          AND sequence_number <= {int(sequence_number)}
        GROUP BY attribute
        """
        return await self._query(sql, "get_state_at_unit")

    async def find_attribute_changes(self, entity_id: str, attribute: str) -> List[Dict[str, Any]]:
        sql = f"""
        SELECT sequence_number, value, raw_excerpt
        FROM state_events
        WHERE story_universe_id = '{self.story_universe_id}'
          AND entity_id = '{entity_id}'
          AND attribute = '{attribute}'
        ORDER BY sequence_number
        """
        return await self._query(sql, "find_attribute_changes")
