"""StoryTrace V2 Investigation Agent Tools.

Executes queries over ClickHouse V2 tables via MCP stdio client, providing rich
spatial trajectories, temporal pacing anchors, co-presence scenes, and unit text.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from mcp import ClientSession

_MAX_ROWS = 25
_MAX_EXCERPT_CHARS = 250


def _sql_str(value: str) -> str:
    return "'" + str(value).replace("\\", "\\\\").replace("'", "\\'") + "'"


def _shorten(text: str, max_chars: int = _MAX_EXCERPT_CHARS) -> str:
    if not text or len(text) <= max_chars:
        return text
    return text[:max_chars].rstrip() + "…"


def _cap_rows(rows: List[Dict[str, Any]], excerpt_key: str = "raw_excerpt") -> List[Dict[str, Any]]:
    shortened = [
        {k: (_shorten(v) if k == excerpt_key and isinstance(v, str) else v) for k, v in row.items()}
        for row in rows[:_MAX_ROWS]
    ]
    if len(rows) > _MAX_ROWS:
        shortened.append({"note": f"... {len(rows) - _MAX_ROWS} more rows omitted"})
    return shortened


class AgentToolsV2:
    def __init__(
        self,
        session: ClientSession,
        story_universe_id: str,
        log: Optional[List[dict]] = None,
        candidate: Optional[Any] = None,
    ):
        self.session = session
        self.story_universe_id = story_universe_id
        self.log: List[dict] = log if log is not None else []
        self.candidate = candidate

    async def _query(self, sql: str, tool_name: str) -> List[Dict[str, Any]]:
        result = await self.session.call_tool("run_query", arguments={"query": sql})
        text = result.content[0].text if result.content else "{}"
        try:
            data = json.loads(text)
        except Exception as e:
            raise RuntimeError(f"Invalid JSON from MCP tool '{tool_name}': {text}") from e
            
        rows = data.get("rows", [])
        self.log.append({
            "tool": tool_name,
            "sql": sql,
            "result_rows": len(rows),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        if "columns" not in data:
            raise RuntimeError(f"MCP query error from tool '{tool_name}': {text}")
        return [dict(zip(data["columns"], row)) for row in rows]

    async def get_entity_timeline_v2(
        self,
        entity_id: str,
        from_sequence: int = 0,
        to_sequence: int = 9999
    ) -> List[Dict[str, Any]]:
        """Retrieve state facts for an entity within sequence range with spatial & temporal anchors."""
        sql = f"""
        SELECT sequence_number, unit_id, attribute, value,
               hier_environment, hier_specific_room, hier_city_region,
               time_anchor, related_entity_id, raw_excerpt
        FROM state_events_v2
        WHERE story_universe_id = {_sql_str(self.story_universe_id)}
          AND entity_id = {_sql_str(entity_id)}
          AND sequence_number >= {int(from_sequence)}
          AND sequence_number <= {int(to_sequence)}
        ORDER BY sequence_number
        """
        return _cap_rows(await self._query(sql, "get_entity_timeline_v2"))

    async def get_scene_co_presence(
        self,
        from_sequence: int = 0,
        to_sequence: int = 9999
    ) -> List[Dict[str, Any]]:
        """Retrieve scene co-presence, environments, and temporal anchors across scenes."""
        sql = f"""
        SELECT sequence_number, unit_id, entity_ids, setting_type, environment, specific_room, time_anchor
        FROM scene_co_presence_v2
        WHERE story_universe_id = {_sql_str(self.story_universe_id)}
          AND sequence_number >= {int(from_sequence)}
          AND sequence_number <= {int(to_sequence)}
        ORDER BY sequence_number
        """
        return _cap_rows(await self._query(sql, "get_scene_co_presence"))

    async def get_spatial_trajectory(self, entity_id: str) -> List[Dict[str, Any]]:
        """Retrieve the complete spatial movement path for a specific entity across the story."""
        sql = f"""
        SELECT sequence_number, unit_id, hier_setting_type, hier_environment, hier_specific_room, hier_city_region, time_anchor, raw_excerpt
        FROM state_events_v2
        WHERE story_universe_id = {_sql_str(self.story_universe_id)}
          AND entity_id = {_sql_str(entity_id)}
          AND (attribute = 'location' OR startsWith(attribute, 'location.'))
        ORDER BY sequence_number
        """
        return _cap_rows(await self._query(sql, "get_spatial_trajectory"))

    async def find_attribute_changes(self, entity_id: str, attribute: str) -> List[Dict[str, Any]]:
        """Find all transitions on a specific attribute for an entity."""
        sql = f"""
        SELECT sequence_number, unit_id, value, related_entity_id, time_anchor, raw_excerpt
        FROM state_events_v2
        WHERE story_universe_id = {_sql_str(self.story_universe_id)}
          AND entity_id = {_sql_str(entity_id)}
          AND (attribute = {_sql_str(attribute)} OR startsWith(attribute, {_sql_str(attribute + '.')}))
        ORDER BY sequence_number
        """
        return _cap_rows(await self._query(sql, "find_attribute_changes"))

    async def get_unit_text(self, unit_id: str) -> Dict[str, Any]:
        """Retrieve verbatim source text for a narrative unit."""
        sql = f"""
        SELECT id, title, text, sequence_number
        FROM narrative_units
        WHERE story_universe_id = {_sql_str(self.story_universe_id)}
          AND id = {_sql_str(unit_id)}
        LIMIT 1
        """
        rows = await self._query(sql, "get_unit_text")
        if not rows:
            return {"error": f"Unit '{unit_id}' not found"}
        row = rows[0]
        text = row.get("text", "")
        return {
            "unit_id": unit_id,
            "title": row.get("title", ""),
            "sequence_number": row.get("sequence_number", 0),
            "text": _shorten(text, 1500)
        }
