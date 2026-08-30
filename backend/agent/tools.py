from backend.clickhouse.client import ClickHouseClient
from typing import List, Dict, Any

class AgentTools:
    def __init__(self, client: ClickHouseClient, story_universe_id: str):
        self.client = client
        self.story_universe_id = story_universe_id

    def get_entity_timeline(self, entity_id: str, from_sequence: int, to_sequence: int) -> List[Dict[str, Any]]:
        query = f"""
        SELECT sequence_number, attribute, value, raw_excerpt
        FROM state_events
        WHERE story_universe_id = '{self.story_universe_id}'
          AND entity_id = '{entity_id}'
          AND sequence_number >= {from_sequence}
          AND sequence_number <= {to_sequence}
        ORDER BY sequence_number
        """
        result = self.client.client.query(query)
        return [{"sequence": r[0], "attr": r[1], "value": r[2], "text": r[3]} for r in result.result_rows]

    def get_unit_text(self, unit_id: str) -> str:
        query = f"""
        SELECT text
        FROM narrative_units
        WHERE story_universe_id = '{self.story_universe_id}' AND id = '{unit_id}'
        """
        result = self.client.client.query(query)
        if result.result_rows:
            return result.result_rows[0][0]
        return ""

    def get_state_at_unit(self, entity_id: str, sequence_number: int) -> List[Dict[str, Any]]:
        query = f"""
        SELECT attribute, argMax(value, sequence_number)
        FROM state_events
        WHERE story_universe_id = '{self.story_universe_id}'
          AND entity_id = '{entity_id}'
          AND sequence_number <= {sequence_number}
        GROUP BY attribute
        """
        result = self.client.client.query(query)
        return [{"attr": r[0], "value": r[1]} for r in result.result_rows]

    def find_attribute_changes(self, entity_id: str, attribute: str) -> List[Dict[str, Any]]:
        query = f"""
        SELECT sequence_number, value, raw_excerpt
        FROM state_events
        WHERE story_universe_id = '{self.story_universe_id}'
          AND entity_id = '{entity_id}'
          AND attribute = '{attribute}'
        ORDER BY sequence_number
        """
        result = self.client.client.query(query)
        return [{"sequence": r[0], "value": r[1], "text": r[2]} for r in result.result_rows]
