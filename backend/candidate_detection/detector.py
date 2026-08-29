from typing import List
from backend.clickhouse.client import ClickHouseClient
from backend.story_state.models import CandidateConflict
import uuid

class CandidateDetector:
    def __init__(self, client: ClickHouseClient):
        self.client = client

    def detect_conflicts(self, screenplay_id: str) -> List[CandidateConflict]:
        # We look for possession conflicts: lost -> held without an acquired event.
        # This uses ClickHouse window functions to look at the previous state.
        
        query = f"""
        WITH ranked_events AS (
            SELECT 
                entity_id,
                scene_id,
                scene_number,
                attribute,
                value,
                raw_excerpt,
                lagInFrame(value) OVER (PARTITION BY entity_id, attribute ORDER BY scene_number) AS prev_value,
                lagInFrame(scene_id) OVER (PARTITION BY entity_id, attribute ORDER BY scene_number) AS prev_scene_id,
                lagInFrame(raw_excerpt) OVER (PARTITION BY entity_id, attribute ORDER BY scene_number) AS prev_raw_excerpt
            FROM state_events
            WHERE screenplay_id = '{screenplay_id}'
            ORDER BY entity_id, scene_number
        )
        SELECT *
        FROM ranked_events
        WHERE 
            (attribute = 'possession' AND prev_value = 'lost' AND value = 'held') OR
            (attribute = 'injury' AND prev_value = 'injured' AND value = 'healed')
        """
        
        result = self.client.client.query(query)
        
        conflicts = []
        for row in result.result_rows:
            entity_id = row[0]
            scene_id = row[1]
            attribute = row[3]
            value = row[4]
            raw_excerpt = row[5]
            prev_value = row[6]
            prev_scene_id = row[7]
            prev_raw_excerpt = row[8]
            
            description = f"Suspicious transition for {attribute}: {prev_value} -> {value} without bridging event."
            
            conflict = CandidateConflict(
                id=f"{screenplay_id}_{uuid.uuid4().hex[:8]}",
                screenplay_id=screenplay_id,
                entity_id=entity_id,
                prior_evidence_scene_id=prev_scene_id,
                prior_evidence_excerpt=prev_raw_excerpt,
                current_evidence_scene_id=scene_id,
                current_evidence_excerpt=raw_excerpt,
                description=description
            )
            conflicts.append(conflict)
            
        return conflicts
