"""Investigation Agent's ClickHouse tools -- executed over the mcp-clickhouse
MCP server (not a direct clickhouse_connect client) so every query the agent
runs at investigation time is a real MCP tool call, logged for the autopsy
trace.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from mcp import ClientSession

# Row/excerpt caps shared by every tool below. A popular entity in a
# 501-chapter novel can have hundreds of state_events rows, and a
# mis-extracted raw_excerpt can occasionally run to a full paragraph instead
# of the single sentence/phrase the extraction prompt asks for -- either one
# dumped verbatim into the agent's own context crowds out room for its own
# structured-output formatting (a likely contributor to "max tool calls
# reached without conclusion" on longer documents) and produces an
# Autopsy-trace panel nobody can actually read. Keep every observation to
# "the most evidence-giving part, not the whole record."
_MAX_ROWS = 20
_MAX_EXCERPT_CHARS = 220


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
        shortened.append({"note": f"... {len(rows) - _MAX_ROWS} more rows omitted, narrow your sequence range"})
    return shortened


class AgentTools:
    def __init__(
        self,
        session: ClientSession,
        story_universe_id: str,
        log: List[dict] | None = None,
        candidate: Optional[Any] = None,
    ):
        self.session = session
        self.story_universe_id = story_universe_id
        self.log: List[dict] = log if log is not None else []
        # The CandidateConflict under investigation, if known -- lets
        # get_unit_text center its snippet on the actual evidence excerpt
        # instead of guessing from the start of a long chapter (see below).
        self.candidate = candidate

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
        return _cap_rows(await self._query(sql, "get_entity_timeline"))

    async def get_unit_text(self, unit_id: str) -> str:
        sql = f"""
        SELECT text, title, start_page
        FROM narrative_units
        WHERE story_universe_id = '{self.story_universe_id}' AND id = '{unit_id}'
        LIMIT 1
        """
        rows = await self._query(sql, "get_unit_text")
        if not rows:
            return ""
        text = rows[0]["text"]

        # A screenplay scene is ~1-3K chars; a novel chapter can run
        # 10-20K+ (measured: Reverend Insanity averaged ~12K, up to 22K).
        # Returning even a flat prefix of that is two problems at once: it
        # bloats the agent's context for no reason, and on a long chapter the
        # actual evidence sentence can sit well past whatever prefix gets
        # returned, so the agent never even sees it. When this unit is one of
        # the candidate's own evidence units, center the snippet on that
        # exact excerpt with a couple sentences of context either side --
        # "the most evidence-giving part," not the start of the chapter.
        _WINDOW_CHARS = 280
        _FALLBACK_CHARS = 400

        anchor = None
        if self.candidate is not None:
            if unit_id == getattr(self.candidate, "prior_evidence_unit_id", None):
                anchor = getattr(self.candidate, "prior_evidence_excerpt", None)
            elif unit_id == getattr(self.candidate, "current_evidence_unit_id", None):
                anchor = getattr(self.candidate, "current_evidence_excerpt", None)

        if anchor and anchor in text:
            idx = text.index(anchor)
            start = max(0, idx - _WINDOW_CHARS)
            end = min(len(text), idx + len(anchor) + _WINDOW_CHARS)
            snippet = text[start:end]
            return f"{'… ' if start > 0 else ''}{snippet}{' …' if end < len(text) else ''}"

        if len(text) > _FALLBACK_CHARS:
            return (
                text[:_FALLBACK_CHARS]
                + f"… [truncated, {len(text)} chars total -- this unit has no known "
                "evidence excerpt to center on; use find_attribute_changes or "
                "get_entity_timeline to locate the specific line you need first]"
            )
        return text

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
        return _cap_rows(await self._query(sql, "get_state_at_unit"), excerpt_key="excerpt")

    async def find_attribute_changes(self, entity_id: str, attribute: str) -> List[Dict[str, Any]]:
        sql = f"""
        SELECT sequence_number, value, raw_excerpt
        FROM state_events
        WHERE story_universe_id = '{self.story_universe_id}'
          AND entity_id = '{entity_id}'
          AND attribute = '{attribute}'
        ORDER BY sequence_number
        """
        return _cap_rows(await self._query(sql, "find_attribute_changes"))
