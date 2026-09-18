"""StoryTrace V2 Deterministic Candidate Conflict Detector.

Executes parameterized ClickHouse analytical window queries across state_events_v2
and scene_co_presence_v2 tables to detect potential continuity anomalies.
Guarantees 100% deterministic, zero-LLM candidate generation.
"""

from __future__ import annotations

import logging
import uuid
from typing import List, Optional

from backend.v2.clickhouse.client import ClickHouseClientV2
from backend.v2.story_state.models import CandidateConflictV2
from backend.v2.candidate_detection.sql_rules import (
    RULE_1_POSSESSION_SQL,
    RULE_2_CO_PRESENCE_COLLISION_SQL,
    RULE_3_SPATIAL_JUMP_SQL,
    RULE_4_PHYSICAL_INVERSION_SQL,
    RULE_5_CLOTHING_SWAP_SQL,
    RULE_6_EPISTEMIC_ORDERING_SQL,
    RULE_7_RELATIONAL_RUPTURE_SQL,
    RULE_8_EVENT_CHRONOLOGY_SQL,
)

logger = logging.getLogger(__name__)

ALL_RULES = [
    ("possession_machine", RULE_1_POSSESSION_SQL),
    ("co_presence_collision", RULE_2_CO_PRESENCE_COLLISION_SQL),
    ("continuous_spatial_jump", RULE_3_SPATIAL_JUMP_SQL),
    ("physical_inversion", RULE_4_PHYSICAL_INVERSION_SQL),
    ("clothing_swap", RULE_5_CLOTHING_SWAP_SQL),
    ("epistemic_anomaly", RULE_6_EPISTEMIC_ORDERING_SQL),
    ("relational_rupture", RULE_7_RELATIONAL_RUPTURE_SQL),
    ("chronology_inversion", RULE_8_EVENT_CHRONOLOGY_SQL),
]


class CandidateDetectorV2:
    def __init__(self, client: ClickHouseClientV2):
        self.client = client

    def detect_conflicts(self, story_universe_id: str) -> List[CandidateConflictV2]:
        """Execute all 8 deterministic SQL rules and return deduplicated candidate conflicts."""
        raw_candidates: List[CandidateConflictV2] = []
        seen_signatures = set()

        for rule_name, sql_query in ALL_RULES:
            try:
                result = self.client.client.query(
                    sql_query,
                    parameters={"story_universe_id": story_universe_id}
                )
                for row in result.result_rows:
                    rule_type = row[0]
                    entity_ids = list(row[1]) if isinstance(row[1], (list, tuple)) else [str(row[1])]
                    attribute = str(row[2])
                    prev_unit_id = str(row[3]) if row[3] is not None else ""
                    prev_raw_excerpt = str(row[4]) if row[4] is not None else ""
                    current_unit_id = str(row[5]) if row[5] is not None else ""
                    current_raw_excerpt = str(row[6]) if row[6] is not None else ""
                    description = str(row[7])
                    severity_hint = str(row[8]) if len(row) > 8 else "warning"

                    # Skip empty transitions
                    if not prev_unit_id or not current_unit_id:
                        continue

                    # Deduplication key
                    sig = (
                        rule_type,
                        tuple(sorted(entity_ids)),
                        attribute,
                        prev_unit_id,
                        current_unit_id
                    )
                    if sig in seen_signatures:
                        continue
                    seen_signatures.add(sig)

                    candidate_id = f"{story_universe_id}_{rule_type}_{uuid.uuid4().hex[:8]}"
                    conflict = CandidateConflictV2(
                        id=candidate_id,
                        story_universe_id=story_universe_id,
                        rule_type=rule_type,
                        entity_ids=entity_ids,
                        attribute=attribute,
                        prior_evidence_unit_id=prev_unit_id,
                        prior_evidence_excerpt=prev_raw_excerpt,
                        current_evidence_unit_id=current_unit_id,
                        current_evidence_excerpt=current_raw_excerpt,
                        description=description,
                        severity_hint=severity_hint
                    )
                    raw_candidates.append(conflict)
            except Exception as e:
                logger.error("Error executing candidate rule %s for universe %s: %s", rule_name, story_universe_id, e)

        return raw_candidates

    def detect_and_store(self, story_universe_id: str) -> List[CandidateConflictV2]:
        """Detect candidates and store them into ClickHouse candidate_conflicts_v2."""
        candidates = self.detect_conflicts(story_universe_id)
        if candidates and self.client:
            self.client.insert_candidate_conflicts_v2(candidates)
        return candidates
