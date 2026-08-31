import os
import clickhouse_connect
from pydantic import BaseModel
from typing import List, Any

class ClickHouseClient:
    def __init__(self):
        host = os.environ.get("CLICKHOUSE_HOST", "localhost")
        port = int(os.environ.get("CLICKHOUSE_PORT", "8123"))
        user = os.environ.get("CLICKHOUSE_USER", "default")
        password = os.environ.get("CLICKHOUSE_PASSWORD", "admin")
        database = os.environ.get("CLICKHOUSE_DB", "storytrace")

        self.client = clickhouse_connect.get_client(
            host=host, port=port, user=user, password=password, database=database
        )

    def insert_narrative_units(self, units: List[BaseModel]):
        if not units:
            return

        data = [
            [
                u.unit_id, u.story_universe_id, u.document_id, u.unit_type,
                u.sequence_number, u.title, u.raw_text, u.page_start, u.page_end
            ]
            for u in units
        ]

        self.client.insert(
            'narrative_units',
            data,
            column_names=['id', 'story_universe_id', 'document_id', 'unit_type', 'sequence_number', 'title', 'text', 'start_page', 'end_page']
        )

    def insert_entities(self, entities: List[Any]):
        if not entities:
            return

        data = [
            [
                e.id, e.story_universe_id, e.type, e.name, e.aliases
            ]
            for e in entities
        ]

        self.client.insert(
            'entities',
            data,
            column_names=['id', 'story_universe_id', 'type', 'name', 'aliases']
        )

    def insert_state_events(self, events: List[Any]):
        if not events:
            return

        data = [
            [
                e.id, e.story_universe_id, e.entity_id, e.attribute,
                e.value, e.unit_id, e.sequence_number, e.page_ref,
                e.raw_excerpt, e.establishment_type, e.confidence
            ]
            for e in events
        ]

        self.client.insert(
            'state_events',
            data,
            column_names=['id', 'story_universe_id', 'entity_id', 'attribute', 'value', 'unit_id', 'sequence_number', 'page_ref', 'raw_excerpt', 'establishment_type', 'confidence']
        )

    def insert_candidate_conflicts(self, conflicts: List[Any]):
        if not conflicts:
            return

        data = [
            [
                c.id, c.story_universe_id, c.entity_id, c.attribute,
                c.prior_evidence_unit_id, c.prior_evidence_excerpt,
                c.current_evidence_unit_id, c.current_evidence_excerpt,
                c.description
            ]
            for c in conflicts
        ]

        self.client.insert(
            'candidate_conflicts',
            data,
            column_names=['id', 'story_universe_id', 'entity_id', 'attribute', 'prior_evidence_unit_id', 'prior_evidence_excerpt', 'current_evidence_unit_id', 'current_evidence_excerpt', 'description']
        )

    def insert_investigation_verdicts(self, verdicts: List[Any]):
        if not verdicts:
            return

        data = [
            [
                v.id, v.candidate_id, v.status, v.severity,
                v.explanation, v.confidence, v.investigation_actions
            ]
            for v in verdicts
        ]

        self.client.insert(
            'investigation_verdicts',
            data,
            column_names=['id', 'candidate_id', 'status', 'severity', 'explanation', 'confidence', 'investigation_actions']
        )
