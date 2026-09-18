import os
from typing import List, Any, Optional
from backend.clickhouse.client import ClickHouseClient
from backend.v2.story_state.models import (
    StateEventV2, SceneCoPresence, CandidateConflictV2, InvestigationVerdictV2
)

class ClickHouseClientV2(ClickHouseClient):
    def __init__(self):
        super().__init__()
        self.ensure_v2_schema()

    def ensure_v2_schema(self):
        sql_path = os.path.join(os.path.dirname(__file__), "schema_v2.sql")
        if os.path.exists(sql_path):
            with open(sql_path, "r") as f:
                statements = f.read().split(";")
                for stmt in statements:
                    stmt = stmt.strip()
                    if stmt:
                        try:
                            self.client.command(stmt)
                        except Exception as e:
                            # Log and proceed if already exists or permission issues
                            pass

    def insert_state_events_v2(self, events: List[StateEventV2]):
        if not events:
            return
        data = [
            [
                e.id, e.story_universe_id, e.entity_id, e.attribute, e.value,
                e.unit_id, e.sequence_number, e.page_ref, e.raw_excerpt,
                e.establishment_type, e.confidence, e.hier_setting_type,
                e.hier_environment, e.hier_specific_room, e.hier_city_region,
                e.time_anchor, e.related_entity_id
            ]
            for e in events
        ]
        column_names = [
            'id', 'story_universe_id', 'entity_id', 'attribute', 'value',
            'unit_id', 'sequence_number', 'page_ref', 'raw_excerpt',
            'establishment_type', 'confidence', 'hier_setting_type',
            'hier_environment', 'hier_specific_room', 'hier_city_region',
            'time_anchor', 'related_entity_id'
        ]
        self._retry_call(self.client.insert, 'state_events_v2', data, column_names=column_names)

    def insert_scene_co_presence_v2(self, co_presences: List[SceneCoPresence]):
        if not co_presences:
            return
        data = [
            [
                cp.id, cp.story_universe_id, cp.unit_id, cp.sequence_number,
                cp.entity_ids, cp.setting_type, cp.environment, cp.specific_room,
                cp.time_of_day, cp.time_anchor
            ]
            for cp in co_presences
        ]
        column_names = [
            'id', 'story_universe_id', 'unit_id', 'sequence_number',
            'entity_ids', 'setting_type', 'environment', 'specific_room',
            'time_of_day', 'time_anchor'
        ]
        self._retry_call(self.client.insert, 'scene_co_presence_v2', data, column_names=column_names)

    def insert_candidate_conflicts_v2(self, candidates: List[CandidateConflictV2]):
        if not candidates:
            return
        data = [
            [
                c.id, c.story_universe_id, c.rule_type, c.entity_ids, c.attribute,
                c.prior_evidence_unit_id, c.prior_evidence_excerpt,
                c.current_evidence_unit_id, c.current_evidence_excerpt,
                c.description, c.severity_hint
            ]
            for c in candidates
        ]
        column_names = [
            'id', 'story_universe_id', 'rule_type', 'entity_ids', 'attribute',
            'prior_evidence_unit_id', 'prior_evidence_excerpt',
            'current_evidence_unit_id', 'current_evidence_excerpt',
            'description', 'severity_hint'
        ]
        self._retry_call(self.client.insert, 'candidate_conflicts_v2', data, column_names=column_names)

    def insert_verdict_v2(self, verdict: InvestigationVerdictV2):
        data = [[
            verdict.id, verdict.candidate_id, str(verdict.status.value),
            verdict.severity, verdict.explanation, verdict.confidence,
            verdict.investigation_actions, verdict.suggested_fix
        ]]
        column_names = [
            'id', 'candidate_id', 'status', 'severity', 'explanation',
            'confidence', 'investigation_actions', 'suggested_fix'
        ]
        self._retry_call(self.client.insert, 'investigation_verdicts_v2', data, column_names=column_names)

    def get_entity_timeline_v2(self, entity_id: str, story_universe_id: str) -> List[Any]:
        return self.client.query(
            """SELECT sequence_number, unit_id, attribute, value, hier_setting_type,
                      hier_environment, hier_specific_room, hier_city_region, time_anchor, raw_excerpt
               FROM state_events_v2
               WHERE story_universe_id = {story_universe_id:String} AND entity_id = {entity_id:String}
               ORDER BY sequence_number ASC""",
            parameters={"story_universe_id": story_universe_id, "entity_id": entity_id},
        ).result_rows

    def get_scene_co_presence(self, story_universe_id: str, sequence_number: int) -> List[Any]:
        return self.client.query(
            """SELECT sequence_number, unit_id, entity_ids, setting_type, environment, specific_room, time_anchor
               FROM scene_co_presence_v2
               WHERE story_universe_id = {story_universe_id:String} AND sequence_number = {sequence_number:Int32}
               LIMIT 1""",
            parameters={"story_universe_id": story_universe_id, "sequence_number": sequence_number},
        ).result_rows

    def get_spatial_trajectory(self, entity_id: str, story_universe_id: str) -> List[Any]:
        return self.client.query(
            """SELECT sequence_number, unit_id, hier_setting_type, hier_environment, hier_specific_room, hier_city_region, time_anchor
               FROM state_events_v2
               WHERE story_universe_id = {story_universe_id:String}
                 AND entity_id = {entity_id:String}
                 AND (hier_environment != '' OR hier_specific_room != '' OR hier_city_region != '')
               ORDER BY sequence_number ASC""",
            parameters={"story_universe_id": story_universe_id, "entity_id": entity_id},
        ).result_rows
