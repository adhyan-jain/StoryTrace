from typing import List
from backend.clickhouse.client import ClickHouseClient
from backend.story_state.models import CandidateConflict
import uuid

class CandidateDetector:
    def __init__(self, client: ClickHouseClient):
        self.client = client

    def detect_conflicts(self, story_universe_id: str) -> List[CandidateConflict]:
        # We look for possession conflicts: lost -> held without an acquired event.
        # This uses ClickHouse window functions to look at the previous state,
        # ordered by the document-agnostic sequence_number rather than any
        # per-document numbering (e.g. scene or chapter number).

        query = f"""
        WITH ranked_events AS (
            SELECT
                entity_id,
                unit_id,
                sequence_number,
                attribute,
                value,
                raw_excerpt,
                lagInFrame(value) OVER (PARTITION BY entity_id, attribute ORDER BY sequence_number) AS prev_value,
                lagInFrame(unit_id) OVER (PARTITION BY entity_id, attribute ORDER BY sequence_number) AS prev_unit_id,
                lagInFrame(raw_excerpt) OVER (PARTITION BY entity_id, attribute ORDER BY sequence_number) AS prev_raw_excerpt
            FROM state_events
            WHERE story_universe_id = '{story_universe_id}'
            ORDER BY entity_id, sequence_number
        )
        SELECT *
        FROM ranked_events
        WHERE
            ((attribute = 'possession' OR startsWith(attribute, 'possession.')) AND prev_value = 'lost' AND value = 'held') OR
            (startsWith(attribute, 'injury.') AND prev_value = 'injured' AND value = 'healed')
        """

        result = self.client.client.query(query)

        conflicts = []
        for row in result.result_rows:
            entity_id = row[0]
            unit_id = row[1]
            attribute = row[3]
            value = row[4]
            raw_excerpt = row[5]
            prev_value = row[6]
            prev_unit_id = row[7]
            prev_raw_excerpt = row[8]

            description = f"Suspicious transition for {attribute}: {prev_value} -> {value} without bridging event."

            conflict = CandidateConflict(
                id=f"{story_universe_id}_{uuid.uuid4().hex[:8]}",
                story_universe_id=story_universe_id,
                entity_id=entity_id,
                attribute=attribute,
                prior_evidence_unit_id=prev_unit_id,
                prior_evidence_excerpt=prev_raw_excerpt,
                current_evidence_unit_id=unit_id,
                current_evidence_excerpt=raw_excerpt,
                description=description
            )
            conflicts.append(conflict)

        return conflicts
