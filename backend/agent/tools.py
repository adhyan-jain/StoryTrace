from backend.clickhouse.client import ClickHouseClient
from typing import List, Dict, Any

class AgentTools:
    def __init__(self, client: ClickHouseClient, screenplay_id: str):
        self.client = client
        self.screenplay_id = screenplay_id

    def get_entity_timeline(self, entity_id: str, from_scene: int, to_scene: int) -> List[Dict[str, Any]]:
        query = f"""
        SELECT scene_number, attribute, value, raw_excerpt
        FROM state_events
        WHERE screenplay_id = '{self.screenplay_id}' 
          AND entity_id = '{entity_id}'
          AND scene_number >= {from_scene}
          AND scene_number <= {to_scene}
        ORDER BY scene_number
        """
        result = self.client.client.query(query)
        return [{"scene": r[0], "attr": r[1], "value": r[2], "text": r[3]} for r in result.result_rows]

    def get_scene_text(self, scene_number: int) -> str:
        query = f"""
        SELECT text
        FROM scenes
        WHERE screenplay_id = '{self.screenplay_id}' AND number = {scene_number}
        """
        result = self.client.client.query(query)
        if result.result_rows:
            return result.result_rows[0][0]
        return ""

    def get_state_at_scene(self, entity_id: str, scene_number: int) -> List[Dict[str, Any]]:
        query = f"""
        SELECT attribute, argMax(value, scene_number)
        FROM state_events
        WHERE screenplay_id = '{self.screenplay_id}' 
          AND entity_id = '{entity_id}'
          AND scene_number <= {scene_number}
        GROUP BY attribute
        """
        result = self.client.client.query(query)
        return [{"attr": r[0], "value": r[1]} for r in result.result_rows]
